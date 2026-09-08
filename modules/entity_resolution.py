"""
entity_resolution.py - Deterministic & Probabilistic Entity Resolution Engine
Zero-GPU execution with explicit IF/ELSE anti-merge safeguards.
Implements:
1. Jaro-Winkler string similarity
2. Indic phonetic name matching
3. Indian vehicle registration OCR error normalizer (e.g., TS09A81234 -> TS09AB1234)
4. Anti-merge rules for high-density addresses (hostels/PGs) and co-accused conflicts
"""

import re
import json
from typing import Dict, List, Tuple, Any, Optional


def jaro_similarity(s1: str, s2: str) -> float:
    """Calculates basic Jaro similarity between two strings."""
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    match_distance = max(len1, len2) // 2 - 1
    s1_matches = [False] * len1
    s2_matches = [False] * len2

    matches = 0
    transpositions = 0

    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    transpositions //= 2
    return (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3.0


def jaro_winkler(s1: str, s2: str, p: float = 0.1) -> float:
    """Calculates Jaro-Winkler distance, giving higher weight to common prefixes."""
    s1_clean = s1.strip().lower()
    s2_clean = s2.strip().lower()
    j = jaro_similarity(s1_clean, s2_clean)
    prefix = 0
    for c1, c2 in zip(s1_clean[:4], s2_clean[:4]):
        if c1 == c2:
            prefix += 1
        else:
            break
    return j + prefix * p * (1 - j)


def indic_phonetic_normalize(name: str) -> str:
    """
    Normalizes common Indic phonetic variations, honorifics, and transliterations.
    e.g., Mohd / Mohammed / Md. -> MOHD
    Raheem / Rahim -> RAHIM
    Farooq / Farook -> FAROOQ
    """
    n = name.strip().upper()
    n = re.sub(r'^(?:MD\.?|MOHD\.?|MOHAMMED|MUHAMMAD)\s+', 'MOHD ', n)
    n = re.sub(r'^(?:SRI\.?|SHREE|SHRI)\s+', '', n)
    n = re.sub(r'^(?:DR\.?|PROF\.?)\s+', '', n)
    
    # Phonetic replacements
    n = n.replace('EE', 'I')
    n = n.replace('OO', 'U')
    n = n.replace('OOK', 'OOQ')
    n = n.replace('KH', 'K')
    n = n.replace('PH', 'F')
    n = n.replace('BHAIJAAN', 'BHAI')
    n = n.replace('BHAI', '')
    return n.strip()


def normalize_vehicle_plate(plate: str) -> Tuple[str, bool]:
    """
    Normalizes Indian vehicle license plates and repairs common OCR misreadings.
    Standard Format: [State 2-alpha][District 2-num][Series 1-2 alpha][Number 4-num]
    e.g. TS 09 AB 1234
    Common OCR Errors: '8' misread as 'B' or vice-versa in series segment.
    """
    raw = re.sub(r'[\s\-_]', '', plate.strip().upper())
    is_corrected = False

    # Standard regex for 10-char plate: TS09AB1234
    m = re.match(r'^([A-Z]{2})([0-9]{1,2})([A-Z0-9]{1,3})([0-9]{4})$', raw)
    if m:
        state, rto, series, num = m.groups()
        # If series contains '8' where a letter should be, repair to 'B'
        if '8' in series:
            repaired_series = series.replace('8', 'B')
            raw = f"{state}{rto}{repaired_series}{num}"
            is_corrected = True
        # If series contains '0' where a letter should be, repair to 'O' or 'D'
        elif '0' in series:
            repaired_series = series.replace('0', 'O')
            raw = f"{state}{rto}{repaired_series}{num}"
            is_corrected = True

    return raw, is_corrected


class DeterministicEntityResolver:
    """
    Deterministic Entity Resolution Engine with explicit Anti-Merge rules.
    Runs on CPU without GPU overhead.
    """

    def __init__(self, known_hostels_path: Optional[str] = None):
        self.known_multi_tenants = []
        if known_hostels_path:
            try:
                with open(known_hostels_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.known_multi_tenants = [a["address_string"].lower() for a in data.get("known_addresses", [])]
                    self.keywords = [k.lower() for k in data.get("known_multi_tenant_keywords", [])]
            except Exception:
                self.keywords = ["hostel", "pg", "paying guest", "tower", "dlf", "mansion"]
        else:
            self.keywords = ["hostel", "pg", "paying guest", "tower", "dlf", "mansion"]

    def is_multi_tenant_address(self, address: str) -> bool:
        """Identifies high-density residential hubs where co-location does not imply conspiracy."""
        addr_lower = address.lower()
        if any(kw in addr_lower for kw in self.keywords):
            return True
        if any(km in addr_lower for km in self.known_multi_tenants):
            return True
        return False

    def evaluate_pair(self, e1: Dict[str, Any], e2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates two entity records using deterministic logic and anti-merge constraints.
        Returns match decision, confidence score, and clear audit explanation.
        """
        reasons = []
        anti_merge_triggered = False
        anti_merge_reason = None

        # ---------------- HARD NEGATIVE CONSTRAINTS (ANTI-MERGE) ---------------- #
        # Constraint 1: Co-accused or Victim vs Accused in the same FIR
        if e1.get("fir_id") and e2.get("fir_id") and e1.get("fir_id") == e2.get("fir_id"):
            role1 = e1.get("role", "").upper()
            role2 = e2.get("role", "").upper()
            if "VICTIM" in role1 and "ACCUSED" in role2:
                anti_merge_triggered = True
                anti_merge_reason = f"ANTI-MERGE RULE #1: Entity A is Victim and Entity B is Accused in FIR {e1['fir_id']}"
            elif "ACCUSED" in role1 and "ACCUSED" in role2 and e1.get("name") != e2.get("name"):
                anti_merge_triggered = True
                anti_merge_reason = f"ANTI-MERGE RULE #2: Distinct co-accused persons listed in same FIR {e1['fir_id']}"

        # Constraint 2: Father name demographic clash
        f1 = e1.get("father_name")
        f2 = e2.get("father_name")
        if f1 and f2:
            if jaro_winkler(f1, f2) < 0.65:
                anti_merge_triggered = True
                anti_merge_reason = f"ANTI-MERGE RULE #3: Demographic clash in Father's Name ('{f1}' vs '{f2}')"

        if anti_merge_triggered:
            return {
                "decision": "BLOCKED_BY_SAFEGUARD",
                "match_score": 0.0,
                "is_same_entity": False,
                "reason": anti_merge_reason,
                "reasons": [anti_merge_reason]
            }

        # ---------------- MULTI-ATTRIBUTE WEIGHTED SCORING ---------------- #
        score = 0.0

        # Feature 1: Deterministic Identifiers (Phone / UPI / Bank / PAN)
        p1 = e1.get("phone")
        p2 = e2.get("phone")
        if p1 and p2 and p1 == p2:
            score += 0.85
            reasons.append(f"Identical verified phone number ({p1})")

        u1 = e1.get("upi_id")
        u2 = e2.get("upi_id")
        if u1 and u2 and u1.lower() == u2.lower():
            score += 0.85
            reasons.append(f"Identical UPI VPA ({u1})")

        # Feature 2: Vehicle Plate with OCR Correction
        v1 = e1.get("vehicle_plate")
        v2 = e2.get("vehicle_plate")
        if v1 and v2:
            norm_v1, c1 = normalize_vehicle_plate(v1)
            norm_v2, c2 = normalize_vehicle_plate(v2)
            if norm_v1 == norm_v2:
                score += 0.80
                reasons.append(f"Vehicle license match ({norm_v1}) [OCR Normalized: {c1 or c2}]")

        # Feature 3: Phonetic & String Name Similarity
        n1 = e1.get("name", "")
        n2 = e2.get("name", "")
        if n1 and n2:
            norm_n1 = indic_phonetic_normalize(n1)
            norm_n2 = indic_phonetic_normalize(n2)
            jw_sim = jaro_winkler(norm_n1, norm_n2)
            if jw_sim >= 0.85:
                score += jw_sim * 0.35
                reasons.append(f"High Indic phonetic name similarity ({jw_sim:.2f}) between '{n1}' and '{n2}'")
            elif jw_sim >= 0.70:
                score += jw_sim * 0.20
                reasons.append(f"Moderate name similarity ({jw_sim:.2f})")

        # Feature 4: Address Entropy Safeguard
        a1 = e1.get("address")
        a2 = e2.get("address")
        if a1 and a2:
            addr_sim = jaro_winkler(a1, a2)
            is_hostel = self.is_multi_tenant_address(a1) or self.is_multi_tenant_address(a2)
            if is_hostel:
                # Down-weight address drastically for hostels to prevent false merge
                score += 0.02
                reasons.append(f"Address matches multi-tenant PG/Hostel ('{a1[:30]}...'). Weight reduced to 0.02 to prevent false syndicate clustering.")
            else:
                score += addr_sim * 0.25
                reasons.append(f"Address match ({addr_sim:.2f})")

        final_score = min(1.0, score)

        if final_score >= 0.85:
            decision = "MERGED_CANONICAL"
            is_same = True
        elif final_score >= 0.60:
            decision = "FLAGGED_FOR_HUMAN_REVIEW"
            is_same = False
        else:
            decision = "DISTINCT_ENTITIES"
            is_same = False

        return {
            "decision": decision,
            "match_score": round(final_score, 3),
            "is_same_entity": is_same,
            "reason": "; ".join(reasons) if reasons else "No corroborated attributes found",
            "reasons": reasons
        }

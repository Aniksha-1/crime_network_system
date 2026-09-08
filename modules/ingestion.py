"""
ingestion.py - Zero-GPU Deterministic Evidence Ingestion & Parsing Engine
Computes SHA-256 digital hashes for chain-of-custody under Section 63 BSA 2023.
Extracts entities deterministically using regex and token normalizers.
"""

import os
import re
import json
import hashlib
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Regex Patterns for Indian Law Enforcement Data
RE_PHONE = re.compile(r'(?:\+91[\-\s]?)?[6-9]\d{9}')
RE_UPI = re.compile(r'\b[a-zA-Z0-9.\-_]{2,64}@[a-zA-Z]{2,32}\b')
RE_VEHICLE = re.compile(r'\b[A-Z]{2}\s?[0-9]{1,2}\s?[A-Z]{1,3}\s?[0-9]{4}\b', re.IGNORECASE)
RE_VEHICLE_TYPO = re.compile(r'\b[A-Z]{2}\s?[0-9]{1,2}\s?[A-Z0-9]{1,3}\s?[0-9]{4}\b', re.IGNORECASE)
RE_BNS_SECTION = re.compile(r'(?:Section\s+)?(?:\d+(?:\(\w+\))?)\s*(?:BNS|IPC|IT\s*Act|PMLA)', re.IGNORECASE)
RE_INR_AMOUNT = re.compile(r'(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)', re.IGNORECASE)
RE_BANK_ACC = re.compile(r'\b\d{9,18}\b')


def compute_sha256(file_path: str) -> str:
    """Calculates SHA-256 cryptographic hash of a file for court admissibility."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def compute_string_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_fir_text(file_path: str) -> Dict[str, Any]:
    """Deterministically extracts structured entities and metadata from FIR text."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    file_hash = compute_sha256(file_path)
    file_name = os.path.basename(file_path)

    # Extract FIR number
    fir_match = re.search(r'FIR\s*(?:No\.?|Number)?\s*[:\-]?\s*([0-9]+/[0-9]{4})', content, re.IGNORECASE)
    fir_no = fir_match.group(1) if fir_match else "UNKNOWN"

    # Police station
    ps_match = re.search(r'Police\s*Station\s*[:\-]?\s*([^\n]+)', content, re.IGNORECASE)
    police_station = ps_match.group(1).strip() if ps_match else "Unknown PS"

    # Sections
    sections = RE_BNS_SECTION.findall(content)

    # Identifiers
    raw_phones = RE_PHONE.findall(content)
    # Normalize phones to +91XXXXXXXXXX
    phones = []
    for p in raw_phones:
        clean_p = re.sub(r'[^\d]', '', p)
        if len(clean_p) == 10:
            clean_p = "+91" + clean_p
        elif len(clean_p) == 12 and clean_p.startswith("91"):
            clean_p = "+" + clean_p
        if clean_p not in phones:
            phones.append(clean_p)

    upis = list(set(RE_UPI.findall(content)))
    vehicles = list(set(RE_VEHICLE.findall(content) + RE_VEHICLE_TYPO.findall(content)))

    # Named Persons & Roles (Deterministic extraction from structured FIR sections)
    persons = []
    complainant_match = re.search(r'Complainant[^\n]*\n\s*Name\s*[:\-]?\s*([^\n\(]+)', content, re.IGNORECASE)
    if complainant_match:
        persons.append({"name": complainant_match.group(1).strip(), "role": "VICTIM_COMPLAINANT", "fir": fir_no})

    suspect_matches = re.findall(r'(?:alias|named|accused|called)\s*["\']?([A-Za-z\s]{3,30})["\']?', content, re.IGNORECASE)
    for sm in suspect_matches:
        s_name = sm.strip()
        if s_name.lower() not in ["mobile", "fedx", "police", "customs", "cbi", "director", "bank"]:
            persons.append({"name": s_name, "role": "SUSPECT_ACCUSED", "fir": fir_no})

    # Amounts
    amounts = RE_INR_AMOUNT.findall(content)

    evidence_envelope = {
        "evidence_id": f"EV_FIR_{fir_no.replace('/', '_')}",
        "source_file": file_name,
        "sha256": file_hash,
        "document_type": "FIRST_INFORMATION_REPORT",
        "case_id": fir_no,
        "police_station": police_station,
        "extracted_sections": sections,
        "phones": phones,
        "upis": upis,
        "vehicles": vehicles,
        "persons": persons,
        "amounts": amounts,
        "raw_content_preview": content[:400] + "..."
    }

    return evidence_envelope


def parse_cdr_csv(file_path: str) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """Parses telecom CDR CSV file with cryptographic verification."""
    df = pd.read_csv(file_path)
    file_hash = compute_sha256(file_path)
    file_name = os.path.basename(file_path)

    all_callers = df["calling_number"].unique().tolist()
    all_called = df["called_number"].unique().tolist()
    unique_phones = list(set(all_callers + all_called))

    metadata = {
        "evidence_id": "EV_CDR_TELECOM_DUMP",
        "source_file": file_name,
        "sha256": file_hash,
        "document_type": "CALL_DETAIL_RECORD",
        "total_calls": len(df),
        "unique_phones": unique_phones,
        "date_range": [str(df["call_timestamp"].min()), str(df["call_timestamp"].max())],
        "top_routes": df.groupby(["calling_number", "called_number"]).size().to_dict()
    }
    return metadata, df


def parse_bank_csv(file_path: str) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """Parses Bank/UPI ledger transactions CSV."""
    df = pd.read_csv(file_path)
    file_hash = compute_sha256(file_path)
    file_name = os.path.basename(file_path)

    total_volume = int(df["amount_inr"].sum())
    unique_entities = list(set(df["sender_vpa_or_acc"].unique().tolist() + df["receiver_vpa_or_acc"].unique().tolist()))

    metadata = {
        "evidence_id": "EV_FIN_BANK_LEDGER",
        "source_file": file_name,
        "sha256": file_hash,
        "document_type": "FINANCIAL_LEDGER",
        "total_transactions": len(df),
        "total_volume_inr": total_volume,
        "participating_accounts": unique_entities
    }
    return metadata, df


def parse_anpr_csv(file_path: str) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """Parses vehicle ANPR / Toll Sighting logs."""
    df = pd.read_csv(file_path)
    file_hash = compute_sha256(file_path)
    file_name = os.path.basename(file_path)

    detected_plates = df["detected_plate"].unique().tolist()
    locations = df["camera_location"].unique().tolist()

    metadata = {
        "evidence_id": "EV_PHYS_ANPR_LOGS",
        "source_file": file_name,
        "sha256": file_hash,
        "document_type": "ANPR_VEHICLE_LOGS",
        "total_sightings": len(df),
        "detected_plates": detected_plates,
        "surveillance_locations": locations
    }
    return metadata, df


def parse_audio_intercept(file_path: str) -> Dict[str, Any]:
    """Parses Sarvam AI speech-to-text audio intercept transcript."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    file_hash = compute_sha256(file_path)
    data["sha256"] = file_hash
    return data

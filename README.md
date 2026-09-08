# Intelligent Crime Network Analysis System (ICNAS)
## SIH 2026 Problem Statement 26189 — Ministry of Home Affairs (MHA)

### 1. Executive Summary & Problem Fit
India's 17,792 police stations are digitized on **CCTNS** and interoperable via **ICJS**. However, investigators still suffer from severe cognitive overload when trying to connect fragmented electronic records (FIRs, CDRs, bank statements, and ANPR toll sightings) across independent state jurisdictions.

**ICNAS** is the **Explainable Reasoning Layer** above CCTNS/ICJS:
- **100% Deterministic & CPU-Executable**: Operates on standard 8GB RAM government laptops without requiring GPUs.
- **Section 63 Bharatiya Sakshya Adhiniyam, 2023 (BSA) Compliant**: Produces legally admissible certificates with cryptographic SHA-256 hashes.
- **Sovereign Indian Speech Integration**: Incorporates **Sarvam AI (Saaras Indic ASR)** for Hinglish/Telugu call intercept transcription.
- **Hard Anti-Merge Safeguards**: Blocks false merges on high-occupancy addresses (e.g. Ameerpet hostels) and distinct co-accused.

---

### 2. Project Directory Structure
```
crime_network_system/
├── app.py                      # Main Streamlit Cockpit & Interactive Visualizer
├── run_icnas.bat               # 1-Click Launch Script
├── requirements.txt            # Python Dependencies
├── data/
│   ├── known_hostels_pms.json  # Multi-tenant address entropy benchmark
│   └── sample_cases/           # Synthetic "Operation Cyber-Spider" dataset
│       ├── fir_104_cyberabad.txt   # Digital Arrest Scam (INR 28.5L)
│       ├── fir_88_hyderabad.txt    # Courier Customs Scam (INR 12L)
│       ├── fir_42_pune.txt         # Hawala Raid (Cash INR 64.5L seized)
│       ├── fir_19_rachakonda.txt   # Stolen White Swift TS09AB1234
│       ├── cdr_dump_feb2026.csv    # 12 Call records linking numbers & towers
│       ├── bank_upi_transactions.csv# Bank accounts & UPI fund flow
│       ├── anpr_toll_sightings.csv # Highway toll & CCTV plate sightings
│       └── audio_transcript_intercept.json # Sarvam AI wiretap transcript
└── modules/
    ├── __init__.py
    ├── ingestion.py            # SHA-256 hasher & deterministic entity extractor
    ├── entity_resolution.py    # Indic Soundex, Jaro-Winkler, Plate OCR fixer, Anti-merge rules
    ├── graph_engine.py         # NetworkX graph builder, Betweenness Centrality, PyVis renderer
    ├── sarvam_speech.py        # Sarvam AI Indic ASR integration with offline fallback
    └── bsa_report.py           # Statutory Section 63 BSA legal certificate generator
```

---

### 3. How to Launch and Demo to Judges

#### Step 1: Launch the Application
In your terminal:
```bash
cd crime_network_system
pip install -r requirements.txt
streamlit run app.py
```
Or simply double-click `run_icnas.bat`.

#### Step 2: The 5-Minute SIH Judging Walkthrough
1. **Overview**: Point to the top metric cards showing **5 ingested electronic files**, all cryptographically verified with **SHA-256 hashes**.
2. **Tab 1 (Graph Visualizer)**: Show how 4 disparate FIRs across Hyderabad, Cyberabad, Rachakonda, and Pune automatically formed an organized crime syndicate. Point out **Farooq Ahmed (Bhaijaan)** and **Vehicle TS09AB1234** glowing in red/orange as top brokers identified by **Brandes Betweenness Centrality**.
3. **Tab 2 (Explain Connection)**: Select `CASE_104_2026` (Cyberabad) and `CASE_42_2026` (Pune). Click **Examine Relationship & Provenance**. The system displays the exact 4-hop evidence trail connecting the victim's money through the IndusInd mule account to the Pune hawala boss.
4. **Tab 3 (Anti-Merge Safeguards)**: Click **Run Hostel Test** and **Run Co-Accused Test**. Show judges how the system explicitly **blocked** false merges for 140 boys living in the Ameerpet hostel and separated distinct co-accused in the same FIR.
5. **Tab 4 (Sarvam AI)**: Show the intercepted phone call between Rahim and Bhaijaan transcribed into Hinglish with sovereign MeitY/Bhashini compliance.
6. **Tab 5 (BSA Certificate)**: Click **Download Official BSA Section 63 Certificate (.txt)**. Explain that this certificate contains the cryptographic hashes and statutory declaration required by the magistrate to issue a search warrant under Section 94 of BNSS, 2023.

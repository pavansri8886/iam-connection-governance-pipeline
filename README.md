# 🔐 IAM Governance Simulation Project aligned with enterprise application risk mapping

> **A reference implementation of enterprise IAM connection governance — 75 applications, 255 connections, 14 departments, 96 governance gaps detected using synthetic production-representative data.**
---
🧩 [IAM Application Connection Governance Report](https://pavan-resume-de.s3.ap-south-1.amazonaws.com/iam_governance_report.html)
---

## 📌 What This Project Does

In large organisations, information about which applications connect to which IAM products is scattered across multiple systems — application inventories, IAM registries, connection logs, and manual spreadsheets. This data is incomplete, inconsistently structured, and not maintained to any defined standard.

The result is a governance gap: nobody has a clear, current picture of which applications have the right IAM coverage, which connections are stale or undocumented, and where the highest risk exposures are.

**This pipeline addresses that directly** — ingesting from three scattered data sources, consolidating into a unified risk-classified governance map, detecting violations, and producing structured outputs for audit systems and management stakeholders.

---

## 🏗️ Architecture

```
3 Scattered Data Sources
        │
        ▼
┌─────────────────────────────────────────┐
│           pipeline.py                   │
│                                         │
│  [1] Ingest from multiple repositories  │
│  [2] Clean & standardise                │
│  [3] Build unified connection map       │
│  [4] Classify risk & detect gaps        │
│  [5] Expose data & maintain             │
└─────────────────────────────────────────┘
        │
        ▼
6 Structured Outputs
```

---

## 📂 Project Structure

```
iam-connection-governance-pipeline/
│
├── 📁 data/                            # Three scattered source repositories
│   ├── application_inventory.csv       # Source 1 — 75 enterprise applications
│   ├── iam_product_registry.json       # Source 2 — 5 IAM products and requirements
│   └── connection_log.csv              # Source 3 — 255 connection records
│
├── 📁 src/                             # Pipeline modules
│   ├── risk_classifier.py              # Risk classification & gap detection logic
│   ├── report_generator.py             # HTML dashboard & CSV export
│   ├── scorecard.py                    # Department scorecard & remediation queue
│   └── __init__.py
│
├── 📁 output/                          # Generated on every pipeline run
│   ├── iam_connection_master_map.csv   # Unified governance map for audit systems
│   ├── governance_gaps.csv             # Gap report for application owners
│   ├── department_risk_scorecard.csv   # Department-level risk ratings
│   ├── remediation_priority_queue.csv  # Prioritised actions with deadlines
│   ├── iam_governance_report.html      # Management dashboard
│   └── pipeline_run_log.txt            # Audit trail
│
├── feeding_rules.yaml                  # Authoritative sources, conflict resolution & SLAs
├── pipeline.py                         # Main entry point
├── requirements.txt
└── README.md
```

---

## 🗂️ Data Sources

| Source | Format | Records | Description |
|--------|--------|---------|-------------|
| `application_inventory.csv` | CSV | 75 apps | Application metadata — owner, department, sensitivity, environment, region |
| `iam_product_registry.json` | JSON | 5 products | Azure AD, PAM, RBAC, MFA, IGA — coverage requirements per sensitivity level |
| `connection_log.csv` | CSV | 255 records | Current connections with realistic gaps — stale reviews, missing entries, unknown reviewers |

**Applications span:** Finance · HR · Operations · Logistics · Compliance · Legal · IT · Air Cargo · Sustainability · Executive · Strategy

**Regions covered:** Global · EMEA · APAC · Americas

---

## ⚙️ Pipeline Steps

### Step 1 — Ingest
Loads all three source files. Simulates the real-world problem: three separate repositories with inconsistencies, missing fields, and varying formats.

### Step 2 — Clean & Standardise
- Fills missing application owners
- Standardises sensitivity and status fields
- Flags connections not reviewed within 180 days as stale
- Handles inconsistent date formats across sources

### Step 3 — Build Unified Connection Map
Merges all three sources into a single structured data model.

**Feeding rules (defined in `feeding_rules.yaml`):**

| Field | Authoritative Source | Update Mode |
|-------|---------------------|-------------|
| App metadata | application_inventory | Manual |
| IAM product details | iam_product_registry | Scheduled (180 days) |
| Connection status | connection_log | Manual (post-review) |
| Risk range | Pipeline (calculated) | Automatic |

### Step 4 — Classify Risk & Detect Gaps

**Risk Classification:**

| Risk | Criteria |
|------|----------|
| 🔴 HIGH | HIGH sensitivity + business critical + Production |
| 🟠 MEDIUM | MEDIUM sensitivity OR stale review OR pending/undocumented |
| 🟢 LOW | LOW sensitivity, Development, non-critical |

**Gap Types Detected:**

| Gap Type | Description |
|----------|-------------|
| `MISSING_CONNECTION` | Required IAM product not connected for app's sensitivity level |
| `STALE_REVIEW` | Connection not reviewed within defined cycle |
| `UNDOCUMENTED_CONNECTION` | Connection exists with no documented status |
| `UNKNOWN_OWNER` | Application has no registered owner |
| `MISSING_REVIEW_DATE` | Active connection with no review date recorded |

### Step 5 — Expose & Maintain
Generates all outputs and logs the run for audit traceability.

---

## 📊 Outputs

| Output | Format | Audience | Channel |
|--------|--------|----------|---------|
| `iam_connection_master_map.csv` | CSV | GRC / Audit systems | Automated integration |
| `governance_gaps.csv` | CSV | Application owners | Weekly email distribution |
| `department_risk_scorecard.csv` | CSV | IAM Manager | Internal reporting |
| `remediation_priority_queue.csv` | CSV | Application owners + IAM team | ServiceNow tickets |
| `iam_governance_report.html` | HTML | Control Tower / Management | Intranet SharePoint |
| `pipeline_run_log.txt` | TXT | Audit trail | Retained in output directory |

---

## 🎯 Remediation SLAs

| Gap Type | HIGH Risk | MEDIUM Risk | LOW Risk |
|----------|-----------|-------------|----------|
| Missing Connection | 7 days 🔴 | 30 days 🟠 | 90 days 🟢 |
| Stale Review | 3 days 🔴 | 14 days 🟠 | 30 days 🟢 |
| Undocumented Connection | 24 hours 🔴 | 7 days 🟠 | 30 days 🟢 |
| Unknown Owner | 48 hours 🔴 | 7 days 🟠 | 30 days 🟢 |
| Missing Review Date | 3 days 🔴 | 14 days 🟠 | 30 days 🟢 |

---

## 🔧 Feeding Rules Engine

The `feeding_rules.yaml` file defines the governance rules for the entire pipeline:

- **Authoritative source** per field — which system owns the data
- **Conflict resolution** — what happens when sources disagree (reject, flag, escalate)
- **Update modes** — automatic, manual, or scheduled
- **Remediation SLAs** — deadlines per gap type and risk range
- **Communication channels** — how each output reaches its audience

---

## 🔄 Data Maintenance Model

### Automatic (every pipeline run)
- Refreshes connection map from all source systems
- Flags stale reviews, missing connections, undocumented entries
- Rebuilds department scorecard and remediation queue
- Regenerates all output files
- Appends timestamped audit log entry

### Manual (defined process)
- Application owners update `connection_log.csv` after each access review
- Data Protection Officer confirms sensitivity classification quarterly
- IAM team updates `iam_product_registry.json` when products change
- Unknown owners resolved within 7 days of gap detection

---

## 🚀 Setup & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the pipeline
python pipeline.py
```

Open `output/iam_governance_report.html` in a browser to view the governance dashboard.

---

## 📈 Sample Output

```
============================================================
  IAM CONNECTION GOVERNANCE PIPELINE
  Run date: 2026-03-09
============================================================

[1/5] Loading data sources...
  ✓ Application inventory: 75 records loaded
  ✓ IAM product registry: 5 products loaded
  ✓ Connection log: 255 connection records loaded

[2/5] Cleaning and standardising data...
  ✓ Missing owners filled: 4 apps
  ✓ Undocumented connections flagged: 10
  ✓ Stale connections flagged: 44

[3/5] Building unified connection map...
  ✓ Unified map built: 255 connection records across 75 applications

[4/5] Classifying risk and detecting gaps...
  ✓ HIGH: 180  MEDIUM: 69  LOW: 6
  ✓ Governance gaps detected: 96

[5/5] Generating outputs...
  ✓ Master map, gap report, scorecard, remediation queue, HTML dashboard
  ✓ 69 CRITICAL items requiring immediate action

============================================================
  PIPELINE COMPLETE — 6 outputs written to ./output/
============================================================
```

---

## 🛠️ Stack

![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat&logo=python)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Processing-green?style=flat)
![YAML](https://img.shields.io/badge/YAML-Config%20Engine-orange?style=flat)
![HTML](https://img.shields.io/badge/HTML-Dashboard-red?style=flat)

- **Python** — pipeline orchestration and data processing
- **pandas** — ingestion, cleaning, merging, classification
- **PyYAML** — feeding rules and remediation config engine
- **HTML/CSS** — stakeholder dashboard (no dependencies, opens in any browser)

---

## 👤 Author

**Pavan Kumar Naganaboina**
MSc Data Management & AI — ECE Paris
[linkedin.com/in/pavankumarn01](https://linkedin.com/in/pavankumarn01) · [github.com/pavansri8886](https://github.com/pavansri8886)

---

> *Built to demonstrate enterprise IAM governance methodology — data consolidation, risk classification, gap detection, feeding rules design, and stakeholder reporting at scale.*

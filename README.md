# IAM Connection Governance Pipeline

A Python project that simulates the exact workflow of an **IAM Application Risk Governance Officer** at a global enterprise — modelled on the CMA CGM Control Tower internship.

It models what happens when application-to-IAM connection data is scattered across multiple repositories, partially missing, stale, and inconsistently maintained. The pipeline ingests those fragmented sources, standardises them, builds a governed connection map, classifies risk by range, detects governance gaps, scores departments, prioritises remediation, and publishes a full HTML governance dashboard.

---

## How this maps directly to the job description

### 1. Reviewing scattered, incomplete, insufficiently structured data
Simulated with three separate source repositories, each with intentional real-world data quality issues:

- `data/application_inventory.csv` — missing owners, missing update dates
- `data/iam_product_registry.json` — IAM policy reference
- `data/connection_log.csv` — stale reviews, pending statuses, undocumented connections, unknown reviewers

### 2. Studying various data repositories on applications
The pipeline treats each source as a distinct governance layer:
- Application inventory → official application register (authoritative for identity fields)
- IAM product registry → policy reference (authoritative for coverage requirements)
- Connection log → operational evidence layer (authoritative for connection status)

Feeding rules for each field are defined in `feeding_rules.yaml`.

### 3. Structuring a connection map with data model, flows, and feeding rules
`pipeline.py` builds a unified connection map using documented feeding rules:
- Application attributes feed from inventory
- IAM product links feed from connection log
- Coverage expectations feed from IAM registry
- Conflict resolution procedures defined per field in `feeding_rules.yaml`

Output: `output/iam_connection_master_map.csv`

### 4. Covering different risk ranges
Every connection is classified as HIGH, MEDIUM, or LOW:

| Risk | Criteria |
|------|----------|
| HIGH | HIGH sensitivity + business critical + Production |
| MEDIUM | MEDIUM sensitivity OR stale review OR pending/undocumented |
| LOW | LOW sensitivity, Development, non-critical |

Department-level risk ratings (CRITICAL / AT RISK / MONITOR / COMPLIANT) in `output/department_risk_scorecard.csv`.

### 5. Data lifecycle management
The pipeline manages the full data lifecycle — ingestion, standardisation, consolidation, classification, gap detection, output generation, and audit logging. Automatic vs manual maintenance responsibilities defined in `feeding_rules.yaml`.

### 6. Simplifying existing processes
The remediation priority queue replaces manual gap triage with a ranked action list — deadlines, responsible owner, and specific action per gap. CRITICAL items surface first with 1-7 day deadlines.

### 7. Data exposure and communication channels
Four channels defined in `feeding_rules.yaml`:
- HTML report → Control Tower and IAM Manager via intranet (weekly)
- Master map CSV → GRC/audit systems via automated integration (every run)
- Gap report → Application owners via email per department (Monday 08:00)
- Remediation queue → ServiceNow tickets for CRITICAL items (real-time)

### 8. Data maintenance model — manual and automatic
Defined per field in `feeding_rules.yaml`:
- **Automatic** — pipeline refreshes connection map, flags stale reviews, regenerates all outputs, appends audit log
- **Manual** — application owners update connection log after reviews, DPO confirms sensitivity quarterly, IAM team updates product registry when products change

---

## Project structure

```
iam-connection-governance-pipeline/
├── data/
│   ├── application_inventory.csv     # 75 enterprise applications
│   ├── iam_product_registry.json     # 5 IAM products with coverage rules
│   └── connection_log.csv            # 255 connection records
├── output/                           # Generated on pipeline run
│   ├── iam_connection_master_map.csv
│   ├── governance_gaps.csv
│   ├── department_risk_scorecard.csv
│   ├── remediation_priority_queue.csv
│   ├── iam_governance_report.html
│   └── pipeline_run_log.txt
├── src/
│   ├── __init__.py
│   ├── risk_classifier.py
│   ├── report_generator.py
│   └── scorecard.py
├── feeding_rules.yaml
├── pipeline.py
├── requirements.txt
└── README.md
```

---

## Data model

### application_inventory.csv
75 applications across Global, EMEA, APAC, Americas.
Departments: Finance, HR, Operations, Logistics, Compliance, IT, Legal, Commercial, Air Cargo, HSE, Sustainability, Strategy, Executive, Communications
Fields: `app_id`, `app_name`, `owner`, `department`, `sub_department`, `environment`, `data_sensitivity`, `business_critical`, `region`, `last_updated`

### iam_product_registry.json
- Azure Active Directory (IAM001)
- Privileged Access Management — PAM (IAM002)
- Role-Based Access Control — RBAC (IAM003)
- Multi-Factor Authentication — MFA (IAM004)
- Identity Governance & Administration — IGA (IAM005)

### connection_log.csv
255 connection records with stale reviews, pending connections, undocumented entries, and missing reviewer information.
Fields: `connection_id`, `app_id`, `iam_product_id`, `connection_status`, `last_reviewed`, `reviewed_by`, `notes`

### feeding_rules.yaml
Defines authoritative source, update mode, conflict resolution, remediation SLAs, and communication channels for every field.

---

## Gap types detected

| Gap Type | Description |
|----------|-------------|
| MISSING_CONNECTION | Required IAM product not connected for app sensitivity level |
| STALE_REVIEW | Connection not reviewed within defined cycle |
| UNDOCUMENTED_CONNECTION | Connection exists with no documented status |
| UNKNOWN_OWNER | Application has no registered owner |
| MISSING_REVIEW_DATE | Active connection with no review date recorded |

---

## Outputs

| File | Audience | Channel |
|------|----------|---------|
| `iam_connection_master_map.csv` | GRC / audit systems | Automated integration |
| `governance_gaps.csv` | Application owners | Email per department |
| `department_risk_scorecard.csv` | IAM Manager | Internal reporting |
| `remediation_priority_queue.csv` | Application owners + IAM team | ServiceNow + email |
| `iam_governance_report.html` | Control Tower + management | Intranet SharePoint |
| `pipeline_run_log.txt` | Audit trail | Retained in output |

---

## Enterprise applications included

SAP HR Core, SAP Finance ERP, Vessel Tracking System, Customer Portal, Freight Booking Platform, CEVA Logistics TMS, Air Cargo Booking System, Customs Clearance Platform, Trade Finance Platform, Sanctions Screening Tool, Anti-Money Laundering System, Board Portal, M&A Dataroom, Kubernetes Cluster, API Gateway, Data Warehouse, SIEM Splunk, and 50+ more.

---

## How to run

```bash
pip install -r requirements.txt
python pipeline.py
```

Open `output/iam_governance_report.html` in a browser to view the governance dashboard.

---

## Stack
Python 3.8+ · pandas · PyYAML · HTML/CSS

---

## Author
Pavan Kumar Naganaboina
MSc Data Management & AI, ECE Paris
linkedin.com/in/pavankumarn01

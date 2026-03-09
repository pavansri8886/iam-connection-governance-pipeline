"""
IAM Connection Governance Pipeline
===================================
Ingests scattered application and IAM connection data from multiple sources,
consolidates into a unified governance map, classifies by risk range,
detects gaps, and produces a structured report with stakeholder-facing output.

Author: Pavan Kumar Naganaboina
"""

import pandas as pd
import json
import os
from datetime import datetime, timedelta
from src.risk_classifier import classify_risk, detect_gaps
from src.report_generator import generate_html_report, generate_master_map
from src.scorecard import build_department_scorecard, build_remediation_queue

# ─── Configuration ────────────────────────────────────────────────────────────
DATA_DIR = "data"
OUTPUT_DIR = "output"
STALE_THRESHOLD_DAYS = 180  # connections not reviewed in 6 months flagged as stale
TODAY = datetime.today()

def load_sources():
    """
    Step 1 – Ingest data from multiple scattered repositories.
    Simulates the real-world problem: three separate sources,
    each with inconsistencies, missing fields, and varying formats.
    """
    print("\n[1/5] Loading data sources...")

    # Source 1: Application inventory (CSV)
    apps = pd.read_csv(os.path.join(DATA_DIR, "application_inventory.csv"))
    print(f"  ✓ Application inventory: {len(apps)} records loaded")

    # Source 2: IAM product registry (JSON)
    with open(os.path.join(DATA_DIR, "iam_product_registry.json")) as f:
        iam_raw = json.load(f)
    iam_products = pd.DataFrame(iam_raw["iam_products"])
    print(f"  ✓ IAM product registry: {len(iam_products)} products loaded")

    # Source 3: Connection log (CSV)
    connections = pd.read_csv(os.path.join(DATA_DIR, "connection_log.csv"))
    print(f"  ✓ Connection log: {len(connections)} connection records loaded")

    return apps, iam_products, connections


def clean_and_standardise(apps, iam_products, connections):
    """
    Step 2 – Clean and standardise data across all three sources.
    Handles missing values, inconsistent formats, and data quality issues.
    This mirrors the 'review of existing information' task in the role.
    """
    print("\n[2/5] Cleaning and standardising data...")

    # --- Applications ---
    apps["owner"] = apps["owner"].fillna("UNKNOWN")
    apps["department"] = apps["department"].fillna("UNKNOWN")
    apps["data_sensitivity"] = apps["data_sensitivity"].str.upper().str.strip()
    apps["last_updated"] = pd.to_datetime(apps["last_updated"], errors="coerce")
    apps["business_critical"] = apps["business_critical"].fillna("No")

    # --- Connections ---
    connections["connection_status"] = connections["connection_status"].str.strip()
    connections["connection_status"] = connections["connection_status"].fillna("UNDOCUMENTED")
    connections["last_reviewed"] = pd.to_datetime(connections["last_reviewed"], errors="coerce")
    connections["reviewed_by"] = connections["reviewed_by"].fillna("UNKNOWN")

    # Flag stale connections
    connections["days_since_review"] = (TODAY - connections["last_reviewed"]).dt.days
    connections["is_stale"] = connections["days_since_review"] > STALE_THRESHOLD_DAYS

    print(f"  ✓ Missing owners filled: {(apps['owner'] == 'UNKNOWN').sum()} apps")
    print(f"  ✓ Undocumented connections flagged: {(connections['connection_status'] == 'UNDOCUMENTED').sum()}")
    print(f"  ✓ Stale connections flagged: {connections['is_stale'].sum()}")

    return apps, iam_products, connections


def build_connection_map(apps, iam_products, connections):
    """
    Step 3 – Consolidate into unified connection map.
    Defines the data model, feeding rules, and ownership.
    Feeding rules:
      - Application metadata feeds from application_inventory (authoritative source)
      - IAM product details feed from iam_product_registry (authoritative source)
      - Connection status feeds from connection_log (updated manually by reviewers)
    """
    print("\n[3/5] Building unified connection map...")

    # Merge connections with application details
    map_df = connections.merge(
        apps[["app_id", "app_name", "owner", "department", "environment",
              "data_sensitivity", "business_critical"]],
        on="app_id", how="left"
    )

    # Merge with IAM product details
    map_df = map_df.merge(
        iam_products[["product_id", "product_name", "type", "review_cycle_days"]],
        left_on="iam_product_id", right_on="product_id", how="left"
    )

    print(f"  ✓ Unified map built: {len(map_df)} connection records across {map_df['app_id'].nunique()} applications")
    return map_df


def classify_and_detect_gaps(map_df, apps, iam_products):
    """
    Step 4 – Classify by risk range and detect governance gaps.
    Risk classification logic:
      HIGH   – HIGH sensitivity + business critical + Production environment
      MEDIUM – MEDIUM sensitivity OR missing connections OR stale reviews
      LOW    – LOW sensitivity, Development environment, non-critical
    Gap detection covers:
      - Missing required IAM connections for HIGH sensitivity apps
      - Stale connection reviews
      - Undocumented connections
      - Unknown ownership
    """
    print("\n[4/5] Classifying risk and detecting gaps...")

    map_df = classify_risk(map_df)
    gaps_df = detect_gaps(map_df, apps, iam_products)

    risk_counts = map_df["risk_range"].value_counts()
    print(f"  ✓ Risk classification complete:")
    for level in ["HIGH", "MEDIUM", "LOW"]:
        print(f"      {level}: {risk_counts.get(level, 0)} connections")
    print(f"  ✓ Governance gaps detected: {len(gaps_df)}")

    return map_df, gaps_df


def expose_and_maintain(map_df, gaps_df, apps, iam_products):
    """
    Step 5 – Data exposure and maintenance model.
    
    AUTOMATIC maintenance (this script):
      - Runs on schedule to refresh connection map from source systems
      - Automatically flags stale reviews and missing connections
      - Regenerates HTML report and master map CSV on each run
    
    MANUAL maintenance (defined process):
      - Reviewers update connection_log.csv after each access review
      - Application owners confirm sensitivity classification quarterly
      - IAM team updates iam_product_registry.json when products change
    
    Communication channels:
      - HTML report → shared with management and IAM team via intranet
      - Master map CSV → ingested by GRC tooling and audit systems
      - Gap report → distributed to application owners for remediation
    """
    print("\n[5/5] Generating outputs and exposing data...")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Output 1: Master governance map (for GRC/audit systems)
    master_map_path = os.path.join(OUTPUT_DIR, "iam_connection_master_map.csv")
    generate_master_map(map_df, master_map_path)
    print(f"  ✓ Master map saved: {master_map_path}")

    # Output 2: Gap report (for application owners)
    gap_report_path = os.path.join(OUTPUT_DIR, "governance_gaps.csv")
    gaps_df.to_csv(gap_report_path, index=False)
    print(f"  ✓ Gap report saved: {gap_report_path} ({len(gaps_df)} gaps)")

    # Output 3: Department risk scorecard
    scorecard_df = build_department_scorecard(map_df, apps)
    scorecard_path = os.path.join(OUTPUT_DIR, "department_risk_scorecard.csv")
    scorecard_df.to_csv(scorecard_path, index=False)
    print(f"  ✓ Department scorecard saved: {scorecard_path} ({len(scorecard_df)} departments)")

    # Output 4: Remediation priority queue
    queue_df = build_remediation_queue(gaps_df, "feeding_rules.yaml")
    queue_path = os.path.join(OUTPUT_DIR, "remediation_priority_queue.csv")
    queue_df.to_csv(queue_path, index=False)
    critical = (queue_df["priority"] == "CRITICAL").sum() if not queue_df.empty else 0
    print(f"  ✓ Remediation queue saved: {queue_path} ({critical} CRITICAL items)")

    # Output 5: HTML governance dashboard (for management/Control Tower)
    html_path = os.path.join(OUTPUT_DIR, "iam_governance_report.html")
    generate_html_report(map_df, gaps_df, apps, scorecard_df, queue_df, html_path)
    print(f"  ✓ HTML governance report saved: {html_path}")

    # Output 6: Run log (audit trail)
    log_path = os.path.join(OUTPUT_DIR, "pipeline_run_log.txt")
    with open(log_path, "a") as log:
        log.write(f"{TODAY.strftime('%Y-%m-%d %H:%M:%S')} | Pipeline run complete | "
                  f"Apps: {apps['app_id'].nunique()} | "
                  f"Connections: {len(map_df)} | "
                  f"Gaps: {len(gaps_df)} | "
                  f"Critical: {critical}\n")
    print(f"  ✓ Run log updated: {log_path}")


def main():
    print("=" * 60)
    print("  IAM CONNECTION GOVERNANCE PIPELINE")
    print(f"  Run date: {TODAY.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    apps, iam_products, connections = load_sources()
    apps, iam_products, connections = clean_and_standardise(apps, iam_products, connections)
    map_df = build_connection_map(apps, iam_products, connections)
    map_df, gaps_df = classify_and_detect_gaps(map_df, apps, iam_products)
    expose_and_maintain(map_df, gaps_df, apps, iam_products)

    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)

    # Summary
    high = (map_df["risk_range"] == "HIGH").sum()
    medium = (map_df["risk_range"] == "MEDIUM").sum()
    low = (map_df["risk_range"] == "LOW").sum()
    print(f"\n  Connection risk summary:")
    print(f"    HIGH   : {high}")
    print(f"    MEDIUM : {medium}")
    print(f"    LOW    : {low}")
    print(f"    GAPS   : {len(gaps_df)}")
    print(f"\n  Outputs written to: ./{OUTPUT_DIR}/")


if __name__ == "__main__":
    main()

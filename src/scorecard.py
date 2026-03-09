"""
Department Risk Scorecard & Remediation Priority Queue
=======================================================
Generates two governance deliverables:
  1. Department-level risk scorecard — coverage %, gap count, risk exposure per department
  2. Remediation priority queue — ranked gaps with deadlines based on feeding_rules.yaml
"""

import pandas as pd
import yaml
from datetime import datetime, timedelta

TODAY = datetime.today()


def load_feeding_rules(rules_path: str = "feeding_rules.yaml") -> dict:
    """Load remediation rules and communication channels from feeding_rules.yaml."""
    with open(rules_path, "r") as f:
        return yaml.safe_load(f)


def build_department_scorecard(map_df: pd.DataFrame, apps: pd.DataFrame) -> pd.DataFrame:
    """
    Builds a department-level risk scorecard.
    
    For each department shows:
    - Total applications
    - Applications with full IAM coverage
    - Coverage percentage
    - HIGH/MEDIUM/LOW connection counts
    - Stale review count
    - Overall department risk rating
    """
    # Total apps per department
    dept_apps = apps.groupby("department").agg(
        total_apps=("app_id", "count"),
        high_sensitivity_apps=("data_sensitivity", lambda x: (x == "HIGH").sum()),
        critical_apps=("business_critical", lambda x: (x == "Yes").sum())
    ).reset_index()

    # Connection stats per department
    dept_connections = map_df.groupby("department").agg(
        total_connections=("connection_id", "count"),
        active_connections=("connection_status", lambda x: (x.str.upper() == "ACTIVE").sum()),
        high_risk_connections=("risk_range", lambda x: (x == "HIGH").sum()),
        medium_risk_connections=("risk_range", lambda x: (x == "MEDIUM").sum()),
        low_risk_connections=("risk_range", lambda x: (x == "LOW").sum()),
        stale_connections=("is_stale", "sum"),
        undocumented=("connection_status", lambda x: (x.str.upper() == "UNDOCUMENTED").sum())
    ).reset_index()

    scorecard = dept_apps.merge(dept_connections, on="department", how="left").fillna(0)

    # Coverage % = active connections / total connections
    scorecard["coverage_pct"] = (
        scorecard["active_connections"] / scorecard["total_connections"].replace(0, 1) * 100
    ).round(1)

    # Department risk rating
    def dept_risk_rating(row):
        if row["high_sensitivity_apps"] > 0 and row["coverage_pct"] < 80:
            return "CRITICAL"
        elif row["coverage_pct"] < 90 or row["stale_connections"] > 3:
            return "AT RISK"
        elif row["coverage_pct"] >= 95 and row["stale_connections"] == 0:
            return "COMPLIANT"
        else:
            return "MONITOR"

    scorecard["risk_rating"] = scorecard.apply(dept_risk_rating, axis=1)

    return scorecard.sort_values(
        ["risk_rating", "high_sensitivity_apps"], 
        ascending=[True, False]
    ).reset_index(drop=True)


def build_remediation_queue(gaps_df: pd.DataFrame, rules_path: str = "feeding_rules.yaml") -> pd.DataFrame:
    """
    Builds a prioritised remediation queue from detected gaps.
    
    Applies remediation rules from feeding_rules.yaml to assign:
    - Priority level (CRITICAL / HIGH / MEDIUM / LOW)
    - Deadline date
    - Responsible owner type
    - Recommended action
    
    Sorted by priority then deadline — most urgent items first.
    """
    if gaps_df.empty:
        return pd.DataFrame()

    rules = load_feeding_rules(rules_path)
    remediation_rules = rules.get("remediation_rules", {})

    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

    queue_rows = []
    for _, gap in gaps_df.iterrows():
        gap_type = gap.get("gap_type", "")
        risk_range = str(gap.get("risk_range", "MEDIUM")).upper()

        # Look up rule
        rule = remediation_rules.get(gap_type, {}).get(risk_range, {})
        if not rule:
            # Default if not found
            rule = {
                "deadline_days": 30,
                "priority": "MEDIUM",
                "owner": "application_owner",
                "action": "Review and remediate within 30 days."
            }

        deadline = TODAY + timedelta(days=rule["deadline_days"])

        queue_rows.append({
            "priority": rule["priority"],
            "gap_type": gap_type,
            "risk_range": risk_range,
            "app_id": gap.get("app_id", ""),
            "app_name": gap.get("app_name", ""),
            "detail": gap.get("detail", ""),
            "recommended_action": rule["action"],
            "responsible_owner": rule["owner"],
            "deadline": deadline.strftime("%Y-%m-%d"),
            "deadline_days": rule["deadline_days"]
        })

    queue_df = pd.DataFrame(queue_rows)

    # Sort: CRITICAL first, then by deadline
    queue_df["priority_order"] = queue_df["priority"].map(priority_order).fillna(4)
    queue_df = queue_df.sort_values(
        ["priority_order", "deadline_days"]
    ).drop(columns=["priority_order"]).reset_index(drop=True)

    return queue_df

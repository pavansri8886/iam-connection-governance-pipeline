"""
Risk Classification and Gap Detection Module
============================================
Classifies each application-IAM connection by risk range
and detects governance gaps across the connection map.
"""

import pandas as pd
from datetime import datetime, timedelta

TODAY = datetime.today()

# IAM products required for HIGH sensitivity production applications
REQUIRED_FOR_HIGH = ["IAM001", "IAM002", "IAM003", "IAM004", "IAM005"]
# IAM products required for MEDIUM sensitivity production applications
REQUIRED_FOR_MEDIUM = ["IAM001", "IAM003", "IAM004"]


def classify_risk(map_df: pd.DataFrame) -> pd.DataFrame:
    """
    Classifies each connection record by risk range.

    Risk logic:
      HIGH   – HIGH data sensitivity AND business critical AND Production
      MEDIUM – MEDIUM sensitivity OR stale review OR pending/undocumented status
      LOW    – Everything else (LOW sensitivity, Development, non-critical)
    """
    def get_risk(row):
        sensitivity = str(row.get("data_sensitivity", "")).upper()
        environment = str(row.get("environment", "")).strip()
        business_critical = str(row.get("business_critical", "No")).strip()
        status = str(row.get("connection_status", "")).strip().upper()
        is_stale = row.get("is_stale", False)

        # HIGH risk conditions
        if (sensitivity == "HIGH"
                and business_critical == "Yes"
                and environment == "Production"):
            return "HIGH"

        # MEDIUM risk conditions
        if (sensitivity == "MEDIUM"
                or is_stale
                or status in ["PENDING", "UNDOCUMENTED", ""]):
            return "MEDIUM"

        return "LOW"

    map_df["risk_range"] = map_df.apply(get_risk, axis=1)
    return map_df


def detect_gaps(map_df: pd.DataFrame, apps: pd.DataFrame,
                iam_products: pd.DataFrame) -> pd.DataFrame:
    """
    Detects governance gaps across the connection map.

    Gap types:
      MISSING_CONNECTION   – Required IAM product not connected for HIGH/MEDIUM app
      STALE_REVIEW         – Connection not reviewed within required cycle
      UNDOCUMENTED         – Connection exists but has no documentation
      UNKNOWN_OWNER        – Application has no registered owner
      MISSING_REVIEW_DATE  – Active connection with no review date recorded
    """
    gaps = []

    # Gap Type 1: Missing required IAM connections
    high_apps = apps[
        (apps["data_sensitivity"] == "HIGH") &
        (apps["business_critical"] == "Yes") &
        (apps["environment"] == "Production")
    ]["app_id"].tolist()

    medium_apps = apps[
        apps["data_sensitivity"] == "MEDIUM"
    ]["app_id"].tolist()

    for app_id in high_apps:
        connected = map_df[map_df["app_id"] == app_id]["iam_product_id"].tolist()
        for required in REQUIRED_FOR_HIGH:
            if required not in connected:
                app_name = apps[apps["app_id"] == app_id]["app_name"].values
                app_name = app_name[0] if len(app_name) > 0 else app_id
                gaps.append({
                    "gap_type": "MISSING_CONNECTION",
                    "risk_range": "HIGH",
                    "app_id": app_id,
                    "app_name": app_name,
                    "detail": f"Required IAM product {required} not connected",
                    "recommended_action": f"Connect {app_id} to {required} immediately"
                })

    for app_id in medium_apps:
        connected = map_df[map_df["app_id"] == app_id]["iam_product_id"].tolist()
        for required in REQUIRED_FOR_MEDIUM:
            if required not in connected:
                app_name = apps[apps["app_id"] == app_id]["app_name"].values
                app_name = app_name[0] if len(app_name) > 0 else app_id
                gaps.append({
                    "gap_type": "MISSING_CONNECTION",
                    "risk_range": "MEDIUM",
                    "app_id": app_id,
                    "app_name": app_name,
                    "detail": f"Required IAM product {required} not connected",
                    "recommended_action": f"Connect {app_id} to {required} within 30 days"
                })

    # Gap Type 2: Stale reviews
    stale = map_df[map_df["is_stale"] == True]
    for _, row in stale.iterrows():
        days = int(row["days_since_review"]) if pd.notna(row["days_since_review"]) else "unknown"
        gaps.append({
            "gap_type": "STALE_REVIEW",
            "risk_range": row.get("risk_range", "UNKNOWN"),
            "app_id": row["app_id"],
            "app_name": row.get("app_name", row["app_id"]),
            "detail": f"Last reviewed {days} days ago (threshold: 180 days)",
            "recommended_action": "Schedule immediate access review with application owner"
        })

    # Gap Type 3: Undocumented connections
    undoc = map_df[map_df["connection_status"].str.upper() == "UNDOCUMENTED"]
    for _, row in undoc.iterrows():
        gaps.append({
            "gap_type": "UNDOCUMENTED_CONNECTION",
            "risk_range": row.get("risk_range", "MEDIUM"),
            "app_id": row["app_id"],
            "app_name": row.get("app_name", row["app_id"]),
            "detail": f"Connection {row['connection_id']} has no documented status",
            "recommended_action": "Review and document connection status within 14 days"
        })

    # Gap Type 4: Unknown application owners
    unknown_owners = map_df[map_df["owner"] == "UNKNOWN"]["app_id"].unique()
    for app_id in unknown_owners:
        app_name = apps[apps["app_id"] == app_id]["app_name"].values
        app_name = app_name[0] if len(app_name) > 0 else app_id
        gaps.append({
            "gap_type": "UNKNOWN_OWNER",
            "risk_range": "MEDIUM",
            "app_id": app_id,
            "app_name": app_name,
            "detail": "No registered application owner",
            "recommended_action": "Assign owner in application inventory within 7 days"
        })

    # Gap Type 5: Active connections with no review date
    no_date = map_df[
        (map_df["connection_status"].str.upper() == "ACTIVE") &
        (map_df["last_reviewed"].isna())
    ]
    for _, row in no_date.iterrows():
        gaps.append({
            "gap_type": "MISSING_REVIEW_DATE",
            "risk_range": row.get("risk_range", "MEDIUM"),
            "app_id": row["app_id"],
            "app_name": row.get("app_name", row["app_id"]),
            "detail": f"Active connection {row['connection_id']} has no review date recorded",
            "recommended_action": "Confirm review date with application owner"
        })

    gaps_df = pd.DataFrame(gaps)
    if not gaps_df.empty:
        # Deduplicate unknown owner gaps
        gaps_df = gaps_df.drop_duplicates(
            subset=["gap_type", "app_id", "detail"]
        ).reset_index(drop=True)

    return gaps_df

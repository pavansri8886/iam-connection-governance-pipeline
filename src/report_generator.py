"""
Report Generator Module
=======================
Generates stakeholder-facing outputs from the unified connection map.
Two outputs:
  1. Master map CSV  — for GRC/audit systems (structured, machine-readable)
  2. HTML dashboard  — for management and Control Tower team (visual, human-readable)
"""

import pandas as pd
from datetime import datetime

TODAY = datetime.today().strftime("%Y-%m-%d")


def generate_master_map(map_df: pd.DataFrame, output_path: str):
    """Exports the unified connection map as a structured CSV for audit systems."""
    cols = [
        "connection_id", "app_id", "app_name", "owner", "department",
        "environment", "data_sensitivity", "business_critical",
        "iam_product_id", "product_name", "type",
        "connection_status", "last_reviewed", "reviewed_by",
        "days_since_review", "is_stale", "risk_range"
    ]
    export_cols = [c for c in cols if c in map_df.columns]
    map_df[export_cols].to_csv(output_path, index=False)


def generate_html_report(map_df: pd.DataFrame, gaps_df: pd.DataFrame,
                          apps: pd.DataFrame, scorecard_df: pd.DataFrame,
                          queue_df: pd.DataFrame, output_path: str):
    """
    Generates an HTML governance dashboard for the Control Tower team.
    Designed to be shared via intranet or email without requiring
    any tooling on the recipient's side.
    """

    # Summary stats
    total_apps = apps["app_id"].nunique()
    total_connections = len(map_df)
    high_count = (map_df["risk_range"] == "HIGH").sum()
    medium_count = (map_df["risk_range"] == "MEDIUM").sum()
    low_count = (map_df["risk_range"] == "LOW").sum()
    total_gaps = len(gaps_df)
    stale_count = map_df["is_stale"].sum()

    # Risk badge colours
    def risk_badge(risk):
        colours = {"HIGH": "#c0392b", "MEDIUM": "#e67e22", "LOW": "#27ae60"}
        colour = colours.get(str(risk).upper(), "#7f8c8d")
        return f'<span style="background:{colour};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold;">{risk}</span>'

    def status_badge(status):
        colours = {"ACTIVE": "#27ae60", "PENDING": "#e67e22",
                   "UNDOCUMENTED": "#c0392b", "UNKNOWN": "#7f8c8d"}
        colour = colours.get(str(status).upper(), "#7f8c8d")
        return f'<span style="background:{colour};color:white;padding:2px 8px;border-radius:4px;font-size:12px;">{status}</span>'

    # Department scorecard rows
    rating_colours = {
        "CRITICAL": "#c0392b", "AT RISK": "#e67e22",
        "MONITOR": "#f39c12", "COMPLIANT": "#27ae60"
    }

    scorecard_rows = ""
    for _, row in scorecard_df.iterrows():
        colour = rating_colours.get(str(row.get("risk_rating", "")), "#7f8c8d")
        badge = f'<span style="background:{colour};color:white;padding:2px 10px;border-radius:4px;font-size:12px;font-weight:bold;">{row.get("risk_rating","")}</span>'
        cov = row.get("coverage_pct", 0)
        bar_colour = "#27ae60" if cov >= 95 else "#e67e22" if cov >= 80 else "#c0392b"
        cov_bar = f'<div style="background:#eee;border-radius:4px;height:10px;width:100%;"><div style="background:{bar_colour};width:{min(cov,100)}%;height:10px;border-radius:4px;"></div></div><small>{cov}%</small>'
        scorecard_rows += f"""
        <tr>
          <td><strong>{row['department']}</strong></td>
          <td>{int(row.get('total_apps',0))}</td>
          <td>{int(row.get('high_sensitivity_apps',0))}</td>
          <td>{cov_bar}</td>
          <td style="color:#c0392b;">{int(row.get('stale_connections',0))}</td>
          <td>{int(row.get('high_risk_connections',0))}</td>
          <td>{badge}</td>
        </tr>"""

    # Remediation queue rows — top 20 only for HTML
    priority_colours = {
        "CRITICAL": "#c0392b", "HIGH": "#e67e22",
        "MEDIUM": "#f39c12", "LOW": "#27ae60"
    }
    queue_rows_html = ""
    display_queue = queue_df.head(20) if not queue_df.empty else pd.DataFrame()
    for _, row in display_queue.iterrows():
        colour = priority_colours.get(str(row.get("priority", "")), "#7f8c8d")
        badge = f'<span style="background:{colour};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold;">{row.get("priority","")}</span>'
        queue_rows_html += f"""
        <tr>
          <td>{badge}</td>
          <td>{row.get('gap_type','')}</td>
          <td><strong>{row.get('app_name','')}</strong></td>
          <td>{row.get('detail','')}</td>
          <td style="color:#e67e22;">{row.get('recommended_action','')}</td>
          <td><strong>{row.get('deadline','')}</strong></td>
          <td>{row.get('responsible_owner','')}</td>
        </tr>"""

    critical_count = (queue_df["priority"] == "CRITICAL").sum() if not queue_df.empty else 0
    compliant_depts = (scorecard_df["risk_rating"] == "COMPLIANT").sum() if not scorecard_df.empty else 0
    app_summary = map_df.groupby(
        ["app_id", "app_name", "department", "data_sensitivity",
         "business_critical", "owner"]
    ).agg(
        total_connections=("connection_id", "count"),
        active_connections=("connection_status", lambda x: (x.str.upper() == "ACTIVE").sum()),
        high_risk=("risk_range", lambda x: (x == "HIGH").sum()),
        stale=("is_stale", "sum")
    ).reset_index()

    app_rows = ""
    for _, row in app_summary.iterrows():
        sensitivity = str(row["data_sensitivity"]).upper()
        badge = risk_badge("HIGH" if sensitivity == "HIGH" else
                           "MEDIUM" if sensitivity == "MEDIUM" else "LOW")
        stale_cell = (f'<span style="color:#c0392b;font-weight:bold;">{int(row["stale"])}</span>'
                      if row["stale"] > 0 else "0")
        app_rows += f"""
        <tr>
          <td>{row['app_id']}</td>
          <td><strong>{row['app_name']}</strong></td>
          <td>{row['department']}</td>
          <td>{badge}</td>
          <td>{row['owner']}</td>
          <td>{int(row['active_connections'])}/{int(row['total_connections'])}</td>
          <td>{stale_cell}</td>
        </tr>"""

    # Gaps table
    gap_rows = ""
    if not gaps_df.empty:
        for _, row in gaps_df.iterrows():
            gap_rows += f"""
            <tr>
              <td>{risk_badge(row.get('risk_range','UNKNOWN'))}</td>
              <td><strong>{row.get('gap_type','')}</strong></td>
              <td>{row.get('app_name', row.get('app_id',''))}</td>
              <td>{row.get('detail','')}</td>
              <td style="color:#e67e22;">{row.get('recommended_action','')}</td>
            </tr>"""
    else:
        gap_rows = '<tr><td colspan="5" style="text-align:center;color:#27ae60;">No governance gaps detected</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>IAM Connection Governance Report - {TODAY}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f6f9; color: #2c3e50; }}
  .header {{ background: #003087; color: white; padding: 32px 40px; }}
  .header h1 {{ font-size: 26px; font-weight: 300; letter-spacing: 1px; }}
  .header p {{ font-size: 13px; opacity: 0.7; margin-top: 6px; }}
  .container {{ max-width: 1300px; margin: 0 auto; padding: 32px 24px; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(8, 1fr); gap: 12px; margin-bottom: 32px; }}
  .card {{ background: white; border-radius: 8px; padding: 16px; text-align: center;
           box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .card .number {{ font-size: 28px; font-weight: 700; margin-bottom: 4px; }}
  .card .label {{ font-size: 11px; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; }}
  .card.high .number {{ color: #c0392b; }}
  .card.medium .number {{ color: #e67e22; }}
  .card.low .number {{ color: #27ae60; }}
  .card.critical .number {{ color: #c0392b; }}
  .card.compliant .number {{ color: #27ae60; }}
  .section {{ background: white; border-radius: 8px; padding: 24px;
              box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 24px; }}
  .section h2 {{ font-size: 16px; font-weight: 600; color: #003087;
                 border-bottom: 2px solid #003087; padding-bottom: 10px; margin-bottom: 18px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #f8f9fa; padding: 10px 12px; text-align: left;
        font-weight: 600; color: #555; border-bottom: 2px solid #e9ecef; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }}
  tr:hover td {{ background: #fafbfc; }}
  .footer {{ text-align: center; font-size: 12px; color: #aaa; padding: 24px; }}
  .maintenance-box {{ background: #f8f9fa; border-left: 4px solid #003087;
                      padding: 16px 20px; border-radius: 4px; font-size: 13px; margin-bottom: 12px; }}
  .maintenance-box h3 {{ font-size: 14px; color: #003087; margin-bottom: 8px; }}
  .maintenance-box ul {{ margin-left: 18px; line-height: 2; }}
  .nav {{ display: flex; gap: 8px; margin-bottom: 24px; flex-wrap: wrap; }}
  .nav a {{ background: #003087; color: white; padding: 8px 16px; border-radius: 4px;
            text-decoration: none; font-size: 13px; }}
  .nav a:hover {{ background: #00205c; }}
</style>
</head>
<body>
<div class="header">
  <h1>IAM Application Connection Governance Report</h1>
  <p>Control Tower · Generated: {TODAY} · 75 Applications · {total_connections} Connections · {total_gaps} Gaps</p>
</div>
<div class="container">

  <div class="nav">
    <a href="#summary">Summary</a>
    <a href="#scorecard">Department Scorecard</a>
    <a href="#remediation">Remediation Queue</a>
    <a href="#appmap">Application Map</a>
    <a href="#gaps">All Gaps</a>
    <a href="#maintenance">Maintenance Model</a>
  </div>

  <div class="summary-grid" id="summary">
    <div class="card"><div class="number">{total_apps}</div><div class="label">Applications</div></div>
    <div class="card"><div class="number">{total_connections}</div><div class="label">Connections</div></div>
    <div class="card high"><div class="number">{high_count}</div><div class="label">High Risk</div></div>
    <div class="card medium"><div class="number">{medium_count}</div><div class="label">Medium Risk</div></div>
    <div class="card low"><div class="number">{low_count}</div><div class="label">Low Risk</div></div>
    <div class="card critical"><div class="number">{critical_count}</div><div class="label">Critical Items</div></div>
    <div class="card"><div class="number">{total_gaps}</div><div class="label">Total Gaps</div></div>
    <div class="card compliant"><div class="number">{compliant_depts}</div><div class="label">Compliant Depts</div></div>
  </div>

  <div class="section" id="scorecard">
    <h2>Department Risk Scorecard</h2>
    <table>
      <thead>
        <tr>
          <th>Department</th><th>Total Apps</th><th>HIGH Sensitivity</th>
          <th>IAM Coverage</th><th>Stale Reviews</th><th>HIGH Risk Connections</th><th>Risk Rating</th>
        </tr>
      </thead>
      <tbody>{scorecard_rows}</tbody>
    </table>
  </div>

  <div class="section" id="remediation">
    <h2>Remediation Priority Queue — Top 20 Critical Items</h2>
    <table>
      <thead>
        <tr>
          <th>Priority</th><th>Gap Type</th><th>Application</th>
          <th>Detail</th><th>Action</th><th>Deadline</th><th>Owner</th>
        </tr>
      </thead>
      <tbody>{queue_rows_html}</tbody>
    </table>
  </div>

  <div class="section" id="appmap">
    <h2>Application Connection Map</h2>
    <table>
      <thead>
        <tr>
          <th>App ID</th><th>Application</th><th>Department</th>
          <th>Sensitivity</th><th>Owner</th>
          <th>Active / Total Connections</th><th>Stale Reviews</th>
        </tr>
      </thead>
      <tbody>{app_rows}</tbody>
    </table>
  </div>

  <div class="section" id="gaps">
    <h2>All Governance Gaps — {total_gaps} identified</h2>
    <table>
      <thead>
        <tr>
          <th>Risk</th><th>Gap Type</th><th>Application</th>
          <th>Detail</th><th>Recommended Action</th>
        </tr>
      </thead>
      <tbody>{gap_rows}</tbody>
    </table>
  </div>

  <div class="section" id="maintenance">
    <h2>Data Maintenance Model</h2>
    <div class="maintenance-box">
      <h3>Automatic (this pipeline)</h3>
      <ul>
        <li>Runs on schedule to refresh connection map from all source systems</li>
        <li>Flags stale reviews, missing connections, and undocumented entries automatically</li>
        <li>Rebuilds department scorecard and remediation priority queue on every run</li>
        <li>Regenerates HTML report, master map CSV, and gap report on each run</li>
        <li>Appends audit log entry per run for full traceability</li>
      </ul>
    </div>
    <div class="maintenance-box" style="border-left-color:#e67e22;">
      <h3>Manual (defined process — see feeding_rules.yaml)</h3>
      <ul>
        <li>Application owners update connection_log.csv after each access review</li>
        <li>Sensitivity classification confirmed by Data Protection Officer quarterly</li>
        <li>IAM team updates iam_product_registry.json when products are added or retired</li>
        <li>Unknown owners resolved within 7 days of gap detection</li>
        <li>Feeding rules reviewed annually by IAM governance team</li>
      </ul>
    </div>
    <div class="maintenance-box" style="border-left-color:#27ae60;">
      <h3>Communication Channels</h3>
      <ul>
        <li>HTML report → Control Tower team via intranet SharePoint (weekly)</li>
        <li>Master map CSV → GRC tooling and audit systems via automated integration</li>
        <li>Gap report → Application owners via email distribution list (weekly Monday 08:00)</li>
        <li>Remediation queue → ServiceNow tickets raised automatically for CRITICAL items</li>
      </ul>
    </div>
  </div>

</div>
<div class="footer">IAM Connection Governance Pipeline · CMA CGM Control Tower Simulation · {TODAY}</div>
</body>
</html>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

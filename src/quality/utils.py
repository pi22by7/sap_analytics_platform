"""
Reporting and Visualization utilities.
"""

import json
from pathlib import Path


def generate_html_report(results, output_path):
    """Generates the HTML dashboard with embedded CSS visualizations."""

    # Simple CSS Bar for "Histogram" effect
    def _bar(pct, color="blue"):
        return f'<div style="width:{pct}%; background:{color}; height:10px; border-radius:2px;"></div>'

    rows = ""
    for check in results["checks"]:
        # Color coding
        status_color = (
            "#e6fffa"
            if check["status"] == "PASS"
            else "#ffe3e3" if check["status"] == "FAIL" else "#fffbea"
        )
        text_color = (
            "green"
            if check["status"] == "PASS"
            else "red" if check["status"] == "FAIL" else "orange"
        )

        # Example failures
        examples = ""
        if check["examples"]:
            examples = (
                f"<br><small>Examples: {', '.join(map(str, check['examples']))}</small>"
            )

        rows += f"""
        <tr style="background-color: {status_color}">
            <td>{check['category']}</td>
            <td><strong>{check['name']}</strong></td>
            <td style="color:{text_color}"><strong>{check['status']}</strong></td>
            <td>{check['message']}{examples}</td>
            <td>{check.get('severity', 'Info')}</td>
        </tr>
        """

    # Stats Summary
    stats = results["profile"]

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SAP Data Quality Dashboard</title>
        <style>
            body {{ font-family: -apple-system, sans-serif; padding: 20px; background: #f4f6f8; }}
            .card {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ text-align: left; padding: 12px; background: #f8f9fa; border-bottom: 2px solid #dee2e6; }}
            td {{ padding: 10px; border-bottom: 1px solid #eee; }}
            .score {{ font-size: 48px; font-weight: bold; color: {'#2ecc71' if results['score'] > 80 else '#e74c3c'}; }}
        </style>
    </head>
    <body>
        <div class="card" style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h1>Data Quality Report</h1>
                <p>Generated: {results['timestamp']}</p>
            </div>
            <div style="text-align:right;">
                <div class="score">{results['score']}/100</div>
                <div>DQ Score</div>
            </div>
        </div>

        <div class="card">
            <h3>📊 Data Profile & Visualizations</h3>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4>Spend Distribution (Pareto)</h4>
                    <p>Top 20% Vendors: <strong>{stats['pareto_pct']:.1f}%</strong> of spend</p>
                    {_bar(stats['pareto_pct'], '#3498db')}
                </div>
                <div>
                    <h4>Delivery Performance</h4>
                    <p>Late Deliveries: <strong>{stats['late_pct']:.1f}%</strong></p>
                    {_bar(stats['late_pct'], '#e74c3c')}
                </div>
            </div>
        </div>

        <div class="card">
            <h3>Detailed Validation Results</h3>
            <table>
                <thead><tr><th>Category</th><th>Check</th><th>Status</th><th>Details</th><th>Severity</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </body>
    </html>
    """

    # Write files
    Path(output_path).mkdir(exist_ok=True, parents=True)
    with open(f"{output_path}/dq_dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)

    with open(f"{output_path}/dq_report.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n✨ Report generated: {output_path}/dq_dashboard.html")

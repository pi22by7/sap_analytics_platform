"""
Reporting and Visualization utilities.
"""

import json
from pathlib import Path


def generate_html_report(results, output_path):
    """Generates the HTML dashboard with embedded CSS visualizations."""

    def _bar(pct, color="blue"):
        return f'<div style="width:{pct}%; background:{color}; height:10px; border-radius:2px;"></div>'

    rows = ""
    for check in results["checks"]:
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

    record_counts_rows = ""
    if "record_counts" in stats:
        for table, count in stats["record_counts"].items():
            record_counts_rows += f"<tr><td>{table}</td><td>{count:,}</td></tr>"

    cardinality_html = ""
    if "cardinality" in stats:
        card = stats["cardinality"]
        cardinality_html = f"""
            <div style="margin-top: 15px;">
                <h4>Relationship Cardinality</h4>
                <ul>
                    <li>Avg Items per PO: <strong>{card.get('avg_items_per_po', 0):.2f}</strong></li>
                    <li>Avg Receipts per Item: <strong>{card.get('avg_receipts_per_item', 0):.2f}</strong></li>
                    <li>Avg Invoices per Item: <strong>{card.get('avg_invoices_per_item', 0):.2f}</strong></li>
                </ul>
            </div>
        """

    # price variance histogram
    price_variance_html = ""
    if "price_variance" in stats and stats["price_variance"]:
        import numpy as np

        variances = np.array(stats["price_variance"]) * 100

        bins = [0, 2, 5, 10, 20, 100]
        hist, _ = np.histogram(variances, bins=bins)
        max_count = max(hist) if max(hist) > 0 else 1

        hist_html = ""
        for i, count in enumerate(hist):
            pct = (count / max_count) * 100 if max_count > 0 else 0
            label = f"{bins[i]}-{bins[i+1]}%"
            hist_html += f"""
                <div style="margin-bottom: 5px;">
                    <div style="display: flex; align-items: center;">
                        <span style="width: 80px; font-size: 12px;">{label}</span>
                        <div style="flex: 1; background: #ecf0f1; border-radius: 3px; height: 20px;">
                            <div style="width: {pct}%; background: #e67e22; height: 100%; border-radius: 3px;"></div>
                        </div>
                        <span style="margin-left: 10px; font-size: 12px;">{count}</span>
                    </div>
                </div>
            """

        price_variance_html = f"""
            <div>
                <h4>Price Variance Distribution</h4>
                <p style="font-size: 12px; color: #7f8c8d;">Contract vs. PO Price Deviation</p>
                {hist_html}
            </div>
        """

    # completeness heatmap
    completeness_html = ""
    if "record_counts" in stats:
        # completeness based on checks
        tables = ["LFA1", "MARA", "EKKO", "EKPO", "EKBE", "VENDOR_CONTRACTS"]
        heatmap_rows = ""
        for table in tables:

            count = stats["record_counts"].get(table, 0)
            completeness = 100 if count > 0 else 0
            color = "#27ae60" if completeness == 100 else "#e74c3c"
            heatmap_rows += f"""
                <div style="display: flex; align-items: center; margin-bottom: 5px;">
                    <span style="width: 150px; font-size: 12px;">{table}</span>
                    <div style="flex: 1; background: #ecf0f1; border-radius: 3px; height: 18px;">
                        <div style="width: {completeness}%; background: {color}; height: 100%; border-radius: 3px;"></div>
                    </div>
                    <span style="margin-left: 10px; font-size: 12px;">{completeness}%</span>
                </div>
            """

        completeness_html = f"""
            <div>
                <h4>Data Completeness Heatmap</h4>
                <p style="font-size: 12px; color: #7f8c8d;">Table-level data availability</p>
                {heatmap_rows}
            </div>
        """

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
            <h3>📊 Data Profile</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4>Table Statistics</h4>
                    <table style="font-size: 13px;">
                        <thead><tr><th>Table</th><th>Records</th></tr></thead>
                        <tbody>{record_counts_rows}</tbody>
                    </table>
                    {cardinality_html}
                </div>
                <div>
                    {completeness_html}
                </div>
            </div>
        </div>

        <div class="card">
            <h3>📈 Visualizations</h3>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4>Spend Distribution (Pareto)</h4>
                    <p>Top 20% Vendors: <strong>{stats.get('pareto_pct', 0):.1f}%</strong> of spend</p>
                    {_bar(stats.get('pareto_pct', 0), '#3498db')}
                </div>
                <div>
                    <h4>Delivery Performance</h4>
                    <p>Late Deliveries: <strong>{stats.get('late_pct', 0):.1f}%</strong></p>
                    {_bar(stats.get('late_pct', 0), '#e74c3c')}
                </div>
            </div>
            <div style="margin-top: 20px;">
                {price_variance_html}
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

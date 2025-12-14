from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
import pandas as pd
from datetime import datetime


def generate_executive_report(data, output_path):
    """
    Generates an executive report using ReportLab with professional formatting.
    """
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title Section
    story.append(Paragraph("Procurement Analytics Executive Summary", styles["Title"]))
    story.append(
        Paragraph(
            f"Generated on: {datetime.now().strftime('%B %d, %Y')}", styles["Normal"]
        )
    )
    story.append(Spacer(1, 20))

    # --- Section 1: Key Performance Indicators ---
    story.append(Paragraph("1. Key Performance Indicators", styles["Heading2"]))

    # Calculate Metrics
    ekko = data["ekko"]
    ekpo = data["ekpo"]
    ekbe = data["ekbe"]

    total_spend = ekpo["NETWR"].sum()

    # OTD Calculation
    grs = ekbe[ekbe["BEWTP"] == "E"].merge(
        ekpo[["EBELN", "EBELP", "EINDT"]], on=["EBELN", "EBELP"]
    )
    on_time = (grs["BUDAT"] <= grs["EINDT"]).sum()
    otd_rate = (on_time / len(grs) * 100) if len(grs) > 0 else 0

    # Compliance Calculation
    contract_pos = len(ekko[ekko["BSART"] == "NB"])
    compliance = (contract_pos / len(ekko) * 100) if len(ekko) > 0 else 0

    # KPI Table
    kpi_data = [
        ["Metric", "Value", "Status"],
        ["Total Spend", f"${total_spend:,.2f}", "-"],
        ["On-Time Delivery", f"{otd_rate:.1f}%", "Target: 95%"],
        ["Contract Compliance", f"{compliance:.1f}%", "Target: 70%"],
        ["Active Vendors", f"{ekko['LIFNR'].nunique()}", "-"],
    ]

    t_kpi = Table(kpi_data, colWidths=[200, 100, 100])
    t_kpi.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.navy),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(t_kpi)
    story.append(Spacer(1, 20))

    # --- Section 2: Strategic Supply Base ---
    story.append(Paragraph("2. Top 5 Vendors by Spend", styles["Heading2"]))

    spend_by_vendor = (
        ekpo.merge(ekko[["EBELN", "LIFNR"]], on="EBELN")
        .groupby("LIFNR")["NETWR"]
        .sum()
        .nlargest(5)
        .reset_index()
    )

    # Merge names
    spend_by_vendor = spend_by_vendor.merge(
        data["lfa1"][["LIFNR", "NAME1", "LAND1"]], on="LIFNR"
    )

    vendor_data = [["Vendor Name", "Country", "Total Spend"]]
    for _, row in spend_by_vendor.iterrows():
        vendor_data.append([row["NAME1"], row["LAND1"], f"${row['NETWR']:,.2f}"])

    t_vendor = Table(vendor_data, colWidths=[200, 100, 100])
    t_vendor.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.navy),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(t_vendor)
    story.append(Spacer(1, 20))

    # --- Section 3: Strategic Recommendations ---
    story.append(Paragraph("3. Strategic Recommendations", styles["Heading2"]))

    recs = []
    if otd_rate < 95:
        recs.append(
            "<b>Logistics Optimization:</b> OTD is below the 95% target. Initiate root cause analysis with bottom-quartile performers."
        )
    if compliance < 70:
        recs.append(
            "<b>Spend Consolidation:</b> Contract compliance is below 70%. Enforce 'No PO, No Pay' policies to reduce maverick spend."
        )

    # Check for maverick spend magnitude
    maverick = ekko[ekko["BSART"] == "FO"]
    if not maverick.empty:
        recs.append(
            f"<b>Maverick Spend Control:</b> Identified {len(maverick)} off-contract orders. Transition top 20% of these commodities to framework agreements."
        )

    if not recs:
        recs.append(
            "Operations are performing within target parameters. Maintain current monitoring cadence."
        )

    for r in recs:
        story.append(Paragraph(f"• {r}", styles["Normal"]))
        story.append(Spacer(1, 6))

    # Build PDF
    doc.build(story)
    return output_path

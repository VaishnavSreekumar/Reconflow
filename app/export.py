"""
Export Module for ReconFlow.

Generates CSV downloads and professional multi-sheet OpenPyXL Excel Review Packs
for interview demonstrations and operational sign-offs.
"""

import io
from typing import Dict, Any, List
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def generate_reconciliation_csv(df_results: pd.DataFrame) -> str:
    """
    Exports full reconciliation dataset to CSV format string.
    """
    if df_results is None or df_results.empty:
        return ""
    
    export_df = df_results.drop(columns=["record_a", "record_b"], errors="ignore")
    return export_df.to_csv(index=False)


def generate_exceptions_csv(df_results: pd.DataFrame) -> str:
    """
    Exports unresolved exception records to CSV format string.
    """
    if df_results is None or df_results.empty:
        return ""

    exceptions_df = df_results[df_results["status"] != "MATCHED"].copy()
    export_df = exceptions_df.drop(columns=["record_a", "record_b"], errors="ignore")
    return export_df.to_csv(index=False)


def generate_excel_review_pack(
    recon_data: Dict[str, Any],
    review_notes: List[Dict[str, Any]]
) -> bytes:
    """
    Generates a professional 5-sheet OpenPyXL Excel Review Pack Workbook.
    
    Sheets:
      1. Executive Summary
      2. Reconciliation Results
      3. Exceptions
      4. Data Quality
      5. Review Notes
    """
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default sheet

    # Styling definitions
    font_title = Font(name="Calibri", size=16, bold=True, color="0F172A")
    font_subtitle = Font(name="Calibri", size=11, italic=True, color="475569")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=11, bold=True, color="0F172A")
    font_regular = Font(name="Calibri", size=11, color="1E293B")

    fill_header = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    fill_sub_header = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
    fill_accent = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    thin_border_side = Side(style="thin", color="CBD5E1")
    border_cell = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    summary = recon_data.get("summary", {})
    df_results = recon_data.get("results", pd.DataFrame())
    quality_a = recon_data.get("quality_a", {})
    quality_b = recon_data.get("quality_b", {})

    # -------------------------------------------------------------
    # SHEET 1: EXECUTIVE SUMMARY
    # -------------------------------------------------------------
    ws1 = wb.create_sheet(title="Executive Summary")
    ws1.views.sheetView[0].showGridLines = True

    ws1["A1"] = "ReconFlow — Transaction Reconciliation Executive Summary"
    ws1["A1"].font = font_title
    ws1["A2"] = f"Health Status: {summary.get('reconciliation_health', 'N/A')} | Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ws1["A2"].font = font_subtitle

    # KPI Table
    ws1["A4"] = "Key Performance Metric"
    ws1["B4"] = "Value"
    ws1["A4"].font = font_header
    ws1["B4"].font = font_header
    ws1["A4"].fill = fill_header
    ws1["B4"].fill = fill_header

    kpis = [
        ("Source A Total Amount", summary.get("source_a_total", 0.0)),
        ("Source B Total Amount", summary.get("source_b_total", 0.0)),
        ("Source A Record Count", summary.get("source_a_count", 0)),
        ("Source B Record Count", summary.get("source_b_count", 0)),
        ("Total Reconciled Pairs", summary.get("total_records", 0)),
        ("Matched Record Count", summary.get("matched_count", 0)),
        ("Reconciliation Rate (%)", f"{summary.get('reconciliation_rate', 0.0)}%"),
        ("Gross Variance (Abs)", summary.get("gross_variance", 0.0)),
        ("Unresolved High Severity Exceptions", summary.get("unresolved_high_severity", 0)),
        ("Reconciliation Health", summary.get("reconciliation_health", "UNKNOWN")),
    ]

    for idx, (k, v) in enumerate(kpis, start=5):
        ws1[f"A{idx}"] = k
        ws1[f"B{idx}"] = v
        ws1[f"A{idx}"].font = font_bold
        ws1[f"B{idx}"].font = font_regular
        ws1[f"A{idx}"].border = border_cell
        ws1[f"B{idx}"].border = border_cell
        if isinstance(v, float):
            ws1[f"B{idx}"].number_format = "#,##0.00"

    # Status Breakdown Table
    row_start = 17
    ws1[f"A{row_start}"] = "Reconciliation Exception Taxonomy"
    ws1[f"B{row_start}"] = "Record Count"
    ws1[f"A{row_start}"].font = font_header
    ws1[f"B{row_start}"].font = font_header
    ws1[f"A{row_start}"].fill = fill_sub_header
    ws1[f"B{row_start}"].fill = fill_sub_header

    status_counts = summary.get("status_counts", {})
    curr_row = row_start + 1
    for st_name, count in status_counts.items():
        ws1[f"A{curr_row}"] = st_name
        ws1[f"B{curr_row}"] = count
        ws1[f"A{curr_row}"].font = font_regular
        ws1[f"B{curr_row}"].font = font_regular
        ws1[f"A{curr_row}"].border = border_cell
        ws1[f"B{curr_row}"].border = border_cell
        curr_row += 1

    # -------------------------------------------------------------
    # SHEET 2: RECONCILIATION RESULTS
    # -------------------------------------------------------------
    ws2 = wb.create_sheet(title="Reconciliation Results")
    ws2.views.sheetView[0].showGridLines = True

    cols_to_export = [
        "severity", "status", "source_a_id", "source_b_id", "reference",
        "account", "amount_a", "amount_b", "variance", "confidence",
        "match_rule", "reason"
    ]

    if not df_results.empty:
        export_results_df = df_results[cols_to_export].copy()
    else:
        export_results_df = pd.DataFrame(columns=cols_to_export)

    # Write Header
    for col_num, col_name in enumerate(cols_to_export, 1):
        cell = ws2.cell(row=1, column=col_num)
        cell.value = col_name.replace("_", " ").title()
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row_num, row_data in enumerate(export_results_df.values, 2):
        for col_num, val in enumerate(row_data, 1):
            cell = ws2.cell(row=row_num, column=col_num)
            cell.value = "" if pd.isna(val) else val
            cell.font = font_regular
            cell.border = border_cell
            if col_num in [7, 8, 9] and isinstance(val, (int, float)):
                cell.number_format = "#,##0.00"
            elif col_num == 10 and isinstance(val, (int, float)):
                cell.number_format = "0.0%"

    # -------------------------------------------------------------
    # SHEET 3: EXCEPTIONS
    # -------------------------------------------------------------
    ws3 = wb.create_sheet(title="Exceptions")
    ws3.views.sheetView[0].showGridLines = True

    if not df_results.empty:
        exceptions_df = df_results[df_results["status"] != "MATCHED"][cols_to_export].copy()
    else:
        exceptions_df = pd.DataFrame(columns=cols_to_export)

    for col_num, col_name in enumerate(cols_to_export, 1):
        cell = ws3.cell(row=1, column=col_num)
        cell.value = col_name.replace("_", " ").title()
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row_num, row_data in enumerate(exceptions_df.values, 2):
        for col_num, val in enumerate(row_data, 1):
            cell = ws3.cell(row=row_num, column=col_num)
            cell.value = "" if pd.isna(val) else val
            cell.font = font_regular
            cell.border = border_cell
            if col_num in [7, 8, 9] and isinstance(val, (int, float)):
                cell.number_format = "#,##0.00"
            elif col_num == 10 and isinstance(val, (int, float)):
                cell.number_format = "0.0%"

    # -------------------------------------------------------------
    # SHEET 4: DATA QUALITY
    # -------------------------------------------------------------
    ws4 = wb.create_sheet(title="Data Quality")
    ws4.views.sheetView[0].showGridLines = True

    dq_headers = ["Quality Metric", "Source A (Core System)", "Source B (Bank Gateway)"]
    for c_idx, h in enumerate(dq_headers, 1):
        cell = ws4.cell(row=1, column=c_idx)
        cell.value = h
        cell.font = font_header
        cell.fill = fill_header

    metrics = [
        ("Total Rows", quality_a.get("total_rows", 0), quality_b.get("total_rows", 0)),
        ("Duplicate Transaction IDs", quality_a.get("duplicate_ids", 0), quality_b.get("duplicate_ids", 0)),
        ("Missing Transaction IDs", quality_a.get("missing_transaction_ids", 0), quality_b.get("missing_transaction_ids", 0)),
        ("Invalid / Unparseable Dates", quality_a.get("invalid_dates", 0), quality_b.get("invalid_dates", 0)),
        ("Invalid / Null Amounts", quality_a.get("invalid_amounts", 0), quality_b.get("invalid_amounts", 0)),
        ("Negative Amounts", quality_a.get("negative_amounts", 0), quality_b.get("negative_amounts", 0)),
        ("Missing References", quality_a.get("missing_references", 0), quality_b.get("missing_references", 0)),
        ("Missing Accounts", quality_a.get("missing_accounts", 0), quality_b.get("missing_accounts", 0)),
        ("Missing Currencies", quality_a.get("missing_currencies", 0), quality_b.get("missing_currencies", 0)),
        ("Total Data Quality Violations", quality_a.get("total_quality_issues", 0), quality_b.get("total_quality_issues", 0)),
        ("Data Quality Score (%)", f"{quality_a.get('health_score', 100.0)}%", f"{quality_b.get('health_score', 100.0)}%"),
    ]

    for r_idx, (m_label, v_a, v_b) in enumerate(metrics, start=2):
        cell_m = ws4.cell(row=r_idx, column=1, value=m_label)
        cell_a = ws4.cell(row=r_idx, column=2, value=v_a)
        cell_b = ws4.cell(row=r_idx, column=3, value=v_b)
        cell_m.font = font_bold
        cell_a.font = font_regular
        cell_b.font = font_regular
        cell_m.border = border_cell
        cell_a.border = border_cell
        cell_b.border = border_cell

    # -------------------------------------------------------------
    # SHEET 5: REVIEW NOTES
    # -------------------------------------------------------------
    ws5 = wb.create_sheet(title="Review Notes")
    ws5.views.sheetView[0].showGridLines = True

    notes_headers = ["Exception Key", "Status", "Reviewer", "Updated At", "Reviewer Notes / Rationale"]
    for c_idx, h in enumerate(notes_headers, 1):
        cell = ws5.cell(row=1, column=c_idx)
        cell.value = h
        cell.font = font_header
        cell.fill = fill_header

    if review_notes:
        for r_idx, note_item in enumerate(review_notes, start=2):
            ws5.cell(row=r_idx, column=1, value=note_item.get("key", "")).font = font_regular
            ws5.cell(row=r_idx, column=2, value=note_item.get("status", "")).font = font_bold
            ws5.cell(row=r_idx, column=3, value=note_item.get("reviewer", "")).font = font_regular
            ws5.cell(row=r_idx, column=4, value=note_item.get("updated_at", "")).font = font_regular
            ws5.cell(row=r_idx, column=5, value=note_item.get("note", "")).font = font_regular
            for c_i in range(1, 6):
                ws5.cell(row=r_idx, column=c_i).border = border_cell
    else:
        ws5.cell(row=2, column=1, value="No human review notes recorded in this session.").font = font_subtitle

    # Auto-adjust column widths across all sheets
    for ws in [ws1, ws2, ws3, ws4, ws5]:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()

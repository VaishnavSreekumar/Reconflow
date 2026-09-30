"""
Unit tests for ReconFlow Export Module (CSV & Excel generation).
"""

import pandas as pd
import openpyxl
import pytest
from app.demo_data import generate_synthetic_demo_data
from app.engine import reconcile_datasets
from app.export import (
    generate_reconciliation_csv,
    generate_exceptions_csv,
    generate_excel_review_pack
)


def test_csv_exports():
    df_a, df_b = generate_synthetic_demo_data(num_records=50, seed=42)
    recon_data = reconcile_datasets(df_a, df_b)
    df_results = recon_data["results"]

    csv_full = generate_reconciliation_csv(df_results)
    csv_exc = generate_exceptions_csv(df_results)

    assert len(csv_full) > 0
    assert "transaction_id" in csv_full.lower() or "source_a_id" in csv_full.lower()
    assert len(csv_exc) > 0


def test_excel_review_pack_generation():
    df_a, df_b = generate_synthetic_demo_data(num_records=50, seed=42)
    recon_data = reconcile_datasets(df_a, df_b)

    review_notes = [
        {
            "key": "A:TXN-01|B:TXN-01|R:REF-01",
            "status": "REVIEWED",
            "reviewer": "Test Ops Analyst",
            "updated_at": "2026-09-30 10:00:00",
            "note": "Verified settlement fee discrepancy with bank."
        }
    ]

    excel_bytes = generate_excel_review_pack(recon_data, review_notes)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0

    # Read back generated excel file using openpyxl to verify sheet integrity
    import io
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    sheet_names = wb.sheetnames

    assert "Executive Summary" in sheet_names
    assert "Reconciliation Results" in sheet_names
    assert "Exceptions" in sheet_names
    assert "Data Quality" in sheet_names
    assert "Review Notes" in sheet_names

    ws_sum = wb["Executive Summary"]
    assert ws_sum["A1"].value.startswith("ReconFlow")

    ws_notes = wb["Review Notes"]
    assert ws_notes["C2"].value == "Test Ops Analyst"

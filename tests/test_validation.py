"""
Unit tests for ReconFlow Validation & Data Quality Module.
"""

import pandas as pd
import numpy as np
import pytest
from app.validation import validate_schema, normalize_dataset, inspect_data_quality


def test_validate_schema_valid():
    df = pd.DataFrame(columns=["transaction_id", "reference", "account", "date", "amount", "currency"])
    is_valid, missing = validate_schema(df)
    assert is_valid is True
    assert len(missing) == 0


def test_validate_schema_missing_columns():
    df = pd.DataFrame(columns=["transaction_id", "amount"])
    is_valid, missing = validate_schema(df)
    assert is_valid is False
    assert "reference" in missing
    assert "account" in missing


def test_normalize_dataset():
    df = pd.DataFrame({
        "Transaction_ID ": ["TXN-101 ", "TXN-102"],
        "AMOUNT": ["1500.50", "invalid_amt"],
        "Date": ["2026-09-01", "2026-99-99"]
    })
    norm = normalize_dataset(df)
    assert "transaction_id" in norm.columns
    assert norm.iloc[0]["transaction_id"] == "TXN-101"
    assert norm.iloc[0]["amount"] == 1500.50
    assert pd.isna(norm.iloc[1]["amount"])
    assert norm.iloc[0]["date_str"] == "2026-09-01"
    assert pd.isna(norm.iloc[1]["date_parsed"])


def test_inspect_data_quality():
    df = pd.DataFrame({
        "transaction_id": ["TXN-01", "TXN-01", None],  # 1 duplicate, 1 missing ID
        "reference": ["REF-01", None, "REF-03"],
        "account": ["ACC-1", "ACC-2", "ACC-3"],
        "date": ["2026-09-01", "invalid_date", "2026-09-03"],  # 1 invalid date
        "amount": [100.0, -50.0, None],  # 1 negative, 1 invalid amount
        "currency": ["INR", "INR", "INR"]
    })
    quality = inspect_data_quality(df, "Source A")
    assert quality["total_rows"] == 3
    assert quality["duplicate_ids"] == 1
    assert quality["missing_transaction_ids"] == 1
    assert quality["invalid_dates"] == 1
    assert quality["invalid_amounts"] == 1
    assert quality["negative_amounts"] == 1
    assert quality["total_quality_issues"] > 0
    assert quality["health_score"] < 100.0

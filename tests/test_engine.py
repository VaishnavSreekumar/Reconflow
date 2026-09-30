"""
Unit tests for ReconFlow Matching Engine.
"""

import pandas as pd
import pytest
from app.engine import reconcile_datasets, ReconciliationStatus, ExceptionSeverity


def test_exact_transaction_id_match():
    df_a = pd.DataFrame([{
        "transaction_id": "TXN-101",
        "reference": "REF-101",
        "account": "ACC-01",
        "date": "2026-09-01",
        "amount": 5000.0,
        "currency": "INR"
    }])
    df_b = pd.DataFrame([{
        "transaction_id": "TXN-101",
        "reference": "REF-101",
        "account": "ACC-01",
        "date": "2026-09-01",
        "amount": 5000.0,
        "currency": "INR"
    }])

    res = reconcile_datasets(df_a, df_b)
    df_res = res["results"]
    summary = res["summary"]

    assert len(df_res) == 1
    assert df_res.iloc[0]["status"] == ReconciliationStatus.MATCHED
    assert df_res.iloc[0]["confidence"] == 1.00
    assert summary["matched_count"] == 1
    assert summary["reconciliation_rate"] == 100.0


def test_reference_and_amount_match():
    df_a = pd.DataFrame([{
        "transaction_id": "TXN-A-01",
        "reference": "REF-999",
        "account": "ACC-01",
        "date": "2026-09-05",
        "amount": 12500.0,
        "currency": "INR"
    }])
    df_b = pd.DataFrame([{
        "transaction_id": "TXN-B-99",
        "reference": "REF-999",
        "account": "ACC-01",
        "date": "2026-09-05",
        "amount": 12500.0,
        "currency": "INR"
    }])

    res = reconcile_datasets(df_a, df_b)
    df_res = res["results"]
    assert len(df_res) == 1
    assert df_res.iloc[0]["status"] == ReconciliationStatus.MATCHED
    assert "RULE 2" in df_res.iloc[0]["match_rule"]


def test_account_date_amount_match():
    df_a = pd.DataFrame([{
        "transaction_id": "TXN-A-02",
        "reference": "REF-DIFF-A",
        "account": "ACC-LN-100",
        "date": "2026-09-10",
        "amount": 7500.0,
        "currency": "INR"
    }])
    df_b = pd.DataFrame([{
        "transaction_id": "TXN-B-02",
        "reference": "REF-DIFF-B",
        "account": "ACC-LN-100",
        "date": "2026-09-10",
        "amount": 7500.0,
        "currency": "INR"
    }])

    res = reconcile_datasets(df_a, df_b)
    df_res = res["results"]
    assert len(df_res) == 1
    assert df_res.iloc[0]["status"] == ReconciliationStatus.MATCHED
    assert "RULE 3" in df_res.iloc[0]["match_rule"]


def test_amount_mismatch():
    df_a = pd.DataFrame([{
        "transaction_id": "TXN-105",
        "reference": "REF-105",
        "account": "ACC-01",
        "date": "2026-09-01",
        "amount": 10500.0,
        "currency": "INR"
    }])
    df_b = pd.DataFrame([{
        "transaction_id": "TXN-105",
        "reference": "REF-105",
        "account": "ACC-01",
        "date": "2026-09-01",
        "amount": 10000.0,
        "currency": "INR"
    }])

    res = reconcile_datasets(df_a, df_b)
    df_res = res["results"]
    assert len(df_res) == 1
    assert df_res.iloc[0]["status"] == ReconciliationStatus.AMOUNT_MISMATCH
    assert df_res.iloc[0]["variance"] == 500.0
    assert df_res.iloc[0]["severity"] in [ExceptionSeverity.MEDIUM, ExceptionSeverity.HIGH]


def test_currency_mismatch():
    df_a = pd.DataFrame([{
        "transaction_id": "TXN-106",
        "reference": "REF-106",
        "account": "ACC-01",
        "date": "2026-09-01",
        "amount": 5000.0,
        "currency": "INR"
    }])
    df_b = pd.DataFrame([{
        "transaction_id": "TXN-106",
        "reference": "REF-106",
        "account": "ACC-01",
        "date": "2026-09-01",
        "amount": 5000.0,
        "currency": "USD"
    }])

    res = reconcile_datasets(df_a, df_b)
    df_res = res["results"]
    assert len(df_res) == 1
    assert df_res.iloc[0]["status"] == ReconciliationStatus.CURRENCY_MISMATCH


def test_missing_records():
    df_a = pd.DataFrame([{
        "transaction_id": "TXN-ONLY-A",
        "reference": "REF-A",
        "account": "ACC-01",
        "date": "2026-09-01",
        "amount": 3000.0,
        "currency": "INR"
    }])
    df_b = pd.DataFrame([{
        "transaction_id": "TXN-ONLY-B",
        "reference": "REF-B",
        "account": "ACC-02",
        "date": "2026-09-01",
        "amount": 4000.0,
        "currency": "INR"
    }])

    res = reconcile_datasets(df_a, df_b)
    df_res = res["results"]
    statuses = set(df_res["status"].tolist())
    assert ReconciliationStatus.MISSING_IN_SOURCE_B in statuses
    assert ReconciliationStatus.MISSING_IN_SOURCE_A in statuses


def test_duplicate_control():
    df_a = pd.DataFrame([
        {
            "transaction_id": "TXN-DUP-01",
            "reference": "REF-DUP",
            "account": "ACC-01",
            "date": "2026-09-01",
            "amount": 2000.0,
            "currency": "INR"
        },
        {
            "transaction_id": "TXN-DUP-01",
            "reference": "REF-DUP",
            "account": "ACC-01",
            "date": "2026-09-01",
            "amount": 2000.0,
            "currency": "INR"
        }
    ])
    df_b = pd.DataFrame([])

    res = reconcile_datasets(df_a, df_b)
    df_res = res["results"]
    assert any(df_res["status"] == ReconciliationStatus.DUPLICATE_CONTROL)


def test_deterministic_reconciliation_repeatability():
    from app.demo_data import generate_synthetic_demo_data
    df_a, df_b = generate_synthetic_demo_data(num_records=100, seed=123)

    res1 = reconcile_datasets(df_a, df_b)
    res2 = reconcile_datasets(df_a, df_b)

    assert res1["summary"]["matched_count"] == res2["summary"]["matched_count"]
    assert res1["summary"]["gross_variance"] == res2["summary"]["gross_variance"]
    assert len(res1["results"]) == len(res2["results"])

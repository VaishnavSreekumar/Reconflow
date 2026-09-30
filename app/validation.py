"""
Validation and Data Quality Module for ReconFlow.

Provides schema validation, data type normalization, and comprehensive quality metrics
for transaction records prior to matching.
"""

from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

REQUIRED_COLUMNS = [
    "transaction_id",
    "reference",
    "account",
    "date",
    "amount",
    "currency"
]

def validate_schema(df: pd.DataFrame, source_name: str = "Source") -> Tuple[bool, List[str]]:
    """
    Checks if required columns exist in input DataFrame.
    Returns (is_valid, list_of_missing_columns).
    """
    if df is None or len(df.columns) == 0:
        return False, ["DataFrame is empty or None"]
    
    # Standardize column names (lowercase, strip whitespace)
    cols = [str(c).strip().lower() for c in df.columns]
    missing = [col for col in REQUIRED_COLUMNS if col not in cols]
    return (len(missing) == 0), missing


def normalize_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes column names, converts dates, and cleans string/numeric fields.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    df_clean = df.copy()
    # Normalize headers
    df_clean.columns = [str(c).strip().lower() for c in df_clean.columns]

    # Fill missing expected columns with NaN if missing to prevent KeyError
    for col in REQUIRED_COLUMNS:
        if col not in df_clean.columns:
            df_clean[col] = np.nan

    # Clean string fields
    for col in ["transaction_id", "reference", "account", "currency"]:
        df_clean[col] = df_clean[col].astype(str).str.strip()
        df_clean.loc[df_clean[col].isin(["nan", "None", "NaN", ""]), col] = np.nan

    # Clean amounts
    df_clean["amount"] = pd.to_numeric(df_clean["amount"], errors="coerce")

    # Clean dates
    df_clean["date_parsed"] = pd.to_datetime(df_clean["date"], errors="coerce")
    df_clean["date_str"] = df_clean["date_parsed"].dt.strftime("%Y-%m-%d")

    return df_clean


def inspect_data_quality(df: pd.DataFrame, source_name: str = "Source") -> Dict[str, Any]:
    """
    Computes detailed Data Quality KPIs for a given dataset.
    """
    if df is None or df.empty:
        return {
            "source": source_name,
            "total_rows": 0,
            "duplicate_ids": 0,
            "missing_transaction_ids": 0,
            "invalid_dates": 0,
            "invalid_amounts": 0,
            "negative_amounts": 0,
            "missing_references": 0,
            "missing_accounts": 0,
            "missing_currencies": 0,
            "total_quality_issues": 0,
            "health_score": 100.0
        }

    norm_df = normalize_dataset(df)
    total_rows = len(norm_df)

    # 1. Missing transaction IDs
    missing_tx_ids = int(norm_df["transaction_id"].isna().sum())

    # 2. Duplicate transaction IDs (excluding NaNs)
    valid_tx_ids = norm_df["transaction_id"].dropna()
    duplicate_ids = int(valid_tx_ids.duplicated().sum())

    # 3. Invalid dates
    invalid_dates = int(norm_df["date_parsed"].isna().sum())

    # 4. Invalid amounts (NaN after numeric coercing)
    invalid_amounts = int(norm_df["amount"].isna().sum())

    # 5. Negative amounts
    valid_amounts = norm_df["amount"].dropna()
    negative_amounts = int((valid_amounts < 0).sum())

    # 6. Missing references, accounts, currencies
    missing_refs = int(norm_df["reference"].isna().sum())
    missing_accounts = int(norm_df["account"].isna().sum())
    missing_currencies = int(norm_df["currency"].isna().sum())

    total_issues = (
        missing_tx_ids + duplicate_ids + invalid_dates +
        invalid_amounts + negative_amounts + missing_refs +
        missing_accounts + missing_currencies
    )

    # Quality Health score % (proportional to issue ratio)
    quality_score = max(0.0, round(100.0 * (1.0 - (total_issues / max(1, total_rows * 3))), 1))

    return {
        "source": source_name,
        "total_rows": total_rows,
        "duplicate_ids": duplicate_ids,
        "missing_transaction_ids": missing_tx_ids,
        "invalid_dates": invalid_dates,
        "invalid_amounts": invalid_amounts,
        "negative_amounts": negative_amounts,
        "missing_references": missing_refs,
        "missing_accounts": missing_accounts,
        "missing_currencies": missing_currencies,
        "total_quality_issues": total_issues,
        "health_score": quality_score
    }

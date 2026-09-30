"""
Synthetic Demo Data Generator for ReconFlow.

Generates realistic, completely fictional financial transaction datasets
tailored for Housing Finance & Banking operations demo scenarios.
Includes explicit edge-case distributions (exact match, amount mismatch,
missing records, duplicates, malformed data).
"""

import random
from datetime import datetime, timedelta
from typing import Tuple
import pandas as pd
import numpy as np


def generate_synthetic_demo_data(num_records: int = 150, seed: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generates two DataFrames (Source A: Core Loan System, Source B: Bank Settlement Gateway)
    with controlled deterministic edge cases.
    """
    random.seed(seed)
    np.random.seed(seed)

    base_date = datetime(2026, 9, 1)
    accounts = [
        "ACC-LN-10042", "ACC-LN-88301", "ACC-LN-54219",
        "ACC-LN-99402", "ACC-ESCROW-001", "ACC-DISB-99"
    ]
    currencies = ["INR", "INR", "INR", "INR", "INR", "USD"]

    rows_a = []
    rows_b = []

    # Distribution counts
    count_exact = int(num_records * 0.70)
    count_ref_match = int(num_records * 0.10)
    count_amt_mismatch = int(num_records * 0.05)
    count_date_mismatch = int(num_records * 0.03)
    count_missing_b = int(num_records * 0.04)
    count_missing_a = int(num_records * 0.04)
    count_duplicate = int(num_records * 0.02)
    count_invalid = max(2, num_records - (
        count_exact + count_ref_match + count_amt_mismatch +
        count_date_mismatch + count_missing_b + count_missing_a + count_duplicate
    ))

    tx_counter = 1000

    # 1. EXACT MATCHES
    for _ in range(count_exact):
        tx_counter += 1
        tx_id = f"TXN-2026-{tx_counter}"
        ref = f"REF-EMI-{tx_counter}"
        acc = random.choice(accounts)
        dt = (base_date + timedelta(days=random.randint(0, 25))).strftime("%Y-%m-%d")
        amt = round(random.uniform(5000.0, 150000.0), 2)
        curr = "USD" if acc == "ACC-DISB-99" else "INR"

        rec = {
            "transaction_id": tx_id,
            "reference": ref,
            "account": acc,
            "date": dt,
            "amount": amt,
            "currency": curr
        }
        rows_a.append(rec)
        rows_b.append(rec.copy())

    # 2. REFERENCE MATCH (Different Tx ID, same Ref & Amount)
    for _ in range(count_ref_match):
        tx_counter += 1
        tx_id_a = f"TXN-2026-{tx_counter}A"
        tx_id_b = f"TXN-2026-{tx_counter}B"
        ref = f"REF-PAY-{tx_counter}"
        acc = random.choice(accounts)
        dt = (base_date + timedelta(days=random.randint(0, 25))).strftime("%Y-%m-%d")
        amt = round(random.uniform(10000.0, 80000.0), 2)
        curr = "INR"

        rows_a.append({
            "transaction_id": tx_id_a,
            "reference": ref,
            "account": acc,
            "date": dt,
            "amount": amt,
            "currency": curr
        })
        rows_b.append({
            "transaction_id": tx_id_b,
            "reference": ref,
            "account": acc,
            "date": dt,
            "amount": amt,
            "currency": curr
        })

    # 3. AMOUNT MISMATCH (Settlement fee / partial payment variance)
    for _ in range(count_amt_mismatch):
        tx_counter += 1
        tx_id = f"TXN-2026-{tx_counter}"
        ref = f"REF-DIFF-{tx_counter}"
        acc = random.choice(accounts)
        dt = (base_date + timedelta(days=random.randint(0, 25))).strftime("%Y-%m-%d")
        amt_a = round(random.uniform(20000.0, 100000.0), 2)
        variance = random.choice([250.0, 500.0, 1200.50, 75.0])
        amt_b = round(amt_a - variance, 2)
        curr = "INR"

        rows_a.append({
            "transaction_id": tx_id,
            "reference": ref,
            "account": acc,
            "date": dt,
            "amount": amt_a,
            "currency": curr
        })
        rows_b.append({
            "transaction_id": tx_id,
            "reference": ref,
            "account": acc,
            "date": dt,
            "amount": amt_b,
            "currency": curr
        })

    # 4. DATE MISMATCH (T+1 Settlement delay)
    for _ in range(count_date_mismatch):
        tx_counter += 1
        tx_id = f"TXN-2026-{tx_counter}"
        ref = f"REF-DATE-{tx_counter}"
        acc = random.choice(accounts)
        dt_a = (base_date + timedelta(days=random.randint(1, 20))).strftime("%Y-%m-%d")
        dt_b = (base_date + timedelta(days=random.randint(21, 28))).strftime("%Y-%m-%d")
        amt = round(random.uniform(15000.0, 45000.0), 2)
        curr = "INR"

        rows_a.append({
            "transaction_id": tx_id,
            "reference": ref,
            "account": acc,
            "date": dt_a,
            "amount": amt,
            "currency": curr
        })
        rows_b.append({
            "transaction_id": tx_id,
            "reference": ref,
            "account": acc,
            "date": dt_b,
            "amount": amt,
            "currency": curr
        })

    # 5. MISSING IN SOURCE B (Uncleared cheque / pending gateway deposit)
    for _ in range(count_missing_b):
        tx_counter += 1
        tx_id = f"TXN-2026-UNCL-{tx_counter}"
        ref = f"REF-UNCL-{tx_counter}"
        acc = random.choice(accounts)
        dt = (base_date + timedelta(days=random.randint(0, 25))).strftime("%Y-%m-%d")
        amt = round(random.uniform(5000.0, 60000.0), 2)

        rows_a.append({
            "transaction_id": tx_id,
            "reference": ref,
            "account": acc,
            "date": dt,
            "amount": amt,
            "currency": "INR"
        })

    # 6. MISSING IN SOURCE A (Direct bank credit without core system record)
    for _ in range(count_missing_a):
        tx_counter += 1
        tx_id = f"TXN-2026-BANK-{tx_counter}"
        ref = f"REF-BANK-{tx_counter}"
        acc = random.choice(accounts)
        dt = (base_date + timedelta(days=random.randint(0, 25))).strftime("%Y-%m-%d")
        amt = round(random.uniform(10000.0, 75000.0), 2)

        rows_b.append({
            "transaction_id": tx_id,
            "reference": ref,
            "account": acc,
            "date": dt,
            "amount": amt,
            "currency": "INR"
        })

    # 7. DUPLICATE CONTROL (System retry / duplicate batch upload)
    for _ in range(count_duplicate):
        tx_counter += 1
        dup_tx_id = f"TXN-2026-DUP-{tx_counter}"
        ref = f"REF-DUP-{tx_counter}"
        acc = random.choice(accounts)
        dt = (base_date + timedelta(days=10)).strftime("%Y-%m-%d")
        amt = 25000.00

        dup_rec = {
            "transaction_id": dup_tx_id,
            "reference": ref,
            "account": acc,
            "date": dt,
            "amount": amt,
            "currency": "INR"
        }
        # Add twice to Source A to trigger Duplicate Control exception
        rows_a.append(dup_rec)
        rows_a.append(dup_rec.copy())
        rows_b.append(dup_rec.copy())

    # 8. INVALID DATA (Malformed date, null transaction ID, negative amount)
    if count_invalid >= 1:
        rows_a.append({
            "transaction_id": None,
            "reference": "REF-BAD-01",
            "account": "ACC-LN-10042",
            "date": "2026-09-15",
            "amount": 12000.0,
            "currency": "INR"
        })
    if count_invalid >= 2:
        rows_b.append({
            "transaction_id": "TXN-BAD-DATE",
            "reference": "REF-BAD-02",
            "account": "ACC-LN-88301",
            "date": "INVALID_DATE_STRING",
            "amount": -4500.0,
            "currency": "INR"
        })

    df_a = pd.DataFrame(rows_a)
    df_b = pd.DataFrame(rows_b)

    # Shuffle datasets to simulate real operational batch order
    df_a = df_a.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    df_b = df_b.sample(frac=1.0, random_state=seed + 1).reset_index(drop=True)

    return df_a, df_b

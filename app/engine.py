"""
Deterministic Reconciliation & Matching Engine for ReconFlow.

Implements index-based multi-tier matching algorithms (O(N) time complexity)
and explicit decision traceability.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from app.validation import normalize_dataset, inspect_data_quality


class ReconciliationStatus:
    MATCHED = "MATCHED"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    DATE_MISMATCH = "DATE_MISMATCH"
    MISSING_IN_SOURCE_A = "MISSING_IN_SOURCE_A"
    MISSING_IN_SOURCE_B = "MISSING_IN_SOURCE_B"
    DUPLICATE_CONTROL = "DUPLICATE_CONTROL"
    INVALID_DATA = "INVALID_DATA"


class ExceptionSeverity:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


def determine_severity(status: str, variance: float) -> str:
    """
    Deterministically assigns severity based on status and monetary variance.
    """
    if status == ReconciliationStatus.MATCHED:
        return ExceptionSeverity.NONE
    
    if status in [
        ReconciliationStatus.DUPLICATE_CONTROL,
        ReconciliationStatus.INVALID_DATA,
        ReconciliationStatus.MISSING_IN_SOURCE_A,
        ReconciliationStatus.MISSING_IN_SOURCE_B,
        ReconciliationStatus.CURRENCY_MISMATCH,
    ]:
        return ExceptionSeverity.HIGH

    if status == ReconciliationStatus.AMOUNT_MISMATCH:
        abs_var = abs(variance)
        if abs_var >= 1000.0:
            return ExceptionSeverity.HIGH
        elif abs_var >= 100.0:
            return ExceptionSeverity.MEDIUM
        else:
            return ExceptionSeverity.LOW

    if status == ReconciliationStatus.DATE_MISMATCH:
        return ExceptionSeverity.LOW

    return ExceptionSeverity.MEDIUM


def reconcile_datasets(df_a: pd.DataFrame, df_b: pd.DataFrame) -> Dict[str, Any]:
    """
    Executes multi-pass deterministic reconciliation between Source A and Source B.
    
    Returns:
      {
        "summary": dict of KPIs & health metrics,
        "results": pd.DataFrame of paired reconciliation records,
        "quality_a": dict,
        "quality_b": dict
      }
    """
    # 1. Data Quality Assessment
    quality_a = inspect_data_quality(df_a, "Source A")
    quality_b = inspect_data_quality(df_b, "Source B")

    norm_a = normalize_dataset(df_a)
    norm_b = normalize_dataset(df_b)

    records_a = norm_a.to_dict(orient="records")
    records_b = norm_b.to_dict(orient="records")

    matched_pairs = []

    # Track processed indices to ensure O(N) single-assignment
    processed_a = set()
    processed_b = set()

    # Detect duplicate IDs upfront for DUPLICATE_CONTROL
    id_counts_a = {}
    id_counts_b = {}
    for r in records_a:
        txid = r.get("transaction_id")
        if pd.notna(txid):
            id_counts_a[txid] = id_counts_a.get(txid, 0) + 1
    for r in records_b:
        txid = r.get("transaction_id")
        if pd.notna(txid):
            id_counts_b[txid] = id_counts_b.get(txid, 0) + 1

    # Index valid non-duplicate records for fast lookups
    dict_a_by_id = {}
    dict_a_by_ref = {}
    dict_a_by_acc_date_amt = {}

    for idx, r in enumerate(records_a):
        # Flag structurally invalid rows
        if pd.isna(r.get("transaction_id")) or pd.isna(r.get("amount")):
            matched_pairs.append({
                "severity": ExceptionSeverity.HIGH,
                "status": ReconciliationStatus.INVALID_DATA,
                "source_a_id": r.get("transaction_id"),
                "source_b_id": None,
                "reference": r.get("reference"),
                "account": r.get("account"),
                "amount_a": r.get("amount"),
                "amount_b": None,
                "variance": 0.0,
                "confidence": 0.0,
                "match_rule": "INVALID_DATA_FILTER",
                "reason": "Source A record contains missing Transaction ID or unparseable amount.",
                "record_a": r,
                "record_b": None
            })
            processed_a.add(idx)
            continue

        txid = r["transaction_id"]
        if id_counts_a.get(txid, 0) > 1:
            matched_pairs.append({
                "severity": ExceptionSeverity.HIGH,
                "status": ReconciliationStatus.DUPLICATE_CONTROL,
                "source_a_id": txid,
                "source_b_id": None,
                "reference": r.get("reference"),
                "account": r.get("account"),
                "amount_a": r.get("amount"),
                "amount_b": None,
                "variance": 0.0,
                "confidence": 0.0,
                "match_rule": "DUPLICATE_ID_FILTER",
                "reason": f"Duplicate Transaction ID '{txid}' detected in Source A.",
                "record_a": r,
                "record_b": None
            })
            processed_a.add(idx)
            continue

        dict_a_by_id[txid] = (idx, r)

        ref = r.get("reference")
        if pd.notna(ref):
            dict_a_by_ref.setdefault(ref, []).append((idx, r))

        acc = r.get("account")
        dt = r.get("date_str")
        amt = round(float(r["amount"]), 2) if pd.notna(r.get("amount")) else None
        if pd.notna(acc) and pd.notna(dt) and amt is not None:
            dict_a_by_acc_date_amt.setdefault((acc, dt, amt), []).append((idx, r))

    # Pre-process Source B duplicates & invalid rows
    dict_b_by_id = {}
    dict_b_by_ref = {}
    dict_b_by_acc_date_amt = {}

    for idx, r in enumerate(records_b):
        if pd.isna(r.get("transaction_id")) or pd.isna(r.get("amount")):
            matched_pairs.append({
                "severity": ExceptionSeverity.HIGH,
                "status": ReconciliationStatus.INVALID_DATA,
                "source_a_id": None,
                "source_b_id": r.get("transaction_id"),
                "reference": r.get("reference"),
                "account": r.get("account"),
                "amount_a": None,
                "amount_b": r.get("amount"),
                "variance": 0.0,
                "confidence": 0.0,
                "match_rule": "INVALID_DATA_FILTER",
                "reason": "Source B record contains missing Transaction ID or unparseable amount.",
                "record_a": None,
                "record_b": r
            })
            processed_b.add(idx)
            continue

        txid = r["transaction_id"]
        if id_counts_b.get(txid, 0) > 1:
            matched_pairs.append({
                "severity": ExceptionSeverity.HIGH,
                "status": ReconciliationStatus.DUPLICATE_CONTROL,
                "source_a_id": None,
                "source_b_id": txid,
                "reference": r.get("reference"),
                "account": r.get("account"),
                "amount_a": None,
                "amount_b": r.get("amount"),
                "variance": 0.0,
                "confidence": 0.0,
                "match_rule": "DUPLICATE_ID_FILTER",
                "reason": f"Duplicate Transaction ID '{txid}' detected in Source B.",
                "record_a": None,
                "record_b": r
            })
            processed_b.add(idx)
            continue

        dict_b_by_id[txid] = (idx, r)

        ref = r.get("reference")
        if pd.notna(ref):
            dict_b_by_ref.setdefault(ref, []).append((idx, r))

        acc = r.get("account")
        dt = r.get("date_str")
        amt = round(float(r["amount"]), 2) if pd.notna(r.get("amount")) else None
        if pd.notna(acc) and pd.notna(dt) and amt is not None:
            dict_b_by_acc_date_amt.setdefault((acc, dt, amt), []).append((idx, r))

    # --- MATCH PASS 1: RULE 1 - Exact Transaction ID ---
    for txid, (idx_a, rec_a) in list(dict_a_by_id.items()):
        if idx_a in processed_a:
            continue
        if txid in dict_b_by_id:
            idx_b, rec_b = dict_b_by_id[txid]
            if idx_b in processed_b:
                continue

            # Compare attributes
            amt_a = float(rec_a["amount"])
            amt_b = float(rec_b["amount"])
            var = round(amt_a - amt_b, 2)
            curr_a = str(rec_a.get("currency", "")).upper()
            curr_b = str(rec_b.get("currency", "")).upper()
            date_a = rec_a.get("date_str")
            date_b = rec_b.get("date_str")

            if curr_a and curr_b and curr_a != curr_b:
                status = ReconciliationStatus.CURRENCY_MISMATCH
                conf = 0.90
                rule = "RULE 1: Exact ID (Currency Mismatch)"
                reason = f"Transaction ID '{txid}' matched, but currency differs: Source A ({curr_a}) vs Source B ({curr_b})."
            elif abs(var) > 0.001:
                status = ReconciliationStatus.AMOUNT_MISMATCH
                conf = 0.95
                rule = "RULE 1: Exact ID (Amount Mismatch)"
                reason = f"Transaction ID '{txid}' matched structurally, but settlement amount differs by {rec_a.get('currency', 'INR')} {var:+,.2f} (A: {amt_a:,.2f} vs B: {amt_b:,.2f})."
            elif date_a and date_b and date_a != date_b:
                status = ReconciliationStatus.DATE_MISMATCH
                conf = 0.96
                rule = "RULE 1: Exact ID (Date Mismatch)"
                reason = f"Transaction ID '{txid}' matched amount exactly ({amt_a:,.2f}), but dates differ: Source A ({date_a}) vs Source B ({date_b})."
            else:
                status = ReconciliationStatus.MATCHED
                conf = 1.00
                rule = "RULE 1: Exact Transaction ID"
                reason = f"Exact match on Transaction ID '{txid}', Amount ({amt_a:,.2f}), Currency ({curr_a}), and Date ({date_a})."

            severity = determine_severity(status, var)
            matched_pairs.append({
                "severity": severity,
                "status": status,
                "source_a_id": txid,
                "source_b_id": txid,
                "reference": rec_a.get("reference") or rec_b.get("reference"),
                "account": rec_a.get("account") or rec_b.get("account"),
                "amount_a": amt_a,
                "amount_b": amt_b,
                "variance": var,
                "confidence": conf,
                "match_rule": rule,
                "reason": reason,
                "record_a": rec_a,
                "record_b": rec_b
            })

            processed_a.add(idx_a)
            processed_b.add(idx_b)

    # --- MATCH PASS 2: RULE 2 - Reference + Amount + Currency ---
    for ref, items_a in dict_a_by_ref.items():
        for idx_a, rec_a in items_a:
            if idx_a in processed_a:
                continue

            amt_a = round(float(rec_a["amount"]), 2)
            curr_a = str(rec_a.get("currency", "")).upper()

            if ref in dict_b_by_ref:
                for idx_b, rec_b in dict_b_by_ref[ref]:
                    if idx_b in processed_b:
                        continue

                    amt_b = round(float(rec_b["amount"]), 2)
                    curr_b = str(rec_b.get("currency", "")).upper()
                    date_a = rec_a.get("date_str")
                    date_b = rec_b.get("date_str")

                    if abs(amt_a - amt_b) <= 0.001 and curr_a == curr_b:
                        var = 0.0
                        if date_a and date_b and date_a != date_b:
                            status = ReconciliationStatus.DATE_MISMATCH
                            conf = 0.92
                            rule = "RULE 2: Reference + Amount (Date Mismatch)"
                            reason = f"Matched on Reference '{ref}' and Amount ({amt_a:,.2f}), but transaction dates differ: Source A ({date_a}) vs Source B ({date_b})."
                        else:
                            status = ReconciliationStatus.MATCHED
                            conf = 0.98
                            rule = "RULE 2: Reference + Amount + Currency"
                            reason = f"Deterministic match on Reference '{ref}', Amount ({amt_a:,.2f} {curr_a})."

                        severity = determine_severity(status, var)
                        matched_pairs.append({
                            "severity": severity,
                            "status": status,
                            "source_a_id": rec_a.get("transaction_id"),
                            "source_b_id": rec_b.get("transaction_id"),
                            "reference": ref,
                            "account": rec_a.get("account") or rec_b.get("account"),
                            "amount_a": amt_a,
                            "amount_b": amt_b,
                            "variance": var,
                            "confidence": conf,
                            "match_rule": rule,
                            "reason": reason,
                            "record_a": rec_a,
                            "record_b": rec_b
                        })

                        processed_a.add(idx_a)
                        processed_b.add(idx_b)
                        break

    # --- MATCH PASS 3: RULE 3 - Account + Date + Amount + Currency ---
    for key_tuple, items_a in dict_a_by_acc_date_amt.items():
        (acc, dt, amt) = key_tuple
        for idx_a, rec_a in items_a:
            if idx_a in processed_a:
                continue

            if key_tuple in dict_b_by_acc_date_amt:
                for idx_b, rec_b in dict_b_by_acc_date_amt[key_tuple]:
                    if idx_b in processed_b:
                        continue

                    curr_a = str(rec_a.get("currency", "")).upper()
                    curr_b = str(rec_b.get("currency", "")).upper()

                    if curr_a == curr_b:
                        status = ReconciliationStatus.MATCHED
                        conf = 0.90
                        rule = "RULE 3: Account + Date + Amount + Currency"
                        reason = f"Matched on Account '{acc}', Date '{dt}', and Amount ({amt:,.2f} {curr_a}). References differ (A: {rec_a.get('reference')} vs B: {rec_b.get('reference')})."

                        severity = determine_severity(status, 0.0)
                        matched_pairs.append({
                            "severity": severity,
                            "status": status,
                            "source_a_id": rec_a.get("transaction_id"),
                            "source_b_id": rec_b.get("transaction_id"),
                            "reference": rec_a.get("reference") or rec_b.get("reference"),
                            "account": acc,
                            "amount_a": amt,
                            "amount_b": amt,
                            "variance": 0.0,
                            "confidence": conf,
                            "match_rule": rule,
                            "reason": reason,
                            "record_a": rec_a,
                            "record_b": rec_b
                        })

                        processed_a.add(idx_a)
                        processed_b.add(idx_b)
                        break

    # --- MATCH PASS 4: Heuristic Reference Match (Amount Mismatch) ---
    for ref, items_a in dict_a_by_ref.items():
        for idx_a, rec_a in items_a:
            if idx_a in processed_a:
                continue

            if ref in dict_b_by_ref:
                for idx_b, rec_b in dict_b_by_ref[ref]:
                    if idx_b in processed_b:
                        continue

                    amt_a = float(rec_a["amount"])
                    amt_b = float(rec_b["amount"])
                    var = round(amt_a - amt_b, 2)
                    status = ReconciliationStatus.AMOUNT_MISMATCH
                    conf = 0.75
                    rule = "HEURISTIC: Reference Match (Amount Mismatch)"
                    reason = f"Matched on Reference '{ref}', but amounts differ by {rec_a.get('currency', 'INR')} {var:+,.2f} (Source A: {amt_a:,.2f} vs Source B: {amt_b:,.2f})."

                    severity = determine_severity(status, var)
                    matched_pairs.append({
                        "severity": severity,
                        "status": status,
                        "source_a_id": rec_a.get("transaction_id"),
                        "source_b_id": rec_b.get("transaction_id"),
                        "reference": ref,
                        "account": rec_a.get("account") or rec_b.get("account"),
                        "amount_a": amt_a,
                        "amount_b": amt_b,
                        "variance": var,
                        "confidence": conf,
                        "match_rule": rule,
                        "reason": reason,
                        "record_a": rec_a,
                        "record_b": rec_b
                    })

                    processed_a.add(idx_a)
                    processed_b.add(idx_b)
                    break

    # --- PASS 5: Remaining Unmatched Records ---
    for idx_a, rec_a in enumerate(records_a):
        if idx_a not in processed_a:
            amt_a = float(rec_a["amount"]) if pd.notna(rec_a.get("amount")) else 0.0
            matched_pairs.append({
                "severity": ExceptionSeverity.HIGH,
                "status": ReconciliationStatus.MISSING_IN_SOURCE_B,
                "source_a_id": rec_a.get("transaction_id"),
                "source_b_id": None,
                "reference": rec_a.get("reference"),
                "account": rec_a.get("account"),
                "amount_a": amt_a,
                "amount_b": None,
                "variance": amt_a,
                "confidence": 0.0,
                "match_rule": "UNMATCHED_FILTER",
                "reason": f"Transaction '{rec_a.get('transaction_id')}' exists in Source A ({amt_a:,.2f}) but was not found in Source B.",
                "record_a": rec_a,
                "record_b": None
            })

    for idx_b, rec_b in enumerate(records_b):
        if idx_b not in processed_b:
            amt_b = float(rec_b["amount"]) if pd.notna(rec_b.get("amount")) else 0.0
            matched_pairs.append({
                "severity": ExceptionSeverity.HIGH,
                "status": ReconciliationStatus.MISSING_IN_SOURCE_A,
                "source_a_id": None,
                "source_b_id": rec_b.get("transaction_id"),
                "reference": rec_b.get("reference"),
                "account": rec_b.get("account"),
                "amount_a": None,
                "amount_b": amt_b,
                "variance": -amt_b,
                "confidence": 0.0,
                "match_rule": "UNMATCHED_FILTER",
                "reason": f"Transaction '{rec_b.get('transaction_id')}' exists in Source B ({amt_b:,.2f}) but was not found in Source A.",
                "record_a": None,
                "record_b": rec_b
            })

    df_results = pd.DataFrame(matched_pairs)

    # --- SUMMARY CALCULATIONS ---
    total_a = float(norm_a["amount"].dropna().sum()) if not norm_a.empty else 0.0
    total_b = float(norm_b["amount"].dropna().sum()) if not norm_b.empty else 0.0

    count_a = len(norm_a)
    count_b = len(norm_b)

    matched_count = len(df_results[df_results["status"] == ReconciliationStatus.MATCHED]) if not df_results.empty else 0
    total_reconciled_records = len(df_results)

    rec_rate = (matched_count / total_reconciled_records * 100.0) if total_reconciled_records > 0 else 100.0

    gross_variance = float(df_results["variance"].abs().sum()) if not df_results.empty else 0.0

    status_counts = df_results["status"].value_counts().to_dict() if not df_results.empty else {}
    severity_counts = df_results["severity"].value_counts().to_dict() if not df_results.empty else {}

    unresolved_high_sev = severity_counts.get(ExceptionSeverity.HIGH, 0)
    total_dq_issues = quality_a["total_quality_issues"] + quality_b["total_quality_issues"]

    # Deterministic Health Status Formula
    if rec_rate >= 95.0 and unresolved_high_sev == 0 and gross_variance <= 5000.0 and total_dq_issues == 0:
        health_status = "HEALTHY"
        health_color = "#10B981"  # Emerald Green
        health_desc = "All reconciliation controls operating within normal thresholds."
    elif rec_rate >= 85.0 and unresolved_high_sev <= 5 and gross_variance <= 50000.0:
        health_status = "WARNING"
        health_color = "#F59E0B"  # Amber
        health_desc = f"Moderate variance or {unresolved_high_sev} unresolved high-severity exceptions requiring attention."
    else:
        health_status = "CRITICAL"
        health_color = "#EF4444"  # Crimson Red
        health_desc = f"Critical reconciliation rate ({rec_rate:.1f}%) or high unresolved exception volume ({unresolved_high_sev})."

    summary = {
        "source_a_total": total_a,
        "source_b_total": total_b,
        "source_a_count": count_a,
        "source_b_count": count_b,
        "total_records": total_reconciled_records,
        "matched_count": matched_count,
        "reconciliation_rate": round(rec_rate, 2),
        "gross_variance": round(gross_variance, 2),
        "status_counts": status_counts,
        "severity_counts": severity_counts,
        "unresolved_high_severity": unresolved_high_sev,
        "reconciliation_health": health_status,
        "health_color": health_color,
        "health_description": health_desc
    }

    return {
        "summary": summary,
        "results": df_results,
        "quality_a": quality_a,
        "quality_b": quality_b
    }

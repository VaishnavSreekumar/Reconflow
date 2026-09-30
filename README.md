# ReconFlow — Transaction Reconciliation & Exception Management

> **Production-Grade Financial Operations MVP** designed for automated transaction reconciliation, exception classification, deterministic decision traceability, and operational auditability.

> [!NOTE]
> Demo data is synthetic and review state is maintained for the active session.

---

## 1. Problem Statement

In banking, housing finance, and fintech operations, financial data resides across disparate source systems (e.g., Core Banking Systems, Payment Gateways, ERPs, and Escrow Accounts). Manual transaction reconciliation is error-prone, repetitive, and exception-heavy. 

Without automated, auditable tools:
- Finance teams waste hundreds of hours manually cross-referencing ledger entries.
- Unmatched balances create operational financial risks and regulatory compliance delays.
- Black-box matching engines fail to provide human-understandable audit trails for why records matched or failed to match.

---

## 2. Solution Overview

**ReconFlow** automates multi-tier transaction reconciliation between Source A (Core System) and Source B (Bank Settlement Gateway) while enforcing **100% deterministic decision explainability**. 

Every record pair processes through an indexed multi-tier matching engine, assigns a granular exception category, and exposes a plain-English **Decision Trace** detailing the exact field-level variance.

---

## 3. Architecture & Data Flow

```
Source A (Core System CSV/XLSX) ──┐
                                  ├─► Validation & Schema Normalization ──► Fast Indexed Matching Engine (O(N))
Source B (Bank Statement CSV/XLSX) ─┘                                                      │
                                                                                           ▼
                                                                                   Exception Classifier
                                                                                           │
                                                                                           ▼
                                                                                  Human Review Queue
                                                                                 ↙                  ↘
                                                                     Session Audit Store     Reports & Excel Packs
```

---

## 4. Matching Rules & Hierarchy

ReconFlow evaluates records using a strict, auditable hierarchy:

| Rule Tier | Matching Criteria | Confidence | Action / Output |
| :--- | :--- | :---: | :--- |
| **RULE 1** | **Exact Transaction ID** | 100% | Checks Amount, Currency & Date. If Amount differs $\rightarrow$ `AMOUNT_MISMATCH`. If Currency differs $\rightarrow$ `CURRENCY_MISMATCH`. If Date differs $\rightarrow$ `DATE_MISMATCH`. Else $\rightarrow$ `MATCHED`. |
| **RULE 2** | **Reference + Amount + Currency** | 98% | Matches structural reference & settlement amount. If date differs $\rightarrow$ `DATE_MISMATCH`. Else $\rightarrow$ `MATCHED`. |
| **RULE 3** | **Account + Date + Amount + Currency** | 90% | Matches ledger account, date, settlement amount across systems when reference differs. |
| **HEURISTIC**| **Reference Match (Amount Variance)** | 75% | Identifies payment reference match with fee deductions or partial settlements $\rightarrow$ `AMOUNT_MISMATCH`. |
| **FILTER** | **Unmatched / Controls** | 0% | Classifies isolated records as `MISSING_IN_SOURCE_A`, `MISSING_IN_SOURCE_B`, `DUPLICATE_CONTROL`, or `INVALID_DATA`. |

---

## 5. Exception Taxonomy

* **`MATCHED`**: Records agree across all reconciliation attributes.
* **`AMOUNT_MISMATCH`**: Structural match established, but settlement values differ (e.g. gateway fee deductions).
* **`CURRENCY_MISMATCH`**: Same transaction reference executed in mismatched currencies.
* **`DATE_MISMATCH`**: Amount & reference match, but settlement date reflects T+1 processing delay.
* **`MISSING_IN_SOURCE_A`**: Credit entry in bank statement missing in core ledger.
* **`MISSING_IN_SOURCE_B`**: Core ledger entry uncleared in bank settlement.
* **`DUPLICATE_CONTROL`**: Duplicate transaction IDs detected in a single batch.
* **`INVALID_DATA`**: Malformed dates, null IDs, or unparseable amounts flagged prior to matching.

---

## 6. Engineering Architecture: Deterministic Engine vs. LLMs/AI

### 💡 Why Core Reconciliation is Strictly Deterministic

In financial operations software, **core ledger matching MUST remain 100% deterministic and mathematically reproducible**. 

Allowing Generative AI or LLMs to autonomously decide whether two monetary records balance is an unacceptable operational risk:
1. **Hallucinations & Non-Determinism**: LLMs can produce varying outcomes for identical inputs across runs.
2. **Auditability Requirements**: Financial regulators and auditors require mathematical proof and reproducible decision rules, not probabilistic prompts.
3. **Zero Margin for Error**: A false positive match silences a financial discrepancy, leading to balance sheet leakage.

### Appropriate Role of AI in Financial Ops (Future Scope)
If AI components are added, they should serve strictly as **read-only metadata assistants**:
* Generating natural-language executive summaries of a batch of exceptions.
* Translating complex multi-field decision traces into executive bullet points.
* Suggesting exception priority queues for ops analyst review.

---

## 7. Technology Stack

* **Language**: Python 3.10+
* **Frontend**: Streamlit (with custom financial-operations dark theme CSS)
* **Data Processing**: Pandas, NumPy (Hashmap indexing for $O(N)$ matching performance)
* **Data Visualization**: Plotly Express & Plotly Graph Objects
* **Excel Reporting**: OpenPyXL (multi-sheet styled workbook exporter)
* **Testing**: Pytest

---

## 8. How to Run the Application

### 1. Clone & Set Up Directory
```bash
cd C:\Users\vaish\.gemini\antigravity-ide\scratch\reconflow
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Streamlit Application
```bash
streamlit run app/main.py
```

### 4. Load Demo Data
In the sidebar, click **`⚡ Load Synthetic Demo Dataset`** to populate 150 realistic housing finance transaction pairs with controlled edge cases.

---

## 9. Test Suite Execution

Run the complete test suite:

```bash
pytest -v
```

Tests cover exact matching, reference matching, account/date/amount matching, missing records, amount variance, duplicate controls, data quality diagnostics, deterministic repeatability, and multi-sheet Excel generation.

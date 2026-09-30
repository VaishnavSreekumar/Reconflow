"""
ReconFlow — Transaction Reconciliation & Exception Management.
Main Streamlit Financial Operations Application.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly via Streamlit
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from app.validation import validate_schema, inspect_data_quality
from app.engine import reconcile_datasets, ReconciliationStatus, ExceptionSeverity
from app.demo_data import generate_synthetic_demo_data
from app.review_state import get_review_store, ReviewStatus
from app.export import (
    generate_reconciliation_csv,
    generate_exceptions_csv,
    generate_excel_review_pack,
)

# Page configuration
st.set_page_config(
    page_title="ReconFlow — Transaction Reconciliation",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Financial Operations Styling
st.markdown("""
<style>
    /* Main Background and Fonts */
    .main {
        background-color: #0B0F19;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #E2E8F0;
    }
    
    /* Header Styling */
    .app-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #F8FAFC;
        letter-spacing: -0.025em;
        margin-bottom: 0px;
    }
    .app-subtitle {
        font-size: 0.95rem;
        color: #94A3B8;
        font-weight: 500;
        margin-bottom: 1.5rem;
    }

    /* Metric Card Styling */
    .metric-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .metric-label {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #94A3B8;
        letter-spacing: 0.05em;
        margin-bottom: 0.35rem;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #F8FAFC;
    }
    .metric-sub {
        font-size: 0.78rem;
        color: #64748B;
        margin-top: 0.25rem;
    }

    /* Status Badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-matched { background-color: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981; }
    .badge-mismatch { background-color: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid #EF4444; }
    .badge-warning { background-color: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B; }
    .badge-info { background-color: rgba(59, 130, 246, 0.15); color: #3B82F6; border: 1px solid #3B82F6; }

    /* Trace Drawer */
    .trace-card {
        background-color: #0F172A;
        border-left: 4px solid #3B82F6;
        border-radius: 6px;
        padding: 1.25rem 1.5rem;
        margin-top: 0.75rem;
        margin-bottom: 1rem;
    }
    .trace-title {
        font-size: 0.85rem;
        font-weight: 700;
        color: #60A5FA;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.75rem;
    }

    /* Diff highlighting */
    .diff-highlight {
        background-color: rgba(239, 68, 68, 0.25);
        color: #FCA5A5;
        font-weight: 700;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        border: 1px solid rgba(239, 68, 68, 0.5);
    }
    .diff-match {
        color: #34D399;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initializes session state objects."""
    if "df_a" not in st.session_state:
        st.session_state.df_a = None
    if "df_b" not in st.session_state:
        st.session_state.df_b = None
    if "recon_output" not in st.session_state:
        st.session_state.recon_output = None
    if "selected_exception_key" not in st.session_state:
        st.session_state.selected_exception_key = None
    if "demo_loaded" not in st.session_state:
        st.session_state.demo_loaded = False


def render_sidebar():
    st.sidebar.markdown("### ⚙️ Operational Controls")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 Data Ingestion")

    # Fast Synthetic Demo Load Button
    if st.sidebar.button("⚡ Load Synthetic Demo Dataset", use_container_width=True, type="primary"):
        df_a, df_b = generate_synthetic_demo_data(num_records=150, seed=42)
        st.session_state.df_a = df_a
        st.session_state.df_b = df_b
        st.session_state.recon_output = reconcile_datasets(df_a, df_b)
        st.session_state.demo_loaded = True
        st.sidebar.success("Synthetic Demo Dataset Loaded! (150 pairs)")

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Upload Custom Datasets")

    file_a = st.sidebar.file_uploader("Upload Source A (Core System CSV/XLSX)", type=["csv", "xlsx"])
    file_b = st.sidebar.file_uploader("Upload Source B (Bank Statement CSV/XLSX)", type=["csv", "xlsx"])

    if file_a is not None and file_b is not None:
        if st.sidebar.button("▶️ Execute Reconciliation Engine", use_container_width=True):
            try:
                df_a = pd.read_csv(file_a) if file_a.name.endswith(".csv") else pd.read_excel(file_a)
                df_b = pd.read_csv(file_b) if file_b.name.endswith(".csv") else pd.read_excel(file_b)

                valid_a, err_a = validate_schema(df_a, "Source A")
                valid_b, err_b = validate_schema(df_b, "Source B")

                if not valid_a:
                    st.sidebar.error(f"Source A Missing Columns: {', '.join(err_a)}")
                elif not valid_b:
                    st.sidebar.error(f"Source B Missing Columns: {', '.join(err_b)}")
                else:
                    st.session_state.df_a = df_a
                    st.session_state.df_b = df_b
                    st.session_state.recon_output = reconcile_datasets(df_a, df_b)
                    st.session_state.demo_loaded = False
                    st.sidebar.success("Custom Reconciliation Completed!")
            except Exception as e:
                st.sidebar.error(f"Error loading files: {str(e)}")

    if st.session_state.demo_loaded:
        st.sidebar.info("ℹ️ **Synthetic Demo Dataset Active**\nFictional housing finance data for interview demonstration.")


def render_overview():
    st.markdown("## Executive Overview Dashboard")

    if st.session_state.recon_output is None:
        st.warning("⚠️ No reconciliation dataset loaded. Click **'⚡ Load Synthetic Demo Dataset'** in the sidebar to view live dashboard.")
        return

    summary = st.session_state.recon_output["summary"]
    review_store = get_review_store()
    all_reviews = review_store.get_all_reviews()

    reviewed_count = sum(1 for r in all_reviews if r["status"] == ReviewStatus.REVIEWED)
    escalated_count = sum(1 for r in all_reviews if r["status"] == ReviewStatus.ESCALATED)
    total_exceptions = summary["total_records"] - summary["matched_count"]

    # Top KPI Row (Calculated dynamically from dataset)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Source A Total</div>
            <div class="metric-value">₹{summary['source_a_total']:,.2f}</div>
            <div class="metric-sub">{summary['source_a_count']:,} transactions</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Source B Total</div>
            <div class="metric-value">₹{summary['source_b_total']:,.2f}</div>
            <div class="metric-sub">{summary['source_b_count']:,} transactions</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Records Reviewed</div>
            <div class="metric-value">{reviewed_count} / {total_exceptions}</div>
            <div class="metric-sub">{escalated_count} escalated</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Reconciliation Rate</div>
            <div class="metric-value">{summary['reconciliation_rate']:.1f}%</div>
            <div class="metric-sub">{summary['matched_count']} matched pairs</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Gross Variance</div>
            <div class="metric-value" style="color: #EF4444;">₹{summary['gross_variance']:,.2f}</div>
            <div class="metric-sub">Total absolute variance</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Reconciliation Health Indicator Card (Deterministic)
    h_color = summary["health_color"]
    st.markdown(f"""
    <div style="background-color: #1E293B; border-left: 6px solid {h_color}; border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h3 style="margin: 0; color: #F8FAFC;">Reconciliation Health: <span style="color: {h_color};">{summary['reconciliation_health']}</span></h3>
                <p style="margin: 0.35rem 0 0 0; color: #94A3B8; font-size: 0.9rem;">{summary['health_description']}</p>
            </div>
            <div style="text-align: right;">
                <span class="badge" style="background-color: {h_color}; color: #000; font-size: 0.85rem;">DETERMINISTIC EVALUATION</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Charts Row
    c_chart1, c_chart2 = st.columns([1, 1])

    status_counts = summary["status_counts"]
    df_status = pd.DataFrame(list(status_counts.items()), columns=["Status", "Count"])

    with c_chart1:
        st.markdown("### Reconciliation Status Breakdown")
        fig_donut = px.pie(
            df_status,
            values="Count",
            names="Status",
            hole=0.55,
            color_discrete_sequence=px.colors.qualitative.Dark24
        )
        fig_donut.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E2E8F0"),
            showlegend=True
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with c_chart2:
        st.markdown("### Variance by Exception Category")
        df_res = st.session_state.recon_output["results"]
        if not df_res.empty:
            var_by_status = df_res.groupby("status")["variance"].apply(lambda s: s.abs().sum()).reset_index()
            fig_bar = px.bar(
                var_by_status,
                x="status",
                y="variance",
                color="status",
                labels={"status": "Exception Type", "variance": "Gross Variance (INR)"},
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig_bar.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E2E8F0"),
                showlegend=False
            )
            st.plotly_chart(fig_bar, use_container_width=True)


def render_exception_queue():
    st.markdown("## Exception Queue & Review Matrix")

    if st.session_state.recon_output is None:
        st.warning("⚠️ Please load synthetic demo data or upload datasets first.")
        return

    df_results = st.session_state.recon_output["results"].copy()
    if df_results.empty:
        st.info("No records found.")
        return

    # Attach human review states dynamically
    review_store = get_review_store()
    review_statuses = []
    for idx, row in df_results.iterrows():
        key = review_store.make_key(row["source_a_id"], row["source_b_id"], row["reference"])
        rev_info = review_store.get_review(key)
        review_statuses.append(rev_info["status"])

    df_results["review_status"] = review_statuses

    # Filter Controls
    st.markdown("#### Filter Exception Queue")
    f_col1, f_col2, f_col3, f_col4, f_col5, f_col6 = st.columns(6)

    with f_col1:
        selected_severity = st.multiselect("Severity", options=["HIGH", "MEDIUM", "LOW", "NONE"], default=["HIGH", "MEDIUM", "LOW"])
    with f_col2:
        all_types = list(df_results["status"].unique())
        selected_types = st.multiselect("Exception Category", options=all_types, default=all_types)
    with f_col3:
        accounts = [a for a in df_results["account"].dropna().unique()]
        selected_accounts = st.multiselect("Account Filter", options=accounts, default=accounts)
    with f_col4:
        selected_review_status = st.multiselect("Review State", options=["UNREVIEWED", "REVIEWED", "ESCALATED"], default=["UNREVIEWED", "REVIEWED", "ESCALATED"])
    with f_col5:
        min_conf = st.slider("Min Confidence", min_value=0, max_value=100, value=0, step=5)
    with f_col6:
        search_query = st.text_input("🔍 Search TxID / Ref / Acc", "").strip()

    # Apply Filters
    filtered_df = df_results.copy()
    if selected_severity:
        filtered_df = filtered_df[filtered_df["severity"].isin(selected_severity)]
    if selected_types:
        filtered_df = filtered_df[filtered_df["status"].isin(selected_types)]
    if selected_accounts:
        filtered_df = filtered_df[filtered_df["account"].isin(selected_accounts)]
    if selected_review_status:
        filtered_df = filtered_df[filtered_df["review_status"].isin(selected_review_status)]
    if min_conf > 0:
        filtered_df = filtered_df[filtered_df["confidence"] >= (min_conf / 100.0)]
    if search_query:
        sq = search_query.lower()
        filtered_df = filtered_df[
            filtered_df["source_a_id"].astype(str).str.lower().str.contains(sq) |
            filtered_df["source_b_id"].astype(str).str.lower().str.contains(sq) |
            filtered_df["reference"].astype(str).str.lower().str.contains(sq) |
            filtered_df["account"].astype(str).str.lower().str.contains(sq)
        ]

    st.markdown(f"Showing **{len(filtered_df)}** exception records matching filters:")

    # Table view
    disp_cols = [
        "severity", "review_status", "status", "source_a_id", "source_b_id",
        "reference", "account", "amount_a", "amount_b", "variance", "confidence", "match_rule"
    ]
    st.dataframe(
        filtered_df[disp_cols],
        use_container_width=True,
        column_config={
            "amount_a": st.column_config.NumberColumn("Amount A (INR)", format="₹%.2f"),
            "amount_b": st.column_config.NumberColumn("Amount B (INR)", format="₹%.2f"),
            "variance": st.column_config.NumberColumn("Variance (INR)", format="₹%.2f"),
            "confidence": st.column_config.NumberColumn("Confidence Score", format="%.0f%%"),
        },
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("### 🔍 Select Record for Detailed Decision Trace & Human Review")

    if not filtered_df.empty:
        record_labels = [
            f"[{r['severity']}] {r['status']} | Ref: {r['reference']} | A: {r['source_a_id']} vs B: {r['source_b_id']}"
            for _, r in filtered_df.iterrows()
        ]
        selected_idx = st.selectbox("Choose Exception Record to Inspect:", range(len(filtered_df)), format_func=lambda i: record_labels[i])
        selected_record = filtered_df.iloc[selected_idx]

        key = review_store.make_key(
            selected_record["source_a_id"],
            selected_record["source_b_id"],
            selected_record["reference"]
        )
        st.session_state.selected_exception_key = key
        
        if st.button("👉 Open Detailed Review Panel", type="primary"):
            st.session_state.current_page = "Reconciliation Detail"
            st.rerun()


def render_reconciliation_detail():
    st.markdown("## Reconciliation Exception Detail & Decision Trace")

    if st.session_state.recon_output is None:
        st.warning("⚠️ Please load synthetic demo data or upload datasets first.")
        return

    df_results = st.session_state.recon_output["results"]
    review_store = get_review_store()

    # Record selector
    keys = [
        review_store.make_key(r["source_a_id"], r["source_b_id"], r["reference"])
        for _, r in df_results.iterrows()
    ]
    labels = [
        f"[{r['severity']}] {r['status']} - Ref: {r['reference']} (A: {r['source_a_id']} | B: {r['source_b_id']})"
        for _, r in df_results.iterrows()
    ]

    selected_key = st.session_state.selected_exception_key or (keys[0] if keys else None)
    default_idx = keys.index(selected_key) if selected_key in keys else 0

    idx = st.selectbox("Select Record to Inspect Trace:", range(len(df_results)), index=default_idx, format_func=lambda i: labels[i])
    rec = df_results.iloc[idx]
    current_key = keys[idx]
    st.session_state.selected_exception_key = current_key

    rev_info = review_store.get_review(current_key)

    st.markdown("---")

    rec_a = rec.get("record_a") or {}
    rec_b = rec.get("record_b") or {}

    # Field-Level Difference Detection
    val_a_txid = rec_a.get("transaction_id")
    val_b_txid = rec_b.get("transaction_id")
    val_a_ref = rec_a.get("reference")
    val_b_ref = rec_b.get("reference")
    val_a_acc = rec_a.get("account")
    val_b_acc = rec_b.get("account")
    val_a_date = rec_a.get("date_str") or rec_a.get("date")
    val_b_date = rec_b.get("date_str") or rec_b.get("date")
    val_a_amt = rec_a.get("amount")
    val_b_amt = rec_b.get("amount")
    val_a_curr = rec_a.get("currency")
    val_b_curr = rec_b.get("currency")

    diff_txid = (val_a_txid != val_b_txid) and bool(val_a_txid and val_b_txid)
    diff_ref = (val_a_ref != val_b_ref) and bool(val_a_ref and val_b_ref)
    diff_acc = (val_a_acc != val_b_acc) and bool(val_a_acc and val_b_acc)
    diff_date = (val_a_date != val_b_date) and bool(val_a_date and val_b_date)
    diff_amt = (val_a_amt is not None and val_b_amt is not None) and (abs(float(val_a_amt) - float(val_b_amt)) > 0.001)
    diff_curr = (val_a_curr != val_b_curr) and bool(val_a_curr and val_b_curr)

    # Side by Side Comparison
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 🏢 SOURCE A (Core System)")
        if rec_a:
            st.markdown(f"**Transaction ID:** <span class='{'diff-highlight' if diff_txid else 'diff-match'}'>{val_a_txid}</span>", unsafe_allow_html=True)
            st.markdown(f"**Reference:** <span class='{'diff-highlight' if diff_ref else 'diff-match'}'>{val_a_ref}</span>", unsafe_allow_html=True)
            st.markdown(f"**Account:** <span class='{'diff-highlight' if diff_acc else 'diff-match'}'>{val_a_acc}</span>", unsafe_allow_html=True)
            st.markdown(f"**Date:** <span class='{'diff-highlight' if diff_date else 'diff-match'}'>{val_a_date}</span>", unsafe_allow_html=True)
            st.markdown(f"**Amount:** <span class='{'diff-highlight' if diff_amt else 'diff-match'}'>₹{float(val_a_amt):,.2f}</span>" if val_a_amt is not None else "**Amount:** N/A", unsafe_allow_html=True)
            st.markdown(f"**Currency:** <span class='{'diff-highlight' if diff_curr else 'diff-match'}'>{val_a_curr}</span>", unsafe_allow_html=True)
        else:
            st.warning("❌ Record Missing in Source A")

    with col_b:
        st.markdown("#### 🏦 SOURCE B (Bank Settlement)")
        if rec_b:
            st.markdown(f"**Transaction ID:** <span class='{'diff-highlight' if diff_txid else 'diff-match'}'>{val_b_txid}</span>", unsafe_allow_html=True)
            st.markdown(f"**Reference:** <span class='{'diff-highlight' if diff_ref else 'diff-match'}'>{val_b_ref}</span>", unsafe_allow_html=True)
            st.markdown(f"**Account:** <span class='{'diff-highlight' if diff_acc else 'diff-match'}'>{val_b_acc}</span>", unsafe_allow_html=True)
            st.markdown(f"**Date:** <span class='{'diff-highlight' if diff_date else 'diff-match'}'>{val_b_date}</span>", unsafe_allow_html=True)
            st.markdown(f"**Amount:** <span class='{'diff-highlight' if diff_amt else 'diff-match'}'>₹{float(val_b_amt):,.2f}</span>" if val_b_amt is not None else "**Amount:** N/A", unsafe_allow_html=True)
            st.markdown(f"**Currency:** <span class='{'diff-highlight' if diff_curr else 'diff-match'}'>{val_b_curr}</span>", unsafe_allow_html=True)
        else:
            st.warning("❌ Record Missing in Source B")

    st.markdown("<br>", unsafe_allow_html=True)

    # Validation Signals Construction
    signals = []
    if diff_amt:
        var_val = float(val_a_amt) - float(val_b_amt)
        signals.append(f"⚠️ Amount Variance of ₹{var_val:+,.2f}")
    if diff_date:
        signals.append(f"📅 Date shift: A({val_a_date}) vs B({val_b_date})")
    if diff_curr:
        signals.append(f"💱 Currency Mismatch: A({val_a_curr}) vs B({val_b_curr})")
    if diff_ref:
        signals.append(f"🔗 Reference Discrepancy: A({val_a_ref}) vs B({val_b_ref})")
    if not rec_a:
        signals.append("❌ Missing in Core System Ledger (Source A)")
    if not rec_b:
        signals.append("❌ Missing in Bank Statement Gateway (Source B)")
    if not signals:
        signals.append("✅ All attribute comparisons aligned cleanly.")

    signals_str = " | ".join(signals)

    # Decision Trace Panel (Including ALL required trace attributes)
    st.markdown(f"""
    <div class="trace-card">
        <div class="trace-title">🛡️ Deterministic Decision Trace</div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 0.75rem;">
            <div><strong>MATCH RULE:</strong> {rec['match_rule']}</div>
            <div><strong>CONFIDENCE:</strong> {rec['confidence']*100:.0f}%</div>
            <div><strong>CONTROL RESULT:</strong> <span class="badge badge-warning">{rec['status']}</span></div>
            <div><strong>SEVERITY:</strong> <span class="badge badge-info">{rec['severity']}</span></div>
            <div><strong>VARIANCE:</strong> ₹{rec['variance']:+,.2f}</div>
            <div><strong>REVIEW STATUS:</strong> {rev_info['status']}</div>
        </div>
        <div style="margin-top: 0.5rem;"><strong>DETERMINISTIC RATIONALE:</strong></div>
        <div style="color: #94A3B8; font-size: 0.95rem; margin-top: 0.25rem;">{rec['reason']}</div>
        <div style="margin-top: 0.75rem;"><strong>VALIDATION SIGNALS:</strong></div>
        <div style="color: #60A5FA; font-size: 0.9rem; margin-top: 0.25rem;">{signals_str}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Human Review Panel
    st.markdown("### ✍️ Human Review Workflow")
    r_col1, r_col2 = st.columns([1, 1])

    with r_col1:
        st.write(f"Current Status: **{rev_info['status']}**")
        if rev_info.get("updated_at"):
            st.caption(f"Last updated by {rev_info.get('reviewer')} on {rev_info.get('updated_at')}")

        reviewer_name = st.text_input("Reviewer Name / ID", value=rev_info.get("reviewer") or "Ops Analyst")
        note_text = st.text_area("Audit Note / Decision Rationale", value=rev_info.get("note") or "", placeholder="Enter audit comments...")

        btn_c1, btn_c2, btn_c3 = st.columns(3)
        with btn_c1:
            if st.button("✅ Mark Reviewed", use_container_width=True):
                review_store.update_review(current_key, ReviewStatus.REVIEWED, note_text, reviewer_name)
                st.success("Record marked as Reviewed!")
                st.rerun()
        with btn_c2:
            if st.button("🚨 Escalate", use_container_width=True):
                review_store.update_review(current_key, ReviewStatus.ESCALATED, note_text, reviewer_name)
                st.warning("Record Escalated!")
                st.rerun()
        with btn_c3:
            if st.button("↺ Reset Status", use_container_width=True):
                review_store.update_review(current_key, ReviewStatus.UNREVIEWED, "", reviewer_name)
                st.info("Reset to Unreviewed.")
                st.rerun()

    with r_col2:
        st.markdown("#### Audit History Trail")
        history = rev_info.get("history", [])
        if history:
            for h in reversed(history):
                st.markdown(f"- **{h['timestamp']}** | `{h['reviewer']}` changed status from `{h['from_status']}` → `{h['to_status']}`")
                if h.get('note'):
                    st.caption(f"  Note: \"{h['note']}\"")
        else:
            st.caption("No audit history for this record yet.")


def render_data_quality():
    st.markdown("## Data Quality & Validation Diagnostics")

    st.info("💡 **Financial Operations Philosophy:** Bad input data should be visible, not hidden. ReconFlow audits source records for missing IDs, malformed dates, and illegal values prior to matching.")

    if st.session_state.recon_output is None:
        st.warning("⚠️ Please load synthetic demo data or upload datasets first.")
        return

    q_a = st.session_state.recon_output["quality_a"]
    q_b = st.session_state.recon_output["quality_b"]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Source A (Core Loan System)")
        st.metric("Total Row Count", f"{q_a['total_rows']:,}")
        st.metric("Quality Score", f"{q_a['health_score']}%")

        metrics_df_a = pd.DataFrame([
            {"Issue Type": "Duplicate Transaction IDs", "Count": q_a["duplicate_ids"]},
            {"Issue Type": "Missing Transaction IDs", "Count": q_a["missing_transaction_ids"]},
            {"Issue Type": "Invalid Dates", "Count": q_a["invalid_dates"]},
            {"Issue Type": "Invalid Amounts", "Count": q_a["invalid_amounts"]},
            {"Issue Type": "Negative Amounts", "Count": q_a["negative_amounts"]},
            {"Issue Type": "Missing References", "Count": q_a["missing_references"]},
            {"Issue Type": "Missing Accounts", "Count": q_a["missing_accounts"]},
        ])
        st.table(metrics_df_a)

    with col2:
        st.markdown("### Source B (Bank Statement Gateway)")
        st.metric("Total Row Count", f"{q_b['total_rows']:,}")
        st.metric("Quality Score", f"{q_b['health_score']}%")

        metrics_df_b = pd.DataFrame([
            {"Issue Type": "Duplicate Transaction IDs", "Count": q_b["duplicate_ids"]},
            {"Issue Type": "Missing Transaction IDs", "Count": q_b["missing_transaction_ids"]},
            {"Issue Type": "Invalid Dates", "Count": q_b["invalid_dates"]},
            {"Issue Type": "Invalid Amounts", "Count": q_b["invalid_amounts"]},
            {"Issue Type": "Negative Amounts", "Count": q_b["negative_amounts"]},
            {"Issue Type": "Missing References", "Count": q_b["missing_references"]},
            {"Issue Type": "Missing Accounts", "Count": q_b["missing_accounts"]},
        ])
        st.table(metrics_df_b)


def render_reports():
    st.markdown("## Reports & Executive Export Center")

    if st.session_state.recon_output is None:
        st.warning("⚠️ Please load synthetic demo data or upload datasets first.")
        return

    st.markdown("Download auditable reconciliation outputs for operations sign-off, external auditors, or interview demonstration.")

    df_results = st.session_state.recon_output["results"]
    review_store = get_review_store()
    review_notes = review_store.get_all_reviews()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📄 Reconciliation CSV")
        st.caption("Complete dataset containing all paired transactions, matching rules, and decision rationales.")
        csv_full = generate_reconciliation_csv(df_results)
        st.download_button(
            label="Download Full Reconciliation CSV",
            data=csv_full,
            file_name="ReconFlow_Full_Reconciliation.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        st.markdown("### ⚠️ Exception CSV")
        st.caption("Filtered subset of unresolved variance exceptions requiring human review.")
        csv_exc = generate_exceptions_csv(df_results)
        st.download_button(
            label="Download Exception CSV",
            data=csv_exc,
            file_name="ReconFlow_Exceptions_Only.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col3:
        st.markdown("### 📊 Excel Review Pack")
        st.caption("Professional 5-sheet styled OpenPyXL workbook formatted for executive presentation.")
        excel_bytes = generate_excel_review_pack(st.session_state.recon_output, review_notes)
        st.download_button(
            label="Download Excel Review Pack (.xlsx)",
            data=excel_bytes,
            file_name="ReconFlow_Executive_Review_Pack.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )

    st.markdown("---")
    st.markdown("### Excel Review Pack Sheet Structure")
    st.markdown("""
    - **Sheet 1: Executive Summary**: Top KPIs, Reconciliation Health Indicator, and Exception Taxonomy breakdown.
    - **Sheet 2: Reconciliation Results**: Complete raw pair reconciliation dataset with formatted monetary values.
    - **Sheet 3: Exceptions**: Isolated list of variance records with severity levels.
    - **Sheet 4: Data Quality**: Comprehensive audit metrics on Source A & Source B input integrity.
    - **Sheet 5: Review Notes**: Complete timestamped audit trail of human review actions and analyst comments.
    """)


def main():
    init_session_state()
    render_sidebar()

    # Application Header
    st.markdown('<div class="app-title">ReconFlow</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Transaction Reconciliation & Exception Management</div>', unsafe_allow_html=True)

    # Main Navigation Tabs
    pages = ["Overview", "Exception Queue", "Reconciliation Detail", "Data Quality", "Reports"]
    
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Overview"

    selected_tab = st.radio(
        "Navigation",
        options=pages,
        index=pages.index(st.session_state.current_page),
        horizontal=True,
        label_visibility="collapsed"
    )
    st.session_state.current_page = selected_tab

    st.markdown("---")

    if selected_tab == "Overview":
        render_overview()
    elif selected_tab == "Exception Queue":
        render_exception_queue()
    elif selected_tab == "Reconciliation Detail":
        render_reconciliation_detail()
    elif selected_tab == "Data Quality":
        render_data_quality()
    elif selected_tab == "Reports":
        render_reports()


if __name__ == "__main__":
    main()

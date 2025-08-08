"""
Multi-Debt Payoff & What‑If Calculator
=====================================
A **Streamlit** app to compare minimum‑payment vs. actual‑payment plans for multiple debts and explore what‑if scenarios.

Run locally with:

    pip install streamlit pandas numpy
    streamlit run debt_calculator_app.py

© 2025 Personal Finance Tools · MIT‑licensed
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

# =====================================================================
# Helper functions
# =====================================================================

def amortization_schedule(
    balance: float,
    monthly_rate: float,
    payment: float,
    *,
    extra: float = 0.0,
) -> tuple[pd.DataFrame, float]:
    """Return schedule DataFrame and total interest."""
    if balance <= 0:
        raise ValueError("Balance must be > 0")
    if payment + extra <= balance * monthly_rate and monthly_rate > 0:
        raise ValueError("Payment too low to cover interest – increase it.")

    rows, month, total_interest = [], 0, 0.0
    while balance > 0:
        month += 1
        interest = balance * monthly_rate
        principal = payment + extra - interest
        principal = min(principal, balance)
        balance -= principal
        total_interest += interest
        rows.append(
            {
                "Month": month,
                "Payment": payment + extra,
                "Principal": principal,
                "Interest": interest,
                "Balance": balance,
            }
        )
    df = pd.DataFrame(rows)
    return df, total_interest


# =====================================================================
# Streamlit layout & state
# =====================================================================

st.set_page_config(
    page_title="Debt Payoff Calculator",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("💸 Multi‑Debt Payoff & What‑If Calculator")

# ---------------- Sidebar — Debts table ----------------

st.sidebar.header("Debts")
DEFAULT = pd.DataFrame(
    {
        "Name": ["Card A"],
        "Balance": [10_000.0],
        "Annual Rate (%)": [18.99],
        "Minimum Payment": [200.0],
        "Monthly Payment": [300.0],
    }
)

if "debts" not in st.session_state:
    st.session_state.debts = DEFAULT.copy()

edited_df: pd.DataFrame = st.sidebar.data_editor(
    st.session_state.debts,
    num_rows="dynamic",
    use_container_width=True,
    key="debt_editor",
)

st.session_state.debts = edited_df

debts = edited_df.dropna(
    subset=["Balance", "Annual Rate (%)", "Minimum Payment", "Monthly Payment"]
).copy()

if debts.empty:
    st.info("Add at least one debt to begin.")
    st.stop()

# -------------- Build minimum & actual schedules ---------------

schedules_min, schedules_act = {}, {}
min_interest_total, act_interest_total = 0.0, 0.0
max_months_act = 0
errors = []

for _, r in debts.iterrows():
    name = str(r["Name"]).strip() or "Unnamed Debt"
    bal = float(r["Balance"])
    rate_m = float(r["Annual Rate (%)"]) / 100 / 12
    p_min = float(r["Minimum Payment"])
    p_act = float(r["Monthly Payment"])

    # Minimum schedule
    try:
        df_min, int_min = amortization_schedule(bal, rate_m, p_min)
        schedules_min[name] = df_min
        min_interest_total += int_min
    except ValueError as exc:
        errors.append(f"{name} (minimum): {exc}")
        continue

    # Actual schedule
    try:
        df_act, int_act = amortization_schedule(bal, rate_m, p_act)
        schedules_act[name] = df_act
        act_interest_total += int_act
        max_months_act = max(max_months_act, len(df_act))
    except ValueError as exc:
        errors.append(f"{name} (actual): {exc}")

if errors:
    st.error("\n".join(errors))
    st.stop()

# ---------------- Dashboard metrics -------------------

total_balance = debts["Balance"].sum()
monthly_payment_sum = debts["Monthly Payment"].sum()
minimum_payment_sum = debts["Minimum Payment"].sum()
interest_saved_total = min_interest_total - act_interest_total

c1, c2, c3 = st.columns(3)

c1.metric("⏱️ Payoff Time (longest)", f"{max_months_act} mo", f"{max_months_act/12:.1f} yr")

c2.metric("💰 Total Interest (actual)", f"${act_interest_total:,.2f}")

c3.metric("💸 Interest Saved vs Min", f"${interest_saved_total:,.2f}")

c4, c5 = st.columns(2)
c4.metric("🧾 Sum of Monthly Payments", f"${monthly_payment_sum:,.2f}")
c5.metric("📉 Sum of Minimum Payments", f"${minimum_payment_sum:,.2f}")

# ---------------- Balance curves with toggles ----------

st.subheader("Balance Curves")

# Build balance DataFrame containing each debt and total
balances_df = (
    pd.concat({n: df.set_index("Month")["Balance"] for n, df in schedules_act.items()}, axis=1)
    .ffill()
    .fillna(0.0)
)
balances_df["Total Balance"] = balances_df.sum(axis=1)

all_cols = list(balances_df.columns)
selected_cols = st.multiselect(
    "Select balances to display", all_cols, default=["Total Balance"]
)

if selected_cols:
    st.line_chart(balances_df[selected_cols])

# --------------- Optional individual amortization tables ------------

if st.checkbox("Show individual amortization tables"):
    for n, df in schedules_act.items():
        st.markdown(f"#### {n} – Actual Payments")
        st.dataframe(
            df.style.format(
                {
                    "Payment": "${:,.2f}",
                    "Principal": "${:,.2f}",
                    "Interest": "${:,.2f}",
                    "Balance": "${:,.2f}",
                }
            ),
            height=380,
        )

# ================ Per‑debt What‑If Scenarios =================

st.header("🔮 What‑If Scenarios (per debt)")
sel_name = st.selectbox("Select a debt", list(schedules_act.keys()))
base_df = schedules_act[sel_name]
row = debts.loc[debts["Name"] == sel_name].iloc[0]

balance = float(row["Balance"])
annual_rate = float(row["Annual Rate (%)"])
monthly_payment = float(row["Monthly Payment"])
monthly_rate = annual_rate / 100 / 12
base_interest = base_df["Interest"].sum()

scenario = st.selectbox(
    "Scenario",
    (
        "Pay off now",
        "Extra monthly payment",
        "Lower interest rate (refinance)",
        "Increase monthly payment",
    ),
)

if scenario == "Pay off now":
    st.metric("Interest Saved (lifetime)", f"${base_interest:,.2f}")
    st.info("Paying today avoids all future interest on this debt.")

elif scenario == "Extra monthly payment":
    extra = st.number_input("Extra monthly ($)", 0.0, 1_000_000.0, 50.0, 10.0, format="%.2f")
    if extra > 0:
        extra_df, extra_int = amortization_schedule(balance, monthly_rate, monthly_payment, extra=extra)
        st.metric("Months Saved", len(base_df) - len(extra_df))
        st.metric("Interest Saved", f"${base_interest - extra_int:,.2f}")
        st.line_chart(extra_df.set_index("Month")["Balance"], height=250)

elif scenario == "Lower interest rate (refinance)":
    new_rate = st.number_input("New annual rate (%)", 0.0, 100.0, max(0.0, annual_rate - 1.0), 0.1, format="%.2f")
    if new_rate != annual_rate:
        new_mr = new_rate / 100 / 12
        low_df, low_int = amortization_schedule(balance, new_mr, monthly_payment)
        st.metric("Interest Saved", f"${base_interest - low_int:,.2f}")
        st.line_chart(low_df.set_index("Month")["Balance"], height=250)

elif scenario == "Increase monthly payment":
    new_payment = st.number_input("New monthly payment ($)", monthly_payment, 1_000_000.0, monthly_payment + 100.0, 10.0, format="%.2f")
    if new_payment > monthly_payment:
        inc_df, inc_int = amortization_schedule(balance, monthly_rate, new_payment)
        st.metric("Months Saved", len(base_df) - len(inc_df))
        st.metric("Interest Saved", f"${base_interest - inc_int:,.2f}")
        st.line_chart(inc_df.set_index("Month")["Balance"], height=250)

st.caption("Built with Streamlit · MIT‑licensed")

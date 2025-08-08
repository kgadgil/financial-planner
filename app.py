"""
Multi‑Debt Payoff & What‑If Calculator
=====================================
A **Streamlit** web‑app that lets you explore how different repayment strategies affect the lifetime cost of **multiple debts** (credit cards, loans, lines of credit).

Run locally with:

    pip install streamlit pandas numpy
    streamlit run debt_calculator_app.py

Built August 2025 · MIT‑licensed · No server needed.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

# ======================================================================
# Utility helpers
# ======================================================================

def amortization_schedule(
    balance: float,
    monthly_rate: float,
    monthly_payment: float,
    *,
    extra_payment: float = 0.0,
) -> tuple[pd.DataFrame, float]:
    """Return DataFrame schedule & total interest for one debt."""
    if balance <= 0:
        raise ValueError("Balance must be > 0")
    if monthly_rate < 0:
        raise ValueError("Rate cannot be negative")
    if monthly_payment + extra_payment <= balance * monthly_rate and monthly_rate > 0:
        raise ValueError("Payment too low to cover accruing interest – increase it.")

    month, total_interest, rows = 0, 0.0, []
    while balance > 0:
        month += 1
        interest = balance * monthly_rate
        principal = monthly_payment + extra_payment - interest
        principal = min(principal, balance)  # final month cap
        balance -= principal
        total_interest += interest
        rows.append(
            {
                "Month": month,
                "Payment": monthly_payment + extra_payment,
                "Principal": principal,
                "Interest": interest,
                "Balance": balance,
            }
        )
    df = pd.DataFrame(rows)
    return df, total_interest


def aggregate_balances(schedules: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Combine multiple schedules into an aggregate total-balance‑over‑time table."""
    if not schedules:
        return pd.DataFrame(columns=["Month", "Total Balance"])

    agg = (
        pd.concat({name: df.set_index("Month")["Balance"] for name, df in schedules.items()}, axis=1)
        .fillna(0.0)
    )
    agg["Total Balance"] = agg.sum(axis=1)
    agg.reset_index(inplace=True)
    return agg[["Month", "Total Balance"]]


# ======================================================================
# Streamlit layout & data model
# ======================================================================

st.set_page_config(
    page_title="Debt Payoff Calculator",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("💸 Multi‑Debt Payoff & What‑If Calculator")

# ------------------------- Sidebar: debt table -------------------------

st.sidebar.header("Debts")
DEFAULT_DATA = pd.DataFrame(
    {
        "Name": ["Card A"],
        "Balance": [10_000.0],
        "Annual Rate (%)": [18.99],
        "Monthly Payment": [300.0],
    }
)

if "debts" not in st.session_state:
    st.session_state.debts = DEFAULT_DATA.copy()

# Editable grid

debt_df: pd.DataFrame = st.sidebar.data_editor(
    st.session_state.debts,
    num_rows="dynamic",
    use_container_width=True,
    key="debt_editor",
)

st.session_state.debts = debt_df

if debt_df.empty:
    st.info("Add at least one debt in the sidebar to begin.")
    st.stop()

# ------------------------- Baseline computation ------------------------

schedules: dict[str, pd.DataFrame] = {}
error_msgs: list[str] = []

total_interest = 0.0
max_months = 0

for _, row in debt_df.iterrows():
    name = str(row["Name"]).strip() or "Unnamed Debt"
    bal = float(row["Balance"])
    rate_monthly = float(row["Annual Rate (%)"]) / 100 / 12
    payment = float(row["Monthly Payment"])

    try:
        df, interest = amortization_schedule(bal, rate_monthly, payment)
        schedules[name] = df
        total_interest += interest
        max_months = max(max_months, len(df))
    except ValueError as exc:
        error_msgs.append(f"{name}: {exc}")

if error_msgs:
    st.error("\n".join(error_msgs))
    st.stop()

initial_total_balance = debt_df["Balance"].sum()

a1, a2, a3 = st.columns(3)
a1.metric("⏱️ Payoff Time (longest)", f"{max_months} months", f"{max_months/12:.1f} years")
a2.metric("💰 Total Interest", f"${total_interest:,.2f}")
a3.metric("💵 Total Paid", f"${initial_total_balance + total_interest:,.2f}")

# ------------------------- Aggregate balance chart --------------------

agg_df = aggregate_balances(schedules)

st.subheader("Aggregate Balance Curve")
if not agg_df.empty:
    st.line_chart(agg_df.set_index("Month")["Total Balance"])

# ------------------------- Optional individual tables -----------------

if st.checkbox("Show individual amortization tables"):
    for name, df in schedules.items():
        st.markdown(f"#### {name}")
        st.dataframe(
            df.style.format(
                {
                    "Payment": "${:,.2f}",
                    "Principal": "${:,.2f}",
                    "Interest": "${:,.2f}",
                    "Balance": "${:,.2f}",
                }
            ),
            height=400,
        )

# ======================================================================
# What‑If Scenarios (per‑debt)
# ======================================================================

st.header("🔮 What‑If Scenarios (per debt)")

selected_debt_name = st.selectbox("Choose a debt to simulate", list(schedules.keys()))
base_df = schedules[selected_debt_name]
row = debt_df.loc[debt_df["Name"] == selected_debt_name].iloc[0]

balance = float(row["Balance"])
annual_rate = float(row["Annual Rate (%)"])
monthly_payment = float(row["Monthly Payment"])
monthly_rate = annual_rate / 100 / 12
base_interest = base_df["Interest"].sum()

scenario = st.selectbox(
    "Scenario",
    (
        "Pay off now",
        "Pay off now (n‑month horizon)",
        "Extra monthly payment",
        "Lower interest rate (refinance)",
        "Increase monthly payment",
    ),
)

if scenario == "Pay off now":
    st.markdown("### Scenario: Pay entire remaining balance today 🏁")
    st.metric("Interest Saved", f"${base_interest:,.2f}")
    st.info(
        "Paying off this debt today removes **all** future interest but requires a lump‑sum of the current balance."
    )

elif scenario == "Pay off now (n‑month horizon)":
    horizon = int(
        st.number_input(
            "Months to look ahead",
            min_value=1,
            value=6,
            step=1,
            format="%d",
        )
    )
    interest_future = base_df.loc[base_df["Month"] <= horizon, "Interest"].sum()
    st.metric(f"Interest Saved in {horizon} months", f"${interest_future:,.2f}")
    st.info(
        f"If you pay the balance today, you avoid **${interest_future:,.2f}** in interest that would accrue over the next {horizon} months under your current payment schedule."
    )

elif scenario == "Extra monthly payment":
    extra = st.number_input(
        "Extra payment each month ($)", min_value=0.0, value=50.0, step=10.0, format="%.2f"
    )
    if extra > 0:
        extra_df, extra_interest = amortization_schedule(
            balance, monthly_rate, monthly_payment, extra_payment=extra
        )
        st.metric("Months Saved", len(base_df) - len(extra_df))
        st.metric("Interest Saved", f"${base_interest - extra_interest:,.2f}")
        st.line_chart(extra_df.set_index("Month")["Balance"], height=250)

elif scenario == "Lower interest rate (refinance)":
    new_rate = st.number_input(
        "New annual interest rate (%)",
        min_value=0.0,
        value=max(0.0, annual_rate - 1.0),
        step=0.1,
        format="%.2f",
    )
    if new_rate != annual_rate:
        new_monthly_rate = new_rate / 100 / 12
        lower_df, lower_interest = amortization_schedule(
            balance, new_monthly_rate, monthly_payment
        )
        st.metric("Interest Saved", f"${base_interest - lower_interest:,.2f}")
        st.line_chart(lower_df.set_index("Month")["Balance"], height=250)

elif scenario == "Increase monthly payment":
    new_payment = st.number_input(
        "New monthly payment ($)",
        min_value=monthly_payment,
        value=monthly_payment + 100.0,
        step=10.0,
        format="%.2f",
    )
    if new_payment > monthly_payment:
        inc_df, inc_interest = amortization_schedule(balance, monthly_rate, new_payment)
        st.metric("Months Saved", len(base_df) - len(inc_df))
        st.metric("Interest Saved", f"${base_interest - inc_interest:,.2f}")
        st.line_chart(inc_df.set_index("Month")["Balance"], height=250)

st.caption("Built with Streamlit · © 2025 Personal Finance Tools")

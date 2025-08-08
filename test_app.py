"""Enhanced unit & property tests for the Debt Payoff Calculator.

Run with:

    pip install pytest hypothesis pandas numpy
    pytest -q
"""

from __future__ import annotations

import math
import importlib
import pytest
from hypothesis import given, strategies as st, assume

# ---------------------------------------------------------------------
# Import target module (app.py must be on PYTHONPATH when pytest runs)
# ---------------------------------------------------------------------

app = importlib.import_module("app")

amortization_schedule = app.amortization_schedule

# ---------------------------------------------------------------------
# Deterministic unit tests
# ---------------------------------------------------------------------

def test_negative_or_zero_balance_raises():
    with pytest.raises(ValueError):
        amortization_schedule(0, 0.05 / 12, 100)
    with pytest.raises(ValueError):
        amortization_schedule(-500, 0.05 / 12, 100)


def test_payment_too_low_raises():
    balance = 1_000.0
    rate = 0.24 / 12  # 24% APR
    payment = balance * rate * 0.9  # 10 % below monthly interest
    with pytest.raises(ValueError):
        amortization_schedule(balance, rate, payment)


def test_payment_equals_interest_raises():
    bal = 2_000.0
    rate = 0.18 / 12
    pay = bal * rate  # exact interest due
    with pytest.raises(ValueError):
        amortization_schedule(bal, rate, pay)


def test_negative_extra_payment_raises():
    with pytest.raises(ValueError):
        amortization_schedule(1_000, 0.1 / 12, 200, extra=-50)


def test_accounting_conservation():
    bal = 5_000
    rate = 0.1 / 12
    pay = 150
    df, total_int = amortization_schedule(bal, rate, pay)

    # Final balance ≈ 0
    assert pytest.approx(df["Balance"].iloc[-1], abs=1e-2) == 0

    # Sum of principal equals original balance
    assert pytest.approx(df["Principal"].sum(), rel=1e-4) == bal

    # Interest column sums to returned total
    assert pytest.approx(df["Interest"].sum(), rel=1e-4) == total_int


def test_extra_payment_improves_outcome():
    bal, rate, pay = 8_000, 0.08 / 12, 250
    base_df, base_int = amortization_schedule(bal, rate, pay)
    extra_df, extra_int = amortization_schedule(bal, rate, pay, extra=50)
    assert len(extra_df) < len(base_df)  # faster payoff
    assert extra_int < base_int  # lower interest

# ---------------------------------------------------------------------
# Parameterised edge‑case coverage
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "balance, apr_pct, payment",
    [
        (1_000, 0.0, 100),      # zero interest loan
        (1_000, 99.0, 2_000),   # huge APR but giant payment
        (750, 4.0, 1_000),      # payment larger than balance (single-shot)
    ],
)
def test_edge_cases_amortise(balance: float, apr_pct: float, payment: float):
    df, _ = amortization_schedule(balance, apr_pct / 100 / 12, payment)
    assert pytest.approx(df["Balance"].iloc[-1], abs=1e-2) == 0

# ---------------------------------------------------------------------
# Property‑based tests with Hypothesis for invariant checking
# ---------------------------------------------------------------------

@given(
    balance=st.floats(min_value=500, max_value=50_000),
    apr=st.floats(min_value=0.0, max_value=0.35),
    payment=st.floats(min_value=50, max_value=5_000),
)
def test_balance_never_negative(balance: float, apr: float, payment: float):
    monthly_rate = apr / 12
    assume(monthly_rate == 0 or payment > balance * monthly_rate)
    df, _ = amortization_schedule(balance, monthly_rate, payment)
    assert (df["Balance"] >= -1e-2).all()


@given(
    balance=st.floats(min_value=1_000, max_value=30_000),
    apr=st.floats(min_value=0.01, max_value=0.25),
    payment=st.floats(min_value=50, max_value=2_000),
    extra=st.floats(min_value=0, max_value=500),
)
def test_interest_non_negative_and_monotonic_balance(balance: float, apr: float, payment: float, extra: float):
    monthly_rate = apr / 12
    assume(payment + extra > balance * monthly_rate)
    df, _ = amortization_schedule(balance, monthly_rate, payment, extra=extra)

    # Interest non‑negative per row
    assert (df["Interest"] >= 0).all()

    # Balance strictly decreases (monotonic decrease)
    assert df["Balance"].is_monotonic_decreasing

"""Unit tests for Debt Payoff Calculator utility logic.

Run with:

    pip install pytest pandas numpy
    pytest -q test_debt_calculator.py
"""

import math
import importlib
import types

# Import the amortization_schedule function from the Streamlit app.
# The app script is assumed to be named ``app.py`` and located in the
# same folder when tests run.
app = importlib.import_module("app")  # noqa: E402

amortization_schedule = app.amortization_schedule


def test_negative_or_zero_balance_raises():
    """Balance must be positive."""
    import pytest

    with pytest.raises(ValueError):
        amortization_schedule(0, 0.05 / 12, 100)
    with pytest.raises(ValueError):
        amortization_schedule(-500, 0.05 / 12, 100)


def test_payment_too_low_raises():
    """Monthly payment that doesn't cover interest should raise."""
    import pytest

    balance = 1_000.0
    rate = 0.24 / 12  # 24% APR
    payment = balance * rate * 0.9  # 10 % below interest due
    with pytest.raises(ValueError):
        amortization_schedule(balance, rate, payment)


def test_interest_and_balance_conservation():
    """Total interest and balance math should balance out."""
    bal = 5_000
    rate = 0.1 / 12  # 10% APR
    pay = 150
    df, total_int = amortization_schedule(bal, rate, pay)

    # Final balance should be zero (within rounding tolerance)
    assert math.isclose(df["Balance"].iloc[-1], 0.0, abs_tol=1e-2)

    # Sum of principal should equal original balance
    principal_sum = df["Principal"].sum()
    assert math.isclose(principal_sum, bal, rel_tol=1e-4)

    # Sum of interest column should equal total_int returned
    assert math.isclose(df["Interest"].sum(), total_int, rel_tol=1e-4)


def test_extra_payment_shortens_schedule():
    """Adding an extra payment should shorten payoff horizon and lower interest."""
    bal = 8_000
    rate = 0.08 / 12  # 8% APR
    pay = 250

    base_df, base_int = amortization_schedule(bal, rate, pay)
    extra_df, extra_int = amortization_schedule(bal, rate, pay, extra=50)

    assert len(extra_df) < len(base_df)  # fewer months
    assert extra_int < base_int  # less total interest

# Debt Payoff Calculator

A web‑based financial tool built with **Streamlit** that lets you compare how different payment strategies affect the payoff timeline and total interest for multiple debts.

## Features

* Enter any number of credit‑cards, loans, or other debts
* Compare minimum‑payment plan vs. your chosen payments
* What‑if analysis: add extra payments to see faster payoff and lower interest
* Import debts from CSV and edit inline
* Runs entirely client‑side (no data leaves your browser)

## Quick Start

1. **Install dependencies**

   ```bash
   pip install streamlit pandas numpy
   ```
2. **Launch the app**

   ```bash
   streamlit run app.py
   ```

   Your default browser will open at `http://localhost:8501`.

## Running Tests

```bash
pip install pytest hypothesis pandas numpy
pytest -q
```

## Project Structure

```
.
├── app.py           # Streamlit application
├── test_app.py      # Unit & property tests
└── README.md
```


## Tasks

- [x] display chart for amortization schedule per debt
- [x] remove the pay in n horizon scenario
- [x] fix the input table jitter
- [x] add csv import option
- [x] add tests
- [ ] add csv, pdf export option
- [ ] add LLM scenarios - what if i pay $500 for the first 3 months towards a credit card and 400 for the rest of the time, how will that affect my debt?
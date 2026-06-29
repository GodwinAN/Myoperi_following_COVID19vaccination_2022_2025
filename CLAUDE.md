# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A pharmacoepidemiology data analysis project examining myopericarditis rates following COVID-19 vaccination (2022–2025), ages 12–24. The Python notebooks implement a wrangling and summary pipeline on **synthetic** data that mirrors real SAS datasets held on a remote study server. The synthetic data is reproducible (seed = 42).

## Running the Pipeline

**Step 1 — Regenerate synthetic input data (only needed if CSVs are missing or stale):**
```
cd dataimages
python generate_datasets.py
```

**Step 2 — Execute the wrangling + summary notebook:**
```
jupyter nbconvert --to notebook --execute --inplace data_wrangling_summary.ipynb
```

**Step 3 — (Optional) Execute the standalone visualisation notebook:**
```
jupyter nbconvert --to notebook --execute --inplace data_visualization.ipynb
```

**Regenerate PDFs** (requires Microsoft Edge on Windows):
```
jupyter nbconvert --to html --no-prompt data_wrangling_summary.ipynb
jupyter nbconvert --to html --no-prompt data_visualization.ipynb
python <scratchpad>/html_to_pdf.py   # Edge headless, A3 landscape, no-cutoff CSS
```

There are no tests or linting steps.

## Architecture

Two notebooks, two roles:

- **`data_wrangling_summary.ipynb`** — the full pipeline: reads 5 raw CSVs → produces `exposure_enriched.csv`, `myo_events.csv`, `analytic_dataset.csv`, `person_season.csv`, 8 `summary_*.csv` files, and 8 PNG plots. All intermediate state lives in notebook memory; cells must run in order.

- **`data_visualization.ipynb`** — standalone; reads only the 8 `summary_*.csv` files from `dataimages/` and reproduces all 8 plots. Can be run independently of the wrangling notebook.

The `dataimages/` directory is both the input source (raw CSVs, schema images) and the output sink (derived CSVs, `plots/`).

### Pipeline stages in `data_wrangling_summary.ipynb`

| Part | Input → Output | Key filter |
|------|---------------|------------|
| 1 (Steps 1–5) | `event.csv` + lookups → `exposure_enriched.csv` (903 rows) | VAX codes, enrollment window, admin concept 724802, close-dose dedup |
| 2 | `event.csv` → `myo_events.csv` (58 rows) | AESI myo1, clinical settings only, 365-day washout |
| 3 | exposure + outcome → merged | myo_date **strictly after** first_vax_date (not same-day) |
| 4 | merged → `analytic_dataset.csv` (501 rows) | after_auth=1, age 12–24, no Unknown brand |
| 5 | analytic → `person_season.csv` (387 rows) | Collapse to first dose per person×season; 28-day risk window |
| 6a | person_season → 8 `summary_*.csv` | Exact Poisson 95% CI via chi-squared method |
| 6b | summaries → `dataimages/plots/*.png` | 8 plots, matplotlib Agg backend in wrangling nb |

## Key Conventions

**Notebook editing** — the `.ipynb` files are too large for the `Read` tool (>33k tokens). Always manipulate them via Python `json.load / json.dump` scripts written to the scratchpad directory. Use `ensure_ascii=True` when saving to prevent mojibake.

**Date format** — all raw dates are `DDMMMYYYY` strings (SAS format, e.g. `06JUL1997`). Parse with `pd.to_datetime(col, format='%d%b%Y', errors='coerce')`. Missing SAS dates (`.`) become `NaT`.

**Seasons** — flu-year (Jul–Jun). A date in Aug 2022 → season `22_23`. The three seasons in scope are `22_23`, `23_24`, `24_25`.

**Vaccine codes** — `cvp` (Pfizer), `cvm` (Moderna), `cvn` (Novavax), `cvj` (Janssen), `cvu` (Unspecified).

**Admin concept filter** — concept_id `724802` co-occurring with a vaccination on the same person-date is an administrative artefact and must be dropped (Step 2).

**Incidence rate formula** — `(num_outcomes / person_days) × 100,000`. Exact Poisson 95% CI: lower = `chi2(0.025, 2d) / (2T) × 100,000`; upper = `chi2(0.975, 2(d+1)) / (2T) × 100,000`.

**Matplotlib backend** — `data_wrangling_summary.ipynb` uses `matplotlib.use('Agg')` (headless, saves to file only). `data_visualization.ipynb` uses `%matplotlib inline` + `plt.show()` for inline display.

**PDF generation** — uses Microsoft Edge headless (`--headless=new --print-to-pdf`) on A3 landscape with injected CSS (`overflow:visible`, `pre-wrap`, `font-size:8pt` on tables) to prevent content cutoff. No LaTeX required.

================================================================================
  MYOPERICARDITIS FOLLOWING COVID-19 VACCINATION
  Pharmacoepidemiology Study — Data Wrangling and Summary Pipeline
================================================================================

OVERVIEW
--------
This project investigates the association between COVID-19 vaccination and
myopericarditis (myocarditis AESI code: myo1) in individuals aged 12-24 years.
It uses a new-user cohort design. The primary analysis platform is SAS on a
remote server; the Python notebook here implements the full data wrangling
pipeline on synthetic reference datasets that mirror the SAS dataset schemas.

STUDY PARAMETERS
----------------
  Study window          : 2022-01-01 to 2026-01-01
  Seasons (COVID19-year)    : 22_23 (Jul 2022 - Jun 2023)
                          23_24 (Jul 2023 - Jun 2024)
                          24_25 (Jul 2024 - Jun 2025)
  Eligible age range    : 12 to 24 years
  Outcome               : Myocarditis (AESI code: myo1)
  Risk window           : 0 to 28 days post first vaccination dose
  Maximum follow-up     : 28 days
  Clean period          : 365 days prior (no prior myocarditis)
  Enrollment window     : 365-day continuous enrollment required

VACCINE BRAND CODES
-------------------
  cvp  = Pfizer
  cvm  = Moderna
  cvn  = Novavax
  cvj  = Janssen (J&J)
  cvu  = Unspecified


================================================================================
  FILE STRUCTURE
================================================================================

  data_wrangling_summary.ipynb   Main analysis notebook (see pipeline below)

  dataimages/
    patient.csv                  Synthetic patient demographics (1,000 rows)
    event.csv                    Synthetic visit-level events (1,000 rows)
    enrollment.csv               Synthetic enrollment records (1,000 rows)
    zip5_mapping.csv             ZIP-5 to CBSA and urban/rural indicator
    zip3_mapping.csv             ZIP-3 to state, OMB region, census region

    exposure_enriched.csv        Output: cleaned vaccination exposure dataset
                                 (903 rows x 38 columns)
    myo_events.csv               Output: cleaned myocarditis outcome events
                                 (58 rows x 19 columns)
    analytic_dataset.csv         Output: final analytic cohort after all
                                 inclusion restrictions (501 rows x 42 columns)

    summary_overall.csv          Output: overall aggregation summary
    summary_season.csv           Output: summary by season
    summary_brand.csv            Output: summary by vaccine brand
    summary_age.csv              Output: summary by age group
    summary_season_brand.csv     Output: summary by season and brand
    summary_season_age.csv       Output: summary by season and age group
    summary_brand_age.csv        Output: summary by brand and age group
    summary_season_brand_age.csv Output: summary by season, brand, and age

    plots/
      plot_overall.png           Rate bar + summary statistics table
      plot_season.png            Rate by season
      plot_brand.png             Rate by vaccine brand
      plot_age.png               Rate by age group
      plot_season_brand.png      Rate by season and brand (grouped bars)
      plot_season_age.png        Rate by season and age group (grouped bars)
      plot_brand_age.png         Rate by brand and age group (grouped bars)
      plot_season_brand_age.png  Rate by season, brand, and age (3-panel facet)

  dataimages/*.docx              Word documents with data creation instructions
  dataimages/*.jpeg              SAS System Viewer screenshots of dataset schemas


================================================================================
  HOW TO RUN
================================================================================

REQUIREMENTS
  Python 3.8+
  pip install pandas scipy matplotlib jupyter

STEP 1 — Generate synthetic input datasets
  cd dataimages
  python generate_datasets.py

  This writes patient.csv, event.csv, enrollment.csv, zip5_mapping.csv, and
  zip3_mapping.csv to dataimages/. Output is reproducible (random.seed = 42).

STEP 2 — Run the wrangling notebook
  jupyter notebook data_wrangling_summary.ipynb

  Then run all cells (Kernel > Restart & Run All).

  Alternatively, execute without opening Jupyter:
    jupyter nbconvert --to notebook --execute --inplace data_wrangling_summary.ipynb

  All intermediate and final CSV outputs, plus all 8 PNG plots, are written
  automatically during execution.


================================================================================
  NOTEBOOK PIPELINE — data_wrangling_summary.ipynb
================================================================================

PART 1 — Build Exposure Dataset (exposure_enriched.csv)
--------------------------------------------------------
The notebook transforms event.csv into an enriched vaccination exposure dataset
through the following steps:

  Step 1 — Subset and enrich vaccination events
    - Filter event.csv to vaccination event codes (cvp, cvm, cvn, cvj, cvu)
    - Merge with patient.csv (sex, birth_date, death_date, zip)
    - Enrich with ZIP geography:
        zip5_mapping  -> CBSA code, urban/rural indicator
        zip3_mapping  -> state abbreviation, census region, OMB region
    - Merge with enrollment.csv (enrl_start_date, enrl_end_date)
    - Retain only records where the vaccination date falls within the
      individual's continuous enrollment window

  Step 2 — Remove co-occurring administrative concept
    - Flag and drop records where concept_id = 724802 co-occurs with a
      vaccination event on the same date (administrative artefact)

  Step 3 — Resolve close-dose pairs (gap <= 3 days)
    - For same-brand duplicates within 3 days, retain only the earlier record
    - For cross-brand pairs within 3 days, retain only the earlier record
      (represents a single vaccination administration event)

  Step 4 — Derive analytical variables
    - age_at_exposure  : age in years at the vaccination date
    - season           : COVID19-year season (22_23, 23_24, 24_25)
    - in_study_window  : 1 if date falls within 2022-01-01 to 2026-01-01
    - brand            : vaccine brand code prefix (cvp, cvm, cvn, cvj, cvu)
    - brand_label      : human-readable brand name
    - vac_brand        : brand x season label (e.g., Pfizer_22_23)

  Step 5 — After-authorization flag (after_auth)
    - Flag records where the vaccine brand was authorized for the individual's
      age group at the time of vaccination, based on brand-specific
      authorization dates and minimum age thresholds

  Output: dataimages/exposure_enriched.csv (903 rows)

PART 2 — Outcome Data Cleaning (myo_events.csv)
------------------------------------------------
  - Load event.csv and subset to myocarditis records (AESI code: myo1)
  - Restrict to clinical settings (FB, PX, OFFICE) and clinical facilities
    (HOSP, ED, OUTPAT)
  - Apply a 365-day washout: for each individual, retain only myocarditis
    events that occur at least 365 days after any prior myocarditis event
    (incident events only)
  - Assign season label

  Output: dataimages/myo_events.csv (58 rows)

PART 3 — Merge Exposure and Outcome
------------------------------------
  Standard epidemiological linkage (not same-day merge):
  - For each person x season, find the first vaccination date (first_vax_date)
  - Link any myocarditis event that occurred AFTER first_vax_date in the same
    season (myo_date > first_vax_date)
  - Create flag: myo_after_first_vax = 1 if such a myocarditis event exists

PART 4 — Age Categorisation and Inclusion Restrictions
-------------------------------------------------------
  - Create age_cat variable:
      12_17  : age >= 12 and age < 18
      18_24  : age >= 18 and age < 25
      other  : outside eligible range

  - Apply inclusion criteria (row counts shown for synthetic data):
      1. after_auth = 1              (903 -> 791 rows)
      2. in_study_window = 1         (791 -> 791 rows, no change)
      3. age_cat in {12_17, 18_24}   (791 -> 680 rows)
      4. Remove Unknown_brand        (680 -> 501 rows)

  Output: dataimages/analytic_dataset.csv (501 rows)

PART 5 — Risk Windows and Follow-up Time
-----------------------------------------
  Collapse to one record per person x season (first vaccination dose only).

  Risk window definition:
    risk_start_dt         = first_vax_date + 0 days
    risk_end_uncensored   = first_vax_date + 28 days

  Censoring (risk_end_dt = minimum of all censor dates):
    disenrollment         = enrl_end_date
    death                 = death_date
    study_end             = end of COVID19 season (Jun 30 of that season)
    observation_end       = risk_end_uncensored (first_vax_date + 28 days)
    next_dose             = next vaccination date - 1 day (earliest dose
                            strictly after first_vax_date, across all seasons)

  Derived variables:
    censor_reason         : which of the above determined risk_end_dt
    risk_length           : (risk_end_dt - risk_start_dt).days + 1
    obs_risk_length       : same as risk_length (observed person-days at risk)
    outcome_in_risk       : 1 if myo_date falls within [risk_start_dt,
                            risk_end_dt], else 0

  Result: 387 person-season records

PART 6 — Summary Tables
------------------------
  Eight aggregation levels, each producing one CSV:

    overall              : single row, all persons pooled
    season               : one row per season
    brand                : one row per vaccine brand
    age                  : one row per age group
    season_brand         : one row per season x brand combination
    season_age           : one row per season x age group combination
    brand_age            : one row per brand x age group combination
    season_brand_age     : one row per season x brand x age group combination

  Variables in each summary file:
    num_vax              : total vaccination records
    num_unique_person    : number of distinct individuals
    num_outcomes_risk    : myocarditis events in the risk window
    pd_risk              : total person-days at risk
    rate_risk            : incidence rate per 100,000 person-days
                           = (num_outcomes_risk / pd_risk) x 100,000
    lower_ci             : exact Poisson 95% CI lower bound
                           = chi2(0.025, 2d) / (2T) x 100,000
    upper_ci             : exact Poisson 95% CI upper bound
                           = chi2(0.975, 2(d+1)) / (2T) x 100,000
    rate_se              : rate standard error
                           = sqrt(d) / T x 100,000

  Where d = num_outcomes_risk and T = pd_risk (person-days).

PART 6b — Visualisations
--------------------------
  One PNG plot per aggregation level, saved to dataimages/plots/.

  Plot types:
    overall              : bar chart + summary statistics table side-by-side
    season, brand, age   : single bar chart; n=unique persons in tick labels
    season_brand         : grouped bar chart; 4 brand bars per season
    season_age           : grouped bar chart; 2 age bars per season
    brand_age            : grouped bar chart; 2 age bars per brand
    season_brand_age     : 3-panel facet (one panel per season); 4 brand bars
                           per panel, split by age group colour

  All plots include:
    - 95% CI error bars
    - Grey bars where no events were observed in that cell
    - n = unique persons annotated per bar
    - Rate value printed above each bar (1-D charts)


================================================================================
  KEY CONVENTIONS
================================================================================

  Dates          : SAS format DDMMMYYYY (e.g., 06JUL1997). In Python these are
                   parsed with pd.to_datetime(col, errors='coerce').
  Missing dates  : Represented as '.' in SAS; become NaT in pandas.
  Settings       : RX = retail pharmacy (vaccines)
                   FB / PX / OFFICE = clinical (myocarditis)
  Facilities     : PHARM (vaccines); HOSP / ED / OUTPAT (myocarditis)
  Seasons        : COVID19-year (Jul - Jun). A date in Aug 2022 belongs to 22_23.
  Random seed    : 42 (reproducible synthetic data)


================================================================================
  NOTES FOR REAL-DATA DEPLOYMENT
================================================================================

  This notebook was developed and validated against synthetic data. When
  applied to real SAS datasets from the study server (beast):

  1. Replace the five input CSVs in dataimages/ with the real data exports.
  2. Confirm that all date columns are exported as DDMMMYYYY strings before
     reading into Python, or adjust the pd.to_datetime() format string.
  3. The admin concept ID filter (Step 2, concept_id = 724802) should be
     verified against the current cohort_specs.sas7bdat before applying.
  4. Authorization dates and age thresholds in Step 5 should be cross-checked
     against the latest EUA/approval records for each vaccine brand.
  5. Summary rate calculations use exact Poisson CIs (chi-squared method),
     which is the standard for rare adverse event surveillance.

================================================================================

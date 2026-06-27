"""
generate_datasets.py

Creates five synthetic CSV datasets for the myopericarditis-following-COVID19-vaccination study:
  patient.csv, event.csv, enrollment.csv, zip5_mapping.csv, zip3_mapping.csv

Design constraints:
  - 1 000 records in every output file
  - person_ids are consistent across patient / event / enrollment
  - ZIP codes in patient file are covered by both ZIP mapping files
  - Longitudinal: ~12% of patients develop myocarditis (myo) within 28 days of their last vaccination
  - ~7% of patients have two consecutive vaccination doses within 1–3 days of each other (edge case)
  - All other multi-dose gaps are 28–180 days
"""

import os
import random
from datetime import datetime, timedelta

import pandas as pd

# ── reproducibility ───────────────────────────────────────────────────────────
random.seed(42)

# ── paths & study window ──────────────────────────────────────────────────────
OUT_DIR     = os.path.dirname(os.path.abspath(__file__))
STUDY_START = datetime(2022, 1, 1)
STUDY_END   = datetime(2026, 1, 1)
PROCESS_DATE = datetime(2025, 12, 1)

# ── helpers ───────────────────────────────────────────────────────────────────
def rdate(start: datetime, end: datetime) -> datetime:
    """Return a random date in [start, end]."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(0, delta)))

def fmt(dt) -> str:
    """SAS-style date string DDMMMYYYY, or '.' for missing."""
    return dt.strftime('%d%b%Y').upper() if dt else '.'

# ── reference tables ──────────────────────────────────────────────────────────
# OMOP concept IDs for COVID-19 vaccine products
CONCEPT_MAP = {
    'cvp22': (37003518, 37003518),   # Pfizer BNT162b2
    'cvp23': (37003518, 37003518),
    'cvp24': (37003518, 37003518),
    'cvm22': (37003436, 37003436),   # Moderna mRNA-1273
    'cvm23': (37003436, 37003436),
    'cvm24': (37003436, 37003436),
    'cvj22': (739906,   739906),     # J&J Ad26.COV2.S
    'cvn22': (702866,   702866),     # Novavax NVX-CoV2373
    'cvn23': (702866,   702866),
    'cvn24': (702866,   702866),
    'cvu':   (40213154, 40213154),   # Unspecified COVID-19 vaccine
    'myo':   (4331309,  4331309),    # Myocarditis
}

BRANDS   = ['cvp', 'cvm', 'cvn', 'cvj', 'cvu']
SETTINGS  = ['RX', 'FB', 'PX', 'OFFICE', 'NURSE', 'PH']
FACILITIES = ['PHARM', 'CLINIC', 'HOSP', 'OUTPAT', 'ED']

STATES = [
    ('01', 'Alabama',        'AL', 'Region IV',  'South:East South Central'),
    ('04', 'Arizona',        'AZ', 'Region IX',  'West:Mountain'),
    ('06', 'California',     'CA', 'Region IX',  'West:Pacific'),
    ('12', 'Florida',        'FL', 'Region IV',  'South:South Atlantic'),
    ('13', 'Georgia',        'GA', 'Region IV',  'South:South Atlantic'),
    ('17', 'Illinois',       'IL', 'Region V',   'Midwest:East North Central'),
    ('22', 'Louisiana',      'LA', 'Region VI',  'South:West South Central'),
    ('26', 'Michigan',       'MI', 'Region V',   'Midwest:East North Central'),
    ('34', 'New Jersey',     'NJ', 'Region II',  'Northeast:Middle Atlantic'),
    ('36', 'New York',       'NY', 'Region II',  'Northeast:Middle Atlantic'),
    ('37', 'North Carolina', 'NC', 'Region IV',  'South:South Atlantic'),
    ('39', 'Ohio',           'OH', 'Region V',   'Midwest:East North Central'),
    ('47', 'Tennessee',      'TN', 'Region IV',  'South:East South Central'),
    ('48', 'Texas',          'TX', 'Region VI',  'South:West South Central'),
    ('51', 'Virginia',       'VA', 'Region III', 'South:South Atlantic'),
    ('53', 'Washington',     'WA', 'Region X',   'West:Pacific'),
]

CBSA_URBAN = [
    (33660, 1), (33860, 1), (19300, 0), (13820, 0), (22840, 1),
    (42460, 1), (45180, 1), (10760, 0), (46220, 1), (21640, 0),
    (12120, 0), (35300, 1), (26900, 1), (41700, 1), (38060, 1),
]

# ── (1) PATIENT FILE ─────────────────────────────────────────────────────────
N = 1000
person_ids = sorted(random.sample(range(1_000_000, 15_000_000), N))

# Exactly N unique 5-digit ZIPs (one per patient for clean mapping)
zip_pool = [str(z).zfill(5) for z in random.sample(range(10001, 99998), N)]

patients = []
for i, pid in enumerate(person_ids):
    # Ages 12–24 during the study window → born ~1997–2010
    bdate = rdate(datetime(1997, 1, 1), datetime(2010, 12, 31))
    ddate = rdate(datetime(2023, 1, 1), STUDY_END) if random.random() < 0.03 else None
    patients.append({
        'person_id':  pid,
        'sex':        random.choice(['M', 'F']),
        'birth_date': fmt(bdate),
        'death_date': fmt(ddate) if ddate else '.',
        'zip':        zip_pool[i],
    })

patient_df = pd.DataFrame(patients)

# ── (2) ENROLLMENT FILE ──────────────────────────────────────────────────────
enroll_dict: dict[int, tuple[datetime, datetime]] = {}
enroll_rows = []
for pid in person_ids:
    s = rdate(STUDY_START, datetime(2024, 6, 1))
    e = rdate(s + timedelta(days=180), STUDY_END)
    enroll_dict[pid] = (s, e)
    enroll_rows.append({
        'person_id':       pid,
        'enrl_start_date': fmt(s),
        'enrl_end_date':   fmt(e),
    })

enrollment_df = pd.DataFrame(enroll_rows)

# ── (3) ZIP MAPPING FILES ─────────────────────────────────────────────────────

# zip5_mapping: exactly 1 000 rows, one per patient ZIP
zip5_rows = []
for z in zip_pool:
    cbsa, urban = random.choice(CBSA_URBAN)
    zip5_rows.append({'zip5': z, 'CBSA': cbsa, 'urban': urban})
zip5_df = pd.DataFrame(zip5_rows)

# zip3_mapping: derive zip3 prefixes from patient ZIPs, pad to 1 000
zip3_dict: dict[str, dict] = {}
for z in zip_pool:
    z3 = z[:3]
    if z3 not in zip3_dict:
        st = random.choice(STATES)
        zip3_dict[z3] = {
            'zip3':               z3,
            'state_fips':         st[0],
            'state_name':         st[1],
            'state_abbv':         st[2],
            'omb_region_label':   st[3],
            'census_region_label': st[4],
        }

extras = [str(i).zfill(3) for i in range(0, 2000) if str(i).zfill(3) not in zip3_dict]
random.shuffle(extras)
for z3 in extras:
    if len(zip3_dict) >= 1000:
        break
    st = random.choice(STATES)
    zip3_dict[z3] = {
        'zip3':               z3,
        'state_fips':         st[0],
        'state_name':         st[1],
        'state_abbv':         st[2],
        'omb_region_label':   st[3],
        'census_region_label': st[4],
    }

zip3_df = pd.DataFrame(list(zip3_dict.values())).head(1000)

# ── (4) EVENT FILE ───────────────────────────────────────────────────────────

def vax_code(brand: str, date: datetime) -> str:
    """Resolve vaccine event code from brand prefix and administration date."""
    yr = date.year % 100   # 22, 23, 24, 25…
    if brand == 'cvu' or yr > 24:
        return 'cvu'
    if brand == 'cvj' and yr > 22:          # J&J discontinued after 2022
        brand = random.choice(['cvp', 'cvm', 'cvn'])
    return f"{brand}{yr}"

vid_counter = [30_000_000]   # mutable so inner function can increment

def make_row(pid: int, ev: str, dt: datetime, ev_num: int) -> dict:
    vid_counter[0] += 1
    vid = vid_counter[0]
    cid, scid = CONCEPT_MAP.get(ev, (0, 0))
    end_dt   = dt + timedelta(days=random.randint(0, 1))
    is_vax   = (ev != 'myo')
    setting  = 'RX'    if is_vax else random.choice(['FB', 'PX', 'OFFICE'])
    facility = 'PHARM' if is_vax else random.choice(['HOSP', 'ED', 'OUTPAT'])
    return {
        'person_id':                   pid,
        'visit_det_all_id':            vid,
        'event':                       ev,
        'concept_id':                  cid,
        'source_concept_id':           scid,
        'date':                        fmt(dt),
        'end_date':                    fmt(end_dt),
        'event_num':                   ev_num,
        'dqc_posit_ion':               random.randint(1, 20),
        'rv_visit_details':            vid - random.randint(0, 5),
        'visit_det_all_concept_pt_id': cid,
        'visit_det_date':              fmt(dt),
        'visit_det_end_date':          fmt(end_dt),
        'visit_det_aim':               random.randint(1, 3),
        'setting':                     setting,
        'facility':                    facility,
        'process_date':                fmt(PROCESS_DATE),
    }

# Designate which patients get myo (≈12%) and which get a close-dose pair (≈7%)
pids_shuffled = person_ids[:]
random.shuffle(pids_shuffled)
myo_pids   = set(pids_shuffled[:120])
close_pids = set(pids_shuffled[120:190])

events = []
for pid in person_ids:
    enr_start, enr_end = enroll_dict[pid]
    brand   = random.choice(BRANDS)
    n_doses = random.choices([1, 2, 3], weights=[0.30, 0.50, 0.20])[0]

    # First dose: at least 60 days before enrollment ends
    first_dose = rdate(enr_start, enr_end - timedelta(days=60))
    doses = [first_dose]

    for d in range(1, n_doses):
        if pid in close_pids and d == 1:
            gap = random.randint(1, 3)         # intentional edge case: ≤3 days
        else:
            gap = random.randint(28, 180)      # normal inter-dose interval
        nd = doses[-1] + timedelta(days=gap)
        if nd < enr_end - timedelta(days=28):
            doses.append(nd)

    for i, dd in enumerate(doses):
        events.append(make_row(pid, vax_code(brand, dd), dd, i + 1))

    # Myocarditis outcome within 1–28 days of the last dose
    if pid in myo_pids and doses:
        myo_dt = doses[-1] + timedelta(days=random.randint(1, 28))
        if myo_dt < enr_end:
            events.append(make_row(pid, 'myo', myo_dt, len(doses) + 1))

event_df = pd.DataFrame(events)

# Trim or pad to exactly 1 000 rows
if len(event_df) > 1000:
    event_df = event_df.head(1000)
elif len(event_df) < 1000:
    shortage = 1000 - len(event_df)
    filler   = event_df.sample(shortage, replace=True).copy()
    new_vids = list(range(vid_counter[0] + 1, vid_counter[0] + 1 + shortage))
    filler['visit_det_all_id'] = new_vids
    event_df = pd.concat([event_df, filler], ignore_index=True)

# ── (5) SAVE ─────────────────────────────────────────────────────────────────
files = {
    'patient.csv':      patient_df,
    'event.csv':        event_df,
    'enrollment.csv':   enrollment_df,
    'zip5_mapping.csv': zip5_df,
    'zip3_mapping.csv': zip3_df,
}

for fname, df in files.items():
    path = os.path.join(OUT_DIR, fname)
    df.to_csv(path, index=False)
    print(f"  {fname:<22} {len(df):>5} rows  ->  {path}")

# ── (6) QUICK VALIDATION ─────────────────────────────────────────────────────
print("\n-- validation --")

# person_id consistency
ev_pids  = set(event_df['person_id'])
enr_pids = set(enrollment_df['person_id'])
pat_pids = set(patient_df['person_id'])
print(f"  person_ids in event not in patient   : {len(ev_pids  - pat_pids)}")
print(f"  person_ids in enrollment not in patient: {len(enr_pids - pat_pids)}")

# myo events
myo_count = (event_df['event'] == 'myo').sum()
print(f"  myo events in event file             : {myo_count}")

# close-dose patients (gap ≤ 3 days)
vax_events = event_df[event_df['event'] != 'myo'].copy()
vax_events['date_dt'] = pd.to_datetime(vax_events['date'], format='%d%b%Y')
vax_events = vax_events.sort_values(['person_id', 'date_dt'])
vax_events['prev_date'] = vax_events.groupby('person_id')['date_dt'].shift(1)
vax_events['gap'] = (vax_events['date_dt'] - vax_events['prev_date']).dt.days
close_count = (vax_events['gap'].dropna() <= 3).sum()
print(f"  vaccination pairs with gap <= 3 days : {close_count}")

# event code variety
print(f"  distinct event codes                 : {sorted(event_df['event'].unique())}")

# zip coverage
pat_zips  = set(patient_df['zip'])
zip5_covered = pat_zips.issubset(set(zip5_df['zip5'].astype(str)))
zip3_covered = {z[:3] for z in pat_zips}.issubset(set(zip3_df['zip3'].astype(str)))
print(f"  all patient ZIPs in zip5_mapping     : {zip5_covered}")
print(f"  all patient ZIP-3s in zip3_mapping   : {zip3_covered}")

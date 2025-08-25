{\rtf1\ansi\ansicpg1252\cocoartf2821
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import re\
import numpy as np\
import pandas as pd\
\
INPUT_PATH = "/Users/banushka/Downloads/employee_data.xlsx"\
OUT_CSV   = "/Users/banushka/Downloads/employee_data_cleaned.csv"\
OUT_XLSX  = "/Users/banushka/Downloads/employee_data_cleaned.xlsx"\
\
\
# If you ever switch to a CSV, this will still work:\
if INPUT_PATH.lower().endswith((".xlsx", ".xls")):\
    df = pd.read_excel(INPUT_PATH)\
else:\
    # robust CSV load (auto-separator + tolerant to bad lines)\
    df = pd.read_csv(INPUT_PATH, sep=None, engine="python", on_bad_lines="skip", encoding="utf-8-sig")\
\
print("\uc0\u9989  Loaded:", INPUT_PATH)\
print("Columns:", list(df.columns))\
\
\
def norm_col(s: str) -> str:\
    # lowercase, remove non-alphanumerics\
    return re.sub(r"[^a-z0-9]", "", s.lower())\
\
norm_to_orig = \{norm_col(c): c for c in df.columns\}\
\
def find_col(possible_keys):\
    """Return actual column name matching any of the keys in possible_keys."""\
    for c in df.columns:\
        nc = norm_col(c)\
        for key in possible_keys:\
            if key in nc:\
                return c\
    return None\
\
salary_col   = find_col(["salary", "pay", "compensat", "ctc", "package"])\
dept_col     = find_col(["department", "dept", "division", "team"])\
join_col     = find_col(["joiningdate", "dateofjoining", "joindate", "hiredate", "startdate"])\
name_col     = find_col(["name", "employeename", "fullName".lower()])  # handles "Employee Name", "Name"\
\
print("\\nDetected columns \uc0\u8594 ",\
      f"Salary: \{salary_col\} | Department: \{dept_col\} | Joining Date: \{join_col\} | Name: \{name_col\}")\
\
\
for c in df.select_dtypes(include="object").columns:\
    df[c] = df[c].astype(str).str.strip()\
\
\
before = len(df)\
df = df.drop_duplicates()\
after = len(df)\
print(f"\\nDuplicates removed: \{before - after\}")\
\
\
def parse_salary(s):\
    """\
    Convert messy salary strings to a float (in absolute currency units).\
    Handles:\
      $50,000 | \uc0\u8377 45,000.75 | \'8060.5k | 2.5 lakh | 1.2 cr | 100k | USD 75,000\
    Heuristics:\
      k -> *1e3\
      lakh/lac/L -> *1e5\
      cr/crore -> *1e7\
      m/mn/million -> *1e6\
    """\
    if s is None or (isinstance(s, float) and np.isnan(s)):\
        return np.nan\
    s = str(s).strip().lower()\
\
    # quick empty/null guard\
    if s in \{"", "nan", "none"\}:\
        return np.nan\
\
    # multipliers\
    mult = 1.0\
    # detect magnitude words\
    if re.search(r"\\b(cr|crore)\\b", s):\
        mult = 1e7\
    elif re.search(r"\\b(lakh|lac)\\b", s):\
        mult = 1e5\
    elif re.search(r"\\b(m|mn|million)\\b", s):\
        mult = 1e6\
    elif re.search(r"\\bk\\b", s):\
        mult = 1e3\
\
    # extract the FIRST number (int or decimal)\
    m = re.search(r"(\\d+(?:\\.\\d+)?)", s.replace(",", ""))\
    if not m:\
        return np.nan\
    val = float(m.group(1)) * mult\
    return val\
\
if salary_col:\
    df[salary_col] = df[salary_col].apply(parse_salary)\
    # fill missing with median if at least one non-NaN\
    if df[salary_col].notna().any():\
        df[salary_col] = df[salary_col].fillna(df[salary_col].median())\
\
\
if join_col:\
    # dayfirst=True (common in India); coercing invalid to NaT\
    df[join_col] = pd.to_datetime(df[join_col], errors="coerce", dayfirst=True)\
\
    # fill missing with mode (most common valid date) if available\
    mode_dates = df[join_col].dropna()\
    if not mode_dates.empty:\
        df[join_col] = df[join_col].fillna(mode_dates.mode().iloc[0])\
\
\
if dept_col:\
    # Title-case then map common variants\
    df[dept_col] = df[dept_col].astype(str).str.strip().str.title()\
\
    dept_map = \{\
        "Hr": "HR",\
        "Human Resources": "HR",\
        "It": "IT",\
        "Information Technology": "IT",\
        "R&d": "R&D",\
        "Research And Development": "R&D",\
        "Fin": "Finance",\
        "Acct": "Finance",\
        "Accounts": "Finance",\
        "Biz Dev": "Business Development",\
        "Bd": "Business Development",\
        "Sales & Marketing": "Sales",\
        "Mktg": "Marketing",\
    \}\
    df[dept_col] = df[dept_col].replace(dept_map)\
    df[dept_col] = df[dept_col].replace(\{"": np.nan\}).fillna("Unknown")\
\
\
if name_col:\
    # Proper case; collapse multiple spaces\
    df[name_col] = (\
        df[name_col]\
        .astype(str)\
        .str.strip()\
        .str.replace(r"\\s+", " ", regex=True)\
        .str.title()\
    )\
\
print("\\n=== FINAL INFO ===")\
print(df.info())\
print("\\nHead:")\
print(df.head())\
\
# Save CSV\
df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")\
print(f"\\n\uc0\u55357 \u56510  Saved CSV \u8594  \{OUT_CSV\}")\
\
# Save Excel (requires openpyxl; if missing, skip gracefully)\
try:\
    df.to_excel(OUT_XLSX, index=False)\
    print(f"\uc0\u55357 \u56510  Saved Excel \u8594  \{OUT_XLSX\}")\
except Exception as e:\
    print(f"\uc0\u9888 \u65039  Skipped Excel save (install openpyxl to enable). Reason: \{e\}")\
}
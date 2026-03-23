#!/usr/bin/env python3
"""
LCA Number Finder Agent

Helps you find your LCA case number from just your employer name and filing date.
Searches the DOL quarterly disclosure Excel file automatically.

Usage:
  python3 lca_agent.py
"""
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

DOL_DISCLOSURE_URL = (
    "https://www.dol.gov/sites/dolgov/files/ETA/oflc/pdfs/"
    "LCA_Disclosure_Data_FY{fy}_Q{q}.xlsx"
)

FISCAL_QUARTER = {
    1: 2, 2: 2, 3: 2,   # Jan-Mar → Q2
    4: 3, 5: 3, 6: 3,   # Apr-Jun → Q3
    7: 4, 8: 4, 9: 4,   # Jul-Sep → Q4
    10: 1, 11: 1, 12: 1 # Oct-Dec → Q1 (next FY)
}

FISCAL_YEAR_OFFSET = {
    10: 1, 11: 1, 12: 1  # Oct-Dec belong to next fiscal year
}


def julian_day(date: datetime) -> int:
    return date.timetuple().tm_yday


def lca_prefix(date: datetime) -> str:
    yy = date.strftime("%y")
    ddd = f"{julian_day(date):03d}"
    return f"I-200-{yy}{ddd}-"


def fiscal_year_and_quarter(date: datetime) -> tuple[int, int]:
    month = date.month
    year = date.year + FISCAL_YEAR_OFFSET.get(month, 0)
    quarter = FISCAL_QUARTER[month]
    return year, quarter


def find_in_excel(filepath: str, employer: str, prefix: str, title: str = "") -> list[dict]:
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active

    headers = None
    results = []
    employer_lower = employer.lower()
    title_lower = title.lower() if title else ""

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            headers = [str(h).strip().upper() if h else "" for h in row]
            continue

        row_dict = dict(zip(headers, row))
        case = str(row_dict.get("CASE_NUMBER", "") or "")
        emp = str(row_dict.get("EMPLOYER_NAME", "") or "")
        job = str(row_dict.get("JOB_TITLE", "") or "")

        emp_match = employer_lower in emp.lower()
        title_match = not title_lower or title_lower in job.lower()

        if prefix in case and emp_match and title_match:
            results.append({
                "case_number": case.strip(),
                "employer": emp.strip(),
                "title": str(row_dict.get("JOB_TITLE", "") or "").strip(),
                "status": str(row_dict.get("CASE_STATUS", "") or "").strip(),
                "received": str(row_dict.get("RECEIVED_DATE", "") or "").strip(),
                "decision": str(row_dict.get("DECISION_DATE", "") or "").strip(),
            })

    wb.close()
    return results


def download_disclosure(fy: int, quarter: int, dest: Path) -> bool:
    if not HAS_REQUESTS:
        print("  Install requests to auto-download: pip install requests")
        return False

    url = DOL_DISCLOSURE_URL.format(fy=fy, q=quarter)
    print(f"  Downloading DOL disclosure data from:\n  {url}")
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        size_mb = dest.stat().st_size / 1_000_000
        print(f"  Downloaded: {dest.name} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"  Download failed: {e}")
        return False


def main():
    print("=== LCA Case Number Finder ===\n")

    # --- collect inputs ---
    employer = input("Employer name (partial is fine, e.g. 'Acme Corp'): ").strip()
    title = input("Job title (partial is fine, or leave blank to skip): ").strip()
    date_str = input("LCA filing date (e.g. April 1 2026 or 2026-03-16): ").strip()

    # parse date flexibly
    for fmt in ("%B %d %Y", "%b %d %Y", "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            filing_date = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    else:
        print(f"Could not parse date: {date_str}")
        sys.exit(1)

    prefix = lca_prefix(filing_date)
    fy, quarter = fiscal_year_and_quarter(filing_date)
    jday = julian_day(filing_date)

    print(f"\n--- Calculated ---")
    print(f"  Filing date    : {filing_date.strftime('%B %d, %Y')}")
    print(f"  Julian day     : {jday:03d}")
    print(f"  LCA prefix     : {prefix}")
    print(f"  DOL fiscal year: FY{fy} Q{quarter}")
    print()

    # --- find disclosure file ---
    downloads = Path.home() / "Downloads"
    candidates = list(downloads.glob(f"*FY{fy}*Q{quarter}*.xlsx")) + \
                 list(downloads.glob(f"*FY{fy}*Q{quarter}*.xlsx".replace("xlsx", "XLSX")))

    xlsx_path = None
    if candidates:
        xlsx_path = candidates[0]
        print(f"Found local disclosure file: {xlsx_path.name}")
    else:
        print(f"No local DOL disclosure file found for FY{fy} Q{quarter}.")
        choice = input("  Auto-download it? (y/n): ").strip().lower()
        if choice == "y":
            dest = downloads / f"LCA_Disclosure_Data_FY{fy}_Q{quarter}.xlsx"
            if download_disclosure(fy, quarter, dest):
                xlsx_path = dest

    if not xlsx_path:
        print("\nCan't search without the disclosure file.")
        print(f"Download manually from:")
        print(f"  https://www.dol.gov/agencies/eta/foreign-labor/performance")
        print(f"\nThen search for prefix '{prefix}' and employer '{employer}'.")
        print(f"\nOr check the FLAG portal directly:")
        print(f"  https://flag.dol.gov/case-status-search")
        sys.exit(0)

    if not HAS_OPENPYXL:
        print("\nInstall openpyxl to search the file: pip install openpyxl")
        sys.exit(1)

    # --- search ---
    filters = f"'{employer}'"
    if title:
        filters += f" + '{title}'"
    print(f"\nSearching for {filters} with prefix '{prefix}'...")
    results = find_in_excel(str(xlsx_path), employer, prefix, title)

    if not results:
        print("\nNo matching cases found.")
        print("Try a shorter employer name or verify the filing date.")
    else:
        print(f"\nFound {len(results)} case(s):\n")
        for r in results:
            print(f"  Case Number : {r['case_number']}")
            print(f"  Employer    : {r['employer']}")
            print(f"  Job Title   : {r['title']}")
            print(f"  Status      : {r['status']}")
            print(f"  Received    : {r['received']}")
            print(f"  Decision    : {r['decision']}")
            print()

        if len(results) == 1:
            case = results[0]["case_number"]
            print(f"Your case number is: {case}")
            print(f"\nTrack it live: https://flag.dol.gov/case-status-search")
            print(f"Auto-monitor : python3 lca_notify_direct.py --setup")


if __name__ == "__main__":
    main()

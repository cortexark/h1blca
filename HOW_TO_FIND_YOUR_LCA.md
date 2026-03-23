# How to Find Your LCA Case Number (Even if Your Employer Hasn't Shared It)

Most employees never get their LCA case number — employers file it quietly and move on.
But the number is **mathematically predictable** if you know your filing date.

---

## The LCA Number Formula

Every H-1B LCA case number follows this exact pattern:

```
I-200-YYDDD-XXXXXX
```

| Segment | What it means |
|---------|--------------|
| `I-200` | H-1B visa type (always the same) |
| `YY`    | 2-digit year (e.g. `26` for 2026) |
| `DDD`   | Julian day — day number of the year (e.g. April 1 = day `075`) |
| `XXXXXX`| Global sequential counter for that day |

**Example:** `I-200-26091-123456`
→ H-1B filed in **2026**, on the **91st day of the year (April 1)**, case number **123456** globally.

---

## How to Calculate Your Julian Day

Ask any LLM, calculator, or just count:

- January 1 = 001
- February 1 = 032
- March 1 = 060 (061 in leap year)
- April 1 = 091

Or use this prompt ↓

---

## Prompt to Ask Any LLM

Copy and paste this into ChatGPT, Claude, Gemini, or any AI:

```
I need to find my H-1B LCA case number on the FLAG DOL portal.

My details:
- Employer: [YOUR EMPLOYER NAME]
- Job title: [YOUR JOB TITLE]
- Filing date: [THE DATE YOUR EMPLOYER FILED THE LCA]
- Work location state: [STATE]

Please:
1. Calculate the Julian day number for my filing date
2. Give me the LCA number prefix (I-200-YYDDD-) I should search for
3. Tell me the URL to search on the FLAG DOL portal
4. Explain how to narrow down the exact 6-digit suffix by searching the employer name

The FLAG DOL portal URL is: https://flag.dol.gov/case-status-search
```

---

## How to Narrow Down the Exact Number

The last 6 digits are a global counter — you can't guess them exactly, but you can find them:

### Option 1 — Search by Employer Name on FLAG Portal
1. Go to [flag.dol.gov/case-status-search](https://flag.dol.gov/case-status-search)
2. There is no employer search directly — but DOL publishes quarterly disclosure data
3. Download from: [dol.gov/agencies/eta/foreign-labor/performance](https://www.dol.gov/agencies/eta/foreign-labor/performance)
4. Open the Excel file, filter by `EMPLOYER_NAME` + `RECEIVED_DATE`
5. Your case number will be there

### Option 2 — Ask Your HR or Attorney
Simply ask: *"Can you share my LCA case number so I can track the certification status myself?"*
It's your case — you're entitled to know it.

### Option 3 — Use This Repo's Tool
If you find your case number, use the [LCA Status Monitor](https://github.com/cortexark/h1blca) to get automated email + SMS alerts when it certifies.

---

## Why This Matters

- LCA certification takes **exactly 7 days** (automated, no human review)
- Once certified, your employer files the H-1B petition (I-129) with USCIS
- **You should know your case number** — it lets you independently verify status without depending on your employer to update you

---

## Quick Julian Day Reference for Common Dates

| Date | Julian Day | LCA Prefix (2026) |
|------|-----------|-------------------|
| Jan 1  | 001 | I-200-26001- |
| Feb 1  | 032 | I-200-26032- |
| Mar 1  | 060 | I-200-26060- |
| Mar 15 | 074 | I-200-26074- |
| Apr 1  | 091 | I-200-26091- |
| Apr 15 | 105 | I-200-26105- |

---

*Built while tracking a real LCA case. Certified in exactly 7 days.*
*Tool: [github.com/cortexark/h1blca](https://github.com/cortexark/h1blca)*

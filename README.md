# H-1B LCA & FedEx Tracker

Automatically monitors your H-1B LCA case status on the [FLAG DOL portal](https://flag.dol.gov/case-status-search) **and** tracks FedEx shipments (petition to USCIS, documents from attorney). Sends email + direct SMS alerts on every status change.

## Requirements

- Python 3.8+
- [Playwright](https://playwright.dev/python/) for browser automation
- [Twilio](https://twilio.com) *(optional — for direct SMS, free trial available)*

```bash
pip install playwright twilio
playwright install chromium
```

## Don't Know Your Case Number?

Most employers never share the LCA case number with the employee. You can find it yourself in 3 ways:

**Option 1 — Ask HR or your attorney**
Just ask: *"Can you share my LCA case number so I can track it myself?"* It's your case — you're entitled to know it.

**Option 2 — Use the finder agent**
If you know your employer name, job title, and roughly when it was filed, run:

```bash
python3 lca_agent.py
```

It downloads the DOL quarterly disclosure file, searches by employer + job title + filing date, and returns your exact case number. No manual searching needed.

**Option 3 — Search the DOL disclosure file manually**
DOL publishes every LCA filed in quarterly Excel files at [dol.gov/agencies/eta/foreign-labor/performance](https://www.dol.gov/agencies/eta/foreign-labor/performance). Filter by employer name and filing date to find your case number.

---

## Quick Start

```bash
git clone <this-repo>
cd lca-status-monitor
python3 lca_notify_direct.py
```

First run walks you through a one-time setup — no config files to edit manually.

## Setup

```bash
python3 lca_notify_direct.py
```

First run walks you through a one-time setup. You'll be asked for:

1. **LCA case number** — format `I-200-YYDDD-XXXXXX`
2. **Employer name and job title** — for notification messages
3. **Filing date**
4. **Email mode** — SMTP (Gmail App Password) or gmail-tools-mcp
5. **Email addresses** to notify
6. **SMS mode** — choose one:
   - **Twilio** *(recommended)*: direct SMS, free trial at twilio.com — needs Account SID, Auth Token, phone number
   - **Gateway**: email-to-carrier (no account needed — `number@tmomail.net` etc.)
7. **FedEx tracking numbers** — add any shipments to track (e.g. H-1B petition to USCIS)
8. **Check schedule** — times to run automated checks

Config is saved to `lca_config.json` (gitignored — your personal info never gets committed).

To change any setting later:
```bash
python3 lca_notify_direct.py --setup
```

## Usage

```bash
# Check everything (LCA + FedEx)
python3 lca_notify_direct.py

# Check LCA only
python3 lca_notify_direct.py --lca-only

# Check FedEx packages only
python3 lca_notify_direct.py --fedex-only
```

## Automating with Cron

After setup, schedule checks using cron:

```bash
crontab -e
```

Example schedule (times in PT):
```
0 6  * * 1  /path/to/lca_cron_run.sh   # Monday 6:00 AM
0 10 * * 1  /path/to/lca_cron_run.sh   # Monday 10:00 AM
0 13 * * 1  /path/to/lca_cron_run.sh   # Monday 1:00 PM
0 17 * * 5  /path/to/lca_cron_run.sh   # Friday 5:00 PM
```

> **When to check:** DOL runs its certification batch overnight. Results are typically visible by 5 AM ET on the 8th calendar day after filing. Monday morning checks (6 AM, 10 AM PT) reliably catch same-day certifications.

## How It Works

**LCA tracking:**
1. Playwright opens a headless browser → searches the FLAG DOL portal for your case number
2. Parses the status (`IN PROCESS` → `CERTIFIED`)
3. Sends email + SMS notification
4. Logs result to `lca_status_log.txt`

**FedEx tracking:**
1. Playwright scrapes fedex.com/tracking for each configured tracking number
2. Compares new status to last known status (saved in config)
3. Sends email + SMS **only when status changes** — no spam on unchanged packages
4. Detects key milestones: `Out for Delivery`, `Delivered`

## LCA Timeline

| Day | What happens |
|-----|-------------|
| 0   | Employer submits LCA on FLAG portal |
| 1–6 | DOL mandatory waiting period (fully automated, no review) |
| 7   | DOL nightly batch runs — eligible cases certified automatically |
| 7+  | `CERTIFIED` status appears on FLAG portal |

Once certified, your employer can file the H-1B petition (Form I-129) with USCIS. The petition filing date — not the certification date — is what protects your status.

## Files

| File | Purpose |
|------|---------|
| `check_lca_status.py` | Scrapes FLAG DOL portal, returns JSON status |
| `fedex_tracker.py` | Scrapes FedEx tracking page, returns JSON status |
| `lca_notify_direct.py` | Main script — checks LCA + FedEx, sends notifications |
| `sms_twilio.py` | Twilio SMS sender module |
| `lca_cron_run.sh` | Cron wrapper |
| `lca_config.json` | Your personal config (auto-created, gitignored) |
| `lca_status_log.txt` | Run history log (gitignored) |

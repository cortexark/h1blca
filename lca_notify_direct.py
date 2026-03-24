#!/usr/bin/env python3
"""
LCA status checker + FedEx tracker with email & SMS notifications.

Notification modes:
  smtp        — plain SMTP via Gmail (no extra dependencies)
  gmail-tools — uses gmail-tools-mcp library (requires MCP setup)

SMS modes:
  twilio      — direct SMS via Twilio (recommended)
  gateway     — email-to-carrier gateway (no account needed, less reliable)

First run creates lca_config.json with your settings.

Usage:
  python3 lca_notify_direct.py              # uses saved config or prompts
  python3 lca_notify_direct.py --setup      # re-run full setup
  python3 lca_notify_direct.py --fedex-only # check FedEx tracking only
  python3 lca_notify_direct.py --lca-only   # check LCA status only
"""
import asyncio
import json
import os
import smtplib
import subprocess
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "lca_config.json"
LOG_FILE    = SCRIPT_DIR / "lca_status_log.txt"


# ── Config ─────────────────────────────────────────────────────────────────

def load_or_create_config(force_setup: bool = False) -> dict:
    if CONFIG_FILE.exists() and not force_setup:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        # Migrate old configs that lack fedex / twilio blocks
        cfg.setdefault("fedex_packages", [])
        cfg.setdefault("mobile_numbers", [])
        cfg.setdefault("sms_mode", "gateway")
        cfg.setdefault("twilio", {})
        return cfg

    print("=== LCA Monitor Setup ===\n")

    case_number  = input("LCA case number (e.g. I-200-26075-123456): ").strip()
    employer     = input("Employer name: ").strip()
    job_title    = input("Job title: ").strip()
    filing_date  = input("LCA filing date (e.g. April 1, 2026): ").strip()

    # ── Email mode ──────────────────────────────────────────────────────────
    print("\nEmail notification mode:")
    print("  1. smtp        — plain Gmail SMTP (recommended)")
    print("  2. gmail-tools — uses gmail-tools-mcp library")
    mode_choice = input("Choose [1/2]: ").strip()
    mode = "smtp" if mode_choice != "2" else "gmail-tools"

    smtp_config, gmail_tools_config = {}, {}
    if mode == "smtp":
        print("\nGmail SMTP setup (use an App Password — myaccount.google.com/apppasswords):")
        smtp_config["sender"]   = input("  Your Gmail address: ").strip()
        smtp_config["password"] = input("  App password (16 chars, no spaces): ").strip()
    else:
        print("\ngmail-tools-mcp setup:")
        gmail_dir = input("  Path to gmail-tools-mcp directory: ").strip()
        gmail_tools_config["creds"] = os.path.join(gmail_dir, ".credentials/client_creds.json")
        gmail_tools_config["token"] = os.path.join(gmail_dir, ".credentials/gmail_tokens.json")
        gmail_tools_config["src"]   = os.path.join(gmail_dir, "src")

    emails_input = input("\nEmail addresses to notify (comma-separated): ").strip()
    emails = [e.strip() for e in emails_input.split(",") if e.strip()]

    # ── SMS mode ────────────────────────────────────────────────────────────
    print("\nSMS notification mode:")
    print("  1. twilio  — direct SMS via Twilio (reliable, needs free account)")
    print("  2. gateway — email-to-carrier (no account needed, may be delayed)")
    sms_choice = input("Choose [1/2]: ").strip()
    sms_mode = "twilio" if sms_choice == "1" else "gateway"

    twilio_cfg, mobile_numbers, sms_numbers = {}, [], []

    if sms_mode == "twilio":
        from sms_twilio import setup_twilio
        tmp = setup_twilio({})
        twilio_cfg    = tmp["twilio"]
        mobile_numbers = tmp["mobile_numbers"]
    else:
        sms_input = input("\nPhone numbers for SMS (comma-separated, or blank to skip): ").strip()
        if sms_input:
            carrier_map = {
                "1": ("T-Mobile", "tmomail.net"),
                "2": ("AT&T",     "txt.att.net"),
                "3": ("Verizon",  "vtext.com"),
                "4": ("Sprint",   "messaging.sprintpcs.com"),
            }
            print("Carrier: 1=T-Mobile  2=AT&T  3=Verizon  4=Sprint")
            carrier_choice = input("Carrier for all numbers [1]: ").strip() or "1"
            _, gateway_domain = carrier_map.get(carrier_choice, ("T-Mobile", "tmomail.net"))
            for num in sms_input.split(","):
                digits = "".join(c for c in num.strip() if c.isdigit())
                if digits:
                    sms_numbers.append(f"{digits}@{gateway_domain}")

    # ── FedEx packages ──────────────────────────────────────────────────────
    print("\n=== FedEx Package Tracking ===")
    print("Add FedEx tracking numbers (e.g. H-1B petition sent to USCIS).")
    fedex_packages = []
    while True:
        tn = input("  FedEx tracking number (or blank to skip/finish): ").strip()
        if not tn:
            break
        label = input(f"  Label for {tn} (e.g. 'H-1B petition to USCIS'): ").strip()
        fedex_packages.append({"tracking": tn, "label": label, "last_status": ""})

    # ── Schedule ────────────────────────────────────────────────────────────
    print("\nCheck schedule — enter times in PT (one per line, blank to finish):")
    print("  Example: Mon 6:00 AM  or  Mon 10:00 AM  or  Fri 5:00 PM")
    schedule = []
    while True:
        entry = input("  Entry (blank to finish): ").strip()
        if not entry:
            break
        schedule.append(entry)

    config = {
        "mode":             mode,
        "sms_mode":         sms_mode,
        "case_number":      case_number,
        "employer":         employer,
        "job_title":        job_title,
        "filing_date":      filing_date,
        "emails":           emails,
        "sms_numbers":      sms_numbers,      # gateway mode
        "mobile_numbers":   mobile_numbers,   # twilio mode
        "fedex_packages":   fedex_packages,
        "schedule":         schedule,
        "smtp":             smtp_config,
        "gmail_tools":      gmail_tools_config,
        "twilio":           twilio_cfg,
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nConfig saved to {CONFIG_FILE}")
    return config


# ── LCA Status ─────────────────────────────────────────────────────────────

def get_lca_status(config: dict) -> str:
    result = subprocess.run(
        ["/usr/bin/python3", str(SCRIPT_DIR / "check_lca_status.py"), config["case_number"]],
        capture_output=True, text=True,
        env={**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"}
    )
    if result.returncode != 0 or not result.stdout.strip():
        print(f"LCA check error: {result.stderr}")
        return "UNKNOWN"
    data = json.loads(result.stdout.strip())
    return data.get("status", "UNKNOWN")


# ── FedEx Tracking ─────────────────────────────────────────────────────────

def get_fedex_status(tracking_number: str) -> dict:
    result = subprocess.run(
        ["/usr/bin/python3", str(SCRIPT_DIR / "fedex_tracker.py"), tracking_number],
        capture_output=True, text=True,
        env={**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"}
    )
    if result.returncode != 0 or not result.stdout.strip():
        return {"tracking": tracking_number, "status": "UNKNOWN", "error": result.stderr}
    return json.loads(result.stdout.strip())


def check_fedex_packages(config: dict) -> list[dict]:
    """Check all FedEx packages; return list of changed ones."""
    packages = config.get("fedex_packages", [])
    if not packages:
        return []

    changed = []
    for pkg in packages:
        tn = pkg["tracking"]
        print(f"  Checking FedEx {tn} ({pkg.get('label', '')})...")
        result = get_fedex_status(tn)
        new_status = result.get("status", "UNKNOWN")
        old_status = pkg.get("last_status", "")

        print(f"    Status: {new_status}")

        if new_status != old_status:
            pkg["last_status"] = new_status
            changed.append({**pkg, **result, "previous_status": old_status})

    # Persist updated statuses
    config["fedex_packages"] = packages
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    return changed


# ── Message Building ────────────────────────────────────────────────────────

def build_lca_message(config: dict, status: str) -> tuple[str, str, str]:
    now       = datetime.now().strftime("%B %d, %Y %I:%M %p")
    certified = "CERTIFIED" in status.upper()

    subject = f"LCA {'CERTIFIED ✅' if certified else 'Status Update ⏳'} — {config['case_number']}"

    schedule_lines   = "\n".join(f"  {s}" for s in config.get("schedule", []))
    schedule_section = f"\nCheck Schedule (PT):\n{schedule_lines}" if schedule_lines else ""

    body = f"""LCA Status Update — {now}

Case Number : {config['case_number']}
Employer    : {config['employer']}
Job Title   : {config['job_title']}
Filed       : {config['filing_date']}
Status      : {status}
Checked at  : {now}

{'🎉 LCA CERTIFIED! Your employer can now file the H-1B petition (Form I-129).' if certified else '⏳ Still IN PROCESS. Will check again per schedule.'}

Check directly: https://flag.dol.gov/case-status-search
{schedule_section}"""

    sms = (
        f"LCA {status} | {config['case_number']} | {now}. "
        f"{'CERTIFIED — employer can file H-1B.' if certified else 'Still IN PROCESS.'}"
    )
    return subject, body, sms


def build_fedex_message(pkg: dict) -> tuple[str, str, str]:
    now       = datetime.now().strftime("%B %d, %Y %I:%M %p")
    label     = pkg.get("label", pkg["tracking"])
    status    = pkg.get("status", "UNKNOWN")
    location  = pkg.get("location", "")
    delivered = pkg.get("delivered", False)
    out_del   = pkg.get("out_for_delivery", False)

    emoji   = "✅" if delivered else ("🚚" if out_del else "📦")
    subject = f"FedEx {emoji} {status} — {label}"

    loc_line = f"\nLocation    : {location}" if location else ""

    body = f"""FedEx Shipment Update — {now}

Tracking    : {pkg['tracking']}
Package     : {label}
Status      : {status}{loc_line}
Previous    : {pkg.get('previous_status', 'N/A')}
Checked at  : {now}

{'✅ DELIVERED! Check your USCIS receipt notice.' if delivered else ('🚚 Out for delivery today!' if out_del else '📦 In transit — tracking updated.')}

Track: https://www.fedex.com/fedextrack/?tracknumbers={pkg['tracking']}"""

    sms = (
        f"FedEx {status} | {label} | {pkg['tracking']}. "
        f"{'DELIVERED.' if delivered else ('Out for delivery!' if out_del else 'Updated.')}"
    )
    return subject, body, sms


# ── Notification Sending ───────────────────────────────────────────────────

def send_notifications(config: dict, subject: str, body: str, sms_body: str):
    """Send email + SMS for any notification (LCA or FedEx)."""
    if config.get("mode") == "gmail-tools":
        asyncio.run(_send_via_gmail_tools(config, subject, body, sms_body))
    else:
        _send_via_smtp(config, subject, body, sms_body)


def _send_via_smtp(config: dict, subject: str, body: str, sms_body: str):
    smtp_cfg = config.get("smtp", {})
    sender   = smtp_cfg.get("sender", "")
    password = smtp_cfg.get("password", "")
    if not sender or not password:
        print("  SMTP not configured — skipping email.")
        return

    # Email recipients
    email_recipients = config.get("emails", [])
    # Gateway SMS recipients (old mode)
    gateway_recipients = config.get("sms_numbers", [])

    all_recipients = email_recipients + gateway_recipients

    gateway_domains = {"tmomail.net", "txt.att.net", "vtext.com", "messaging.sprintpcs.com"}

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        for recipient in all_recipients:
            domain = recipient.split("@")[-1] if "@" in recipient else ""
            text   = sms_body if domain in gateway_domains else body
            msg    = MIMEText(text)
            msg["Subject"] = subject
            msg["From"]    = sender
            msg["To"]      = recipient
            server.sendmail(sender, recipient, msg.as_string())
            print(f"  Sent to {recipient}")

    # Twilio SMS
    _send_twilio(config, sms_body)


async def _send_via_gmail_tools(config: dict, subject: str, body: str, sms_body: str):
    gc = config["gmail_tools"]
    sys.path.insert(0, gc["src"])
    from gmail_tools.server import GmailClient

    client = GmailClient(gc["creds"], gc["token"])
    for addr in config.get("emails", []):
        result = await client.compose(addr, subject, body)
        print(f"  Email sent to {addr}: {result}")
    for sms in config.get("sms_numbers", []):
        result = await client.compose(sms, subject, sms_body)
        print(f"  SMS sent to {sms}: {result}")

    _send_twilio(config, sms_body)


def _send_twilio(config: dict, message: str):
    """Send direct SMS via Twilio if configured."""
    mobile_numbers = config.get("mobile_numbers", [])
    if not mobile_numbers:
        return
    if not config.get("twilio", {}).get("account_sid"):
        return

    from sms_twilio import send_sms
    print(f"  Sending Twilio SMS to {len(mobile_numbers)} number(s)...")
    send_sms(mobile_numbers, message, config)


# ── Logging ────────────────────────────────────────────────────────────────

def log(entry: str):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | {entry}\n")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    force_setup  = "--setup"      in sys.argv
    fedex_only   = "--fedex-only" in sys.argv
    lca_only     = "--lca-only"   in sys.argv

    config = load_or_create_config(force_setup)

    # ── LCA Check ───────────────────────────────────────────────────────────
    if not fedex_only:
        print(f"\nChecking LCA status for {config['case_number']}...")
        lca_status = get_lca_status(config)
        print(f"  LCA Status: {lca_status}")

        subject, body, sms = build_lca_message(config, lca_status)
        send_notifications(config, subject, body, sms)
        log(f"LCA | {config['case_number']} | {lca_status}")

    # ── FedEx Check ─────────────────────────────────────────────────────────
    if not lca_only:
        packages = config.get("fedex_packages", [])
        if packages:
            print(f"\nChecking {len(packages)} FedEx package(s)...")
            changed = check_fedex_packages(config)

            if changed:
                print(f"  {len(changed)} package(s) with status update:")
                for pkg in changed:
                    print(f"    {pkg['tracking']}: {pkg.get('previous_status')} → {pkg.get('status')}")
                    subject, body, sms = build_fedex_message(pkg)
                    send_notifications(config, subject, body, sms)
                    log(f"FedEx | {pkg['tracking']} | {pkg.get('previous_status')} → {pkg.get('status')}")
            else:
                print("  No FedEx status changes.")
        elif not lca_only:
            print("\nNo FedEx packages configured. Run --setup to add tracking numbers.")

    print("\nDone.")


if __name__ == "__main__":
    main()

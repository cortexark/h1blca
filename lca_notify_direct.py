#!/usr/bin/env python3
"""
LCA status checker with email + SMS notifications.

Two modes:
  smtp        — plain SMTP, no Claude or MCP needed (works anywhere)
  gmail-tools — uses gmail-tools-mcp library (requires Claude MCP setup)

First run creates lca_config.json with your settings.

Usage:
  python3 lca_notify_direct.py           # uses saved config or prompts
  python3 lca_notify_direct.py --setup   # re-run setup to change config
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

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "lca_config.json"
LOG_FILE = SCRIPT_DIR / "lca_status_log.txt"


def load_or_create_config(force_setup: bool = False) -> dict:
    if CONFIG_FILE.exists() and not force_setup:
        with open(CONFIG_FILE) as f:
            return json.load(f)

    print("=== LCA Monitor Setup ===\n")

    case_number = input("LCA case number (e.g. I-200-26075-123456): ").strip()
    employer = input("Employer name: ").strip()
    job_title = input("Job title: ").strip()
    filing_date = input("LCA filing date (e.g. April 1, 2026): ").strip()

    print()
    print("Notification mode:")
    print("  1. smtp        — plain email via Gmail SMTP (no Claude needed)")
    print("  2. gmail-tools — uses gmail-tools-mcp library (requires MCP setup)")
    mode_choice = input("Choose [1/2]: ").strip()
    mode = "smtp" if mode_choice != "2" else "gmail-tools"

    smtp_config = {}
    gmail_tools_config = {}

    if mode == "smtp":
        print("\nGmail SMTP setup:")
        print("  (use an App Password — https://myaccount.google.com/apppasswords)")
        smtp_config["sender"] = input("  Your Gmail address: ").strip()
        smtp_config["password"] = input("  App password (16 chars, no spaces): ").strip()
    else:
        print("\ngmail-tools-mcp setup:")
        gmail_dir = input("  Path to gmail-tools-mcp directory: ").strip()
        gmail_tools_config["creds"] = os.path.join(gmail_dir, ".credentials/client_creds.json")
        gmail_tools_config["token"] = os.path.join(gmail_dir, ".credentials/gmail_tokens.json")
        gmail_tools_config["src"] = os.path.join(gmail_dir, "src")

    print()
    emails_input = input("Email addresses to notify (comma-separated): ").strip()
    emails = [e.strip() for e in emails_input.split(",") if e.strip()]

    print()
    carrier_map = {
        "1": ("T-Mobile",  "tmomail.net"),
        "2": ("AT&T",      "txt.att.net"),
        "3": ("Verizon",   "vtext.com"),
        "4": ("Sprint",    "messaging.sprintpcs.com"),
    }
    sms_numbers = []
    sms_input = input("Phone numbers for SMS (comma-separated, or blank to skip): ").strip()
    if sms_input:
        print("Carrier options: 1=T-Mobile  2=AT&T  3=Verizon  4=Sprint")
        carrier_choice = input("Carrier for all numbers [1]: ").strip() or "1"
        _, gateway = carrier_map.get(carrier_choice, ("T-Mobile", "tmomail.net"))
        for num in sms_input.split(","):
            digits = "".join(c for c in num.strip() if c.isdigit())
            if digits:
                sms_numbers.append(f"{digits}@{gateway}")

    print()
    print("Check schedule — enter times in PT (free text), one per line, blank to finish:")
    print("  Example: Mon 6:00 AM, Mon 10:00 AM, Fri 5:00 PM")
    schedule = []
    while True:
        entry = input("  Entry (or blank to finish): ").strip()
        if not entry:
            break
        schedule.append(entry)

    config = {
        "mode": mode,
        "case_number": case_number,
        "employer": employer,
        "job_title": job_title,
        "filing_date": filing_date,
        "emails": emails,
        "sms_numbers": sms_numbers,
        "schedule": schedule,
        "smtp": smtp_config,
        "gmail_tools": gmail_tools_config,
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nConfig saved to {CONFIG_FILE}")
    return config


def get_status(config: dict) -> str:
    result = subprocess.run(
        ["/usr/bin/python3", str(SCRIPT_DIR / "check_lca_status.py"), config["case_number"]],
        capture_output=True, text=True,
        env={**os.environ, "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"}
    )
    if result.returncode != 0 or not result.stdout.strip():
        print(f"Error checking status: {result.stderr}")
        return "UNKNOWN"
    data = json.loads(result.stdout.strip())
    return data.get("status", "UNKNOWN")


def build_message(config: dict, status: str) -> tuple[str, str, str]:
    now = datetime.now().strftime("%B %d, %Y %I:%M %p")
    certified = "CERTIFIED" in status.upper()

    subject = f"LCA {'APPROVED ✅' if certified else 'Status Update ⏳'} — {config['case_number']}"

    schedule_lines = "\n".join(f"  {s}" for s in config.get("schedule", []))
    schedule_section = f"\nCheck Schedule (PT):\n{schedule_lines}" if schedule_lines else ""

    body = f"""LCA Status Update — {now}

Case Number : {config['case_number']}
Employer    : {config['employer']}
Job Title   : {config['job_title']}
Filed       : {config['filing_date']}
Status      : {status}
Checked at  : {now}

{'🎉 Your LCA has been CERTIFIED! Your employer can now proceed with the H-1B petition.' if certified else '⏳ Still IN PROCESS. Will check again per schedule.'}

Check directly: https://flag.dol.gov/case-status-search
{schedule_section}"""

    sms_body = (
        f"LCA {status} — {config['case_number']}. "
        f"Checked {now}. "
        f"{'CERTIFIED! Employer can proceed with H-1B.' if certified else 'Still IN PROCESS.'}"
    )

    return subject, body, sms_body


def send_via_smtp(config: dict, status: str):
    subject, body, sms_body = build_message(config, status)
    smtp_cfg = config["smtp"]
    sender = smtp_cfg["sender"]
    password = smtp_cfg["password"]

    recipients = config.get("emails", []) + config.get("sms_numbers", [])
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        for recipient in recipients:
            text = sms_body if "@tmomail.net" in recipient or "txt.att.net" in recipient \
                            or "vtext.com" in recipient or "sprintpcs.com" in recipient \
                            else body
            msg = MIMEText(text)
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = recipient
            server.sendmail(sender, recipient, msg.as_string())
            print(f"Sent to {recipient}")


async def send_via_gmail_tools(config: dict, status: str):
    gc = config["gmail_tools"]
    sys.path.insert(0, gc["src"])
    from gmail_tools.server import GmailClient

    subject, body, sms_body = build_message(config, status)
    client = GmailClient(gc["creds"], gc["token"])

    for addr in config.get("emails", []):
        result = await client.compose(addr, subject, body)
        print(f"Email sent to {addr}: {result}")

    for sms in config.get("sms_numbers", []):
        result = await client.compose(sms, subject, sms_body)
        print(f"SMS sent to {sms}: {result}")


def main():
    force_setup = "--setup" in sys.argv
    config = load_or_create_config(force_setup)

    status = get_status(config)
    print(f"Status: {status}")

    if config.get("mode") == "gmail-tools":
        asyncio.run(send_via_gmail_tools(config, status))
    else:
        send_via_smtp(config, status)

    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | {config['case_number']} | {status}\n")


if __name__ == "__main__":
    main()

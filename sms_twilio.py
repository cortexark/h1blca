"""
Twilio SMS sender.
Requires: pip install twilio
Credentials in lca_config.json under "twilio" key, or set env vars:
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER
"""
import os
import json
from pathlib import Path


def send_sms(to_numbers: list[str], message: str, config: dict) -> list[dict]:
    """
    Send SMS via Twilio.
    to_numbers: list of E.164 phone numbers e.g. ["+14085551234"]
    config: dict with twilio.account_sid, twilio.auth_token, twilio.from_number
    Returns list of result dicts.
    """
    try:
        from twilio.rest import Client
    except ImportError:
        print("Twilio not installed. Run: pip install twilio")
        return [{"error": "twilio not installed"}]

    twilio_cfg = config.get("twilio", {})
    account_sid = (twilio_cfg.get("account_sid")
                   or os.getenv("TWILIO_ACCOUNT_SID", ""))
    auth_token  = (twilio_cfg.get("auth_token")
                   or os.getenv("TWILIO_AUTH_TOKEN", ""))
    from_number = (twilio_cfg.get("from_number")
                   or os.getenv("TWILIO_FROM_NUMBER", ""))

    if not all([account_sid, auth_token, from_number]):
        print("Twilio credentials missing — check config or env vars.")
        return [{"error": "missing credentials"}]

    client = Client(account_sid, auth_token)
    results = []
    for number in to_numbers:
        try:
            msg = client.messages.create(
                body=message,
                from_=from_number,
                to=number
            )
            print(f"  SMS sent to {number} — SID: {msg.sid}")
            results.append({"to": number, "sid": msg.sid, "status": msg.status})
        except Exception as e:
            print(f"  SMS failed to {number}: {e}")
            results.append({"to": number, "error": str(e)})
    return results


def setup_twilio(config: dict) -> dict:
    """Interactive Twilio setup — adds credentials to config."""
    print("\n=== Twilio SMS Setup ===")
    print("Sign up free at twilio.com — get $15 trial credit")
    print("You need: Account SID, Auth Token, and a Twilio phone number\n")

    account_sid = input("  Account SID (starts with AC...): ").strip()
    auth_token  = input("  Auth Token: ").strip()
    from_number = input("  Twilio phone number (E.164, e.g. +14155551234): ").strip()

    print("\nPhone numbers to receive SMS alerts:")
    numbers_input = input("  Your mobile numbers (E.164, comma-separated): ").strip()
    mobile_numbers = [n.strip() for n in numbers_input.split(",") if n.strip()]

    config["twilio"] = {
        "account_sid": account_sid,
        "auth_token": auth_token,
        "from_number": from_number,
    }
    config["mobile_numbers"] = mobile_numbers
    return config

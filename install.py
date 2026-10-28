"""One-time setup for open_wsj.py. Run it from this folder:

    python3 install.py

It will:
  1. ask for your Gmail address and save it to config.json
  2. store your Gmail app password in the macOS Keychain (you type it, it's never saved in a file)
  3. schedule open_wsj.py to run every day at 7:00am
  4. do a test run to make sure it can find your WSJ email

Safe to run again if you need to change your address, password, or time.
"""
import getpass
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "open_wsj.py"
CONFIG_FILE = HERE / "config.json"
LOG_FILE = HERE / "log.txt"
KEYCHAIN_SERVICE = "wsj-script"  # must match open_wsj.py
LABEL = f"com.{getpass.getuser()}.wsj-edition"
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"

PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>{script}</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>{hour}</integer>
        <key>Minute</key><integer>{minute}</integer>
    </dict>
    <key>StandardOutPath</key><string>{log}</string>
    <key>StandardErrorPath</key><string>{log}</string>
</dict>
</plist>
"""


def ask_gmail() -> str:
    current = ""
    if CONFIG_FILE.exists():
        current = json.loads(CONFIG_FILE.read_text()).get("gmail", "")
    prompt = f"Gmail address [{current}]: " if current else "Gmail address: "
    gmail = input(prompt).strip() or current
    if "@" not in gmail:
        sys.exit("That doesn't look like an email address.")
    CONFIG_FILE.write_text(json.dumps({"gmail": gmail}))
    return gmail


def save_password(gmail: str) -> None:
    print("\nNext, your Gmail *app password* (16 letters, from myaccount.google.com/apppasswords).")
    print("The Mac will ask you to type it twice. Nothing shows as you type; that's normal.")
    # -U updates an existing entry; -w with no value makes `security` prompt for it,
    # so the password never appears on screen or in a file.
    subprocess.run(
        ["security", "add-generic-password", "-U", "-a", gmail, "-s", KEYCHAIN_SERVICE, "-w"],
        check=True,
    )


def ask_time() -> tuple[int, int]:
    answer = input("\nWhat time should it open the paper each day? (24-hour, e.g. 7:00) [7:00]: ").strip()
    hour, _, minute = (answer or "7:00").partition(":")
    return int(hour), int(minute or 0)


def schedule(hour: int, minute: int) -> None:
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_text(PLIST_TEMPLATE.format(
        label=LABEL, python=sys.executable, script=SCRIPT, hour=hour, minute=minute, log=LOG_FILE,
    ))
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(PLIST)], capture_output=True)  # ok if not loaded yet
    subprocess.run(["launchctl", "bootstrap", domain, str(PLIST)], check=True)
    print(f"Scheduled daily at {hour}:{minute:02d}.")


def main() -> None:
    gmail = ask_gmail()
    save_password(gmail)
    hour, minute = ask_time()
    schedule(hour, minute)
    print("\nTest run (finds the link but doesn't open it):")
    subprocess.run([sys.executable, str(SCRIPT), "--dry-run"])
    print(f"\nAll set. Check {LOG_FILE.name} if the paper ever doesn't open.")


if __name__ == "__main__":
    main()

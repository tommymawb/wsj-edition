"""Find today's WSJ Print Edition email in Gmail and open its link in Chrome.

The PDF link needs your WSJ login, so we let Chrome (where you're signed in) do the download.
Your Gmail app password is read from the macOS Keychain, never stored in this file.
Run install.py once first: it saves your Gmail address to config.json and sets up the daily schedule.

Usage:
    python3 open_wsj.py --dry-run   # show the link it found, don't open it
    python3 open_wsj.py             # open the link in Chrome (once per edition)
"""
import argparse
import email
import imaplib
import json
import re
import subprocess
import sys
import time
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG_FILE = HERE / "config.json"  # written by install.py: {"gmail": "you@gmail.com"}
KEYCHAIN_SERVICE = "wsj-script"
SUBJECT_TEXT = "Wall Street Journal Print Edition"  # no apostrophe: it breaks Gmail's IMAP search
LOOKBACK_DAYS = 3  # ignore emails older than this
RETRIES = 6          # how many times to try if the network isn't up yet
RETRY_WAIT = 60      # seconds between tries (about 5 minutes total)
STATE_FILE = HERE / "opened.json"


def gmail_user() -> str:
    try:
        return json.loads(CONFIG_FILE.read_text())["gmail"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        sys.exit("No Gmail address set up yet. Run: python3 install.py")


class LinkCollector(HTMLParser):
    """Collects (link text, href) pairs from an HTML email."""

    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            self.links.append((" ".join("".join(self._text).split()), self._href))
            self._href = None


def unwrap_urldefense(url: str) -> str:
    """OSU's mail scanner wraps links as urldefense.com/v3/__REAL_URL__;!!...  Undo that."""
    match = re.search(r"urldefense\.com/v3/__(.+?)__;", url)
    return match.group(1) if match else url


def keychain_password() -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-a", gmail_user(), "-s", KEYCHAIN_SERVICE, "-w"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip().replace(" ", "")  # Google shows app passwords with spaces


def html_body(msg) -> str:
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
    return ""


def find_edition_link(html: str):
    collector = LinkCollector()
    collector.feed(html)
    for text, href in collector.links:  # best match: the "Read Today's Edition" button
        if "read today" in text.lower():
            return unwrap_urldefense(href)
    for _, href in collector.links:  # fallback: any link that points straight at the PDF
        if "WSJNewsPaper" in href:
            return unwrap_urldefense(href)
    return None


def latest_edition_email():
    """Return (message_id, link, email_date) for the newest matching email, or None."""
    since = (date.today() - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
    with imaplib.IMAP4_SSL("imap.gmail.com") as imap:
        imap.login(gmail_user(), keychain_password())
        imap.select("INBOX", readonly=True)
        _, data = imap.search(None, "SINCE", since, "SUBJECT", f'"{SUBJECT_TEXT}"')
        ids = data[0].split()
        for num in reversed(ids):  # newest first
            _, fetched = imap.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(fetched[0][1])
            link = find_edition_link(html_body(msg))
            if link:
                return msg["Message-ID"], link, msg["Date"]
    return None


def already_opened(message_id: str) -> bool:
    try:
        return message_id in json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def remember(message_id: str) -> None:
    try:
        opened = json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        opened = []
    STATE_FILE.write_text(json.dumps(opened[-30:] + [message_id]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    found = None
    for attempt in range(1, RETRIES + 1):
        try:
            found = latest_edition_email()
            break
        except (OSError, imaplib.IMAP4.abort) as e:  # no network yet, e.g. right after waking
            print(f"Attempt {attempt}/{RETRIES} failed: {e}")
            if attempt == RETRIES:
                print("Giving up; will try again at the next scheduled run.")
                return
            time.sleep(RETRY_WAIT)
    if not found:
        print("No recent WSJ edition email found in Gmail.")
        return
    message_id, link, sent = found
    print(f"Found edition email from {sent}\n{link}")

    if args.dry_run:
        return
    if already_opened(message_id):
        print("Already opened this edition.")
        return
    subprocess.run(["open", "-a", "Google Chrome", link], check=True)
    remember(message_id)
    print("Opened in Chrome.")


if __name__ == "__main__":
    main()

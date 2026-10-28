# WSJ Edition Opener

Opens the Wall Street Journal print edition in Chrome every morning, automatically.

WSJ emails subscribers a "Wall Street Journal Print Edition" message with a **Read Today's Edition** link. This script checks your Gmail for that email each morning and opens the link in Chrome, where you're already signed in to WSJ.

## What you need

- A Mac with **Google Chrome**, signed in to your WSJ account
- A WSJ subscription that sends the **Print Edition** email
- **Gmail**, with 2-Step Verification turned on
- **Python 3** (type `python3 --version` in Terminal; if it isn't installed, macOS will offer to install it)

If your WSJ email goes to a different account (like a school Outlook), set up a rule there that forwards it to your Gmail.

## Setup

1. **Make a Gmail app password.** Go to <https://myaccount.google.com/apppasswords>, create one (name it anything, like "WSJ"), and copy the 16-letter password. This lets the script read your email without your real password.

2. **Download this project.** Click the green **Code** button on this page → **Download ZIP**, then unzip it somewhere you'll keep it, such as your home folder. (Don't move the folder afterwards. If you do, run step 3 again.)

3. **Run the installer.** Open Terminal, then type `cd ` (with a space), drag the unzipped folder into the Terminal window, and press Return. Then run:

   ```
   python3 install.py
   ```

   It asks for your Gmail address, your app password, and what time to open the paper, then does a test run.

That's it. The paper opens every morning at the time you picked, as long as your Mac is on and you're logged in.

## Using it

- `python3 open_wsj.py --dry-run`: find today's link without opening it
- `python3 open_wsj.py`: open it now
- `log.txt` shows what happened each morning
- Each edition only opens once, even if the script runs again

## Troubleshooting

- **"No recent WSJ edition email found"**: check that the Print Edition email is actually arriving in your Gmail inbox (not spam).
- **Login error**: rerun `python3 install.py` and re-enter the app password.
- **WSJ asks you to sign in**: sign in to wsj.com in Chrome once; it'll remember you.

## Uninstall

```
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.$(whoami).wsj-edition.plist
rm ~/Library/LaunchAgents/com.$(whoami).wsj-edition.plist
```

Then delete the folder.

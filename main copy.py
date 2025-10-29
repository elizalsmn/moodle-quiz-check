import os
from dotenv import load_dotenv
import time
import subprocess
from pathlib import Path
from getpass import getpass
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


# ---- CONFIG ----
load_dotenv()
LOGIN_URL   = os.getenv("LOGIN_URL", "https://moodle.hku.hk/login/index.php")
TARGET_URL  = os.getenv("TARGET_URL", "")
KEYWORD     = os.getenv("KEYWORD", "nothing")
INTERVAL    = int(os.getenv("INTERVAL", 5))
FIRST_DUMP  = Path(os.getenv("FIRST_DUMP", "example.txt"))
HEADLESS    = False 
MANUAL_LOGIN_WAIT = int(os.getenv("MANUAL_LOGIN_WAIT", "30"))

def notify_mac():
    try:
        for i in range(3):
            subprocess.run(
                ["afplay", "/System/Library/Sounds/Glass.aiff"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
    except Exception:
        try:
            subprocess.run(["say", "Keyword found"], check=False)
        except Exception:
            print("\a", end="", flush=True)

def manual_login(page):
    """Open browser and wait for user to login manually"""
    print("\n" + "="*60)
    print("🔐 MANUAL LOGIN REQUIRED")
    print("="*60)
    print(f"Opening login page: {LOGIN_URL}")
    print(f"\nPlease login in the browser window.")
    print(f"You have {MANUAL_LOGIN_WAIT} seconds to complete the login.")
    print("DO NOT CLOSE THE BROWSER - just login and leave it open!")
    print("The script will continue automatically after login.")
    print("="*60 + "\n")
    
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    
    start_time = time.time()
    while time.time() - start_time < MANUAL_LOGIN_WAIT:
        try:
            current_url = page.url.lower()
            if "login" not in current_url or TARGET_URL.lower() in current_url:
                print("✅ Login detected! Continuing...")
                time.sleep(2)  
                return True
            time.sleep(1)
        except Exception as e:
            print(f"[!] Error checking login: {e}")
            pass
    
    try:
        current_url = page.url.lower()
        if "login" not in current_url or TARGET_URL.lower() in current_url:
            print("✅ Login successful!")
            return True
        else:
            print("⚠️  Login timeout - continuing anyway...")
            print("If the page is stuck on login, the script may not work properly.")
            return False
    except Exception:
        print("⚠️  Could not verify login status - continuing anyway...")
        return False

def page_text(page) -> str:
    try:
        return page.inner_text("body", timeout=8000)
    except Exception:
        return page.content() 

def ensure_logged_in_and_on_target(page):
    if "login" in (page.url or "").lower():
        manual_login(page)
    if page.url.rstrip("/") != TARGET_URL.rstrip("/"):
        page.goto(TARGET_URL, wait_until="domcontentloaded")

def main():
    if "example.com" in TARGET_URL or TARGET_URL.endswith("..."):
        raise SystemExit("Please set TARGET_URL to the exact Moodle page you want to monitor.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        ctx = browser.new_context()
        page = ctx.new_page()

        manual_login(page)
        page.goto(TARGET_URL, wait_until="domcontentloaded")

        txt = page_text(page)
        try:
            FIRST_DUMP.write_text(txt, encoding="utf-8")
            print(f"[+] First scrape saved to {FIRST_DUMP.resolve()}")
        except Exception as e:
            print(f"[!] Could not save first scrape: {e}")

        print(f"\nMonitoring {TARGET_URL!r} for {KEYWORD!r} every {INTERVAL}s. Ctrl+C to stop.\n")
        while True:
            try:
                ensure_logged_in_and_on_target(page)
                txt = page_text(page)
                
                try:
                    FIRST_DUMP.write_text(txt, encoding="utf-8")
                    ts = time.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{ts}] 💾 Saved to {FIRST_DUMP.name}")
                except Exception as e:
                    print(f"[!] Could not save scrape: {e}")
                
                if KEYWORD.lower() in txt.lower():
                    ts = time.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{ts}] ✅ Found '{KEYWORD}'")
                    notify_mac()
                    print("\n🎉 Keyword found! Stopping monitor.")
                    break 
                else:
                    ts = time.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{ts}] ❌ Not found yet...")

                time.sleep(INTERVAL)
                page.reload(wait_until="domcontentloaded")
            except KeyboardInterrupt:
                print("\nBye!")
                break
            except Exception as e:
                print(f"[!] Error: {e}")
                time.sleep(INTERVAL)

        ctx.close()
        browser.close()

if __name__ == "__main__":
    main()

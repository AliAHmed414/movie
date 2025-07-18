from playwright.sync_api import sync_playwright
import os

# Path to Brave browser executable
brave_path = "/usr/bin/brave-browser"  # already confirmed

# Path to Brave user data directory
user_data_dir = os.path.expanduser("~/.config/BraveSoftware/Brave-Browser")
profile_name = "Default"

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        executable_path=brave_path,
        headless=False,
        args=[f"--profile-directory={profile_name}"]
    )
    
    page = browser.new_page()
    page.goto("https://example.com")
    
    input("Press Enter to close...")
    browser.close()
import undetected_chromedriver as uc
import time
import json
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def save_session(driver, filename="session.json"):
    """Save cookies and local storage from manual session"""
    cookies = driver.get_cookies()
    
    # Try to get local storage (may not work in all cases)
    local_storage = {}
    try:
        local_storage = driver.execute_script("return window.localStorage;")
    except:
        pass
    
    session_data = {
        'cookies': cookies,
        'local_storage': local_storage,
        'user_agent': driver.execute_script("return navigator.userAgent;")
    }
    
    with open(filename, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    print(f"✓ Session saved to {filename}")

def load_session(driver, filename="session.json"):
    """Load cookies and session data"""
    if not os.path.exists(filename):
        print(f"⚠ Session file {filename} not found")
        return False
    
    with open(filename, 'r') as f:
        session_data = json.load(f)
    
    # Load cookies
    for cookie in session_data['cookies']:
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            print(f"Failed to add cookie {cookie['name']}: {e}")
    
    # Load local storage
    if session_data.get('local_storage'):
        for key, value in session_data['local_storage'].items():
            try:
                driver.execute_script(f"window.localStorage.setItem('{key}', '{value}');")
            except:
                pass
    
    print("✓ Session loaded successfully")
    return True

def manual_auth_step():
    """Step 1: Manual authentication to get past Cloudflare"""
    print("=== STEP 1: Manual Authentication ===")
    print("This will open a browser for you to manually solve Cloudflare challenges")
    
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # Use a persistent profile
    profile_path = "/tmp/manual_auth_profile"
    options.add_argument(f'--user-data-dir={profile_path}')
    
    driver = uc.Chrome(options=options)
    
    try:
        print("Opening hianime.to...")
        driver.get("https://hianime.to")
        
        print("\n" + "="*60)
        print("MANUAL ACTION REQUIRED:")
        print("1. Wait for the page to fully load")
        print("2. Complete any Cloudflare challenges that appear")
        print("3. Navigate to any page on the site to confirm access")
        print("4. Press ENTER here when you're ready to save the session")
        print("="*60)
        
        input("Press ENTER after completing manual authentication...")
        
        # Save the session
        save_session(driver, "hianime_session.json")
        
        print("✓ Manual authentication completed!")
        
    finally:
        driver.quit()

def automated_access():
    """Step 2: Use saved session for automated access"""
    print("\n=== STEP 2: Automated Access ===")
    
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # Use the same profile as manual auth
    profile_path = "/tmp/manual_auth_profile"
    options.add_argument(f'--user-data-dir={profile_path}')
    
    driver = uc.Chrome(options=options)
    
    try:
        # First go to the main site
        print("Loading hianime.to with saved session...")
        driver.get("https://hianime.to")
        
        # Load saved session data
        time.sleep(2)
        load_session(driver, "hianime_session.json")
        
        # Refresh to apply session
        driver.refresh()
        time.sleep(3)
        
        # Check if we're authenticated
        if "cloudflare" not in driver.page_source.lower():
            print("✓ Successfully bypassed Cloudflare!")
            
            # Now navigate to target page
            print("Navigating to episode page...")
            driver.get("https://hianime.to/watch/one-piece-100?ep=2142")
            
            # Wait and check
            time.sleep(5)
            
            if "episode" in driver.page_source.lower() or "watch" in driver.page_source.lower():
                print("✓ Successfully accessed episode page!")
                print(f"Current URL: {driver.current_url}")
                
                # Keep browser open for interaction
                print("Browser will stay open for 60 seconds...")
                time.sleep(60)
            else:
                print("⚠ May still be blocked or redirected")
        else:
            print("⚠ Still encountering Cloudflare challenges")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        driver.quit()

def main():
    print("HiAnime.to Access Tool")
    print("This uses a two-step process:")
    print("1. Manual authentication to bypass Cloudflare")
    print("2. Automated access using the saved session")
    
    while True:
        print("\nOptions:")
        print("1. Manual authentication (run first)")
        print("2. Automated access (run after manual auth)")
        print("3. Both steps (recommended)")
        print("4. Exit")
        
        choice = input("Choose option (1-4): ").strip()
        
        if choice == '1':
            manual_auth_step()
        elif choice == '2':
            automated_access()
        elif choice == '3':
            manual_auth_step()
            time.sleep(2)
            automated_access()
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    main()
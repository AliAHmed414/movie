import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_mediafire_cookie(email, password):
    """
    Login to MediaFire and return cookie string
    
    Args:
        email (str): MediaFire email
        password (str): MediaFire password
        
    Returns:
        str: Cookie string or None if failed
    """
    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        driver = uc.Chrome(
            options=options
        )

        driver.get("https://www.mediafire.com/login/")
        wait = WebDriverWait(driver, 15)

        # Wait for and fill login form
        wait.until(EC.presence_of_element_located((By.ID, "widget_login_email"))).send_keys(email)
        driver.find_element(By.ID, "widget_login_pass").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Wait for login to complete and get cookies
        required_cookies = {'ukey', 'session', 'user'}
        for _ in range(30):  # 30 seconds max
            cookies = driver.get_cookies()
            cookie_dict = {c['name']: c['value'] for c in cookies}
            if required_cookies.issubset(cookie_dict.keys()):
                cookie_string = '; '.join([f"{k}={v}" for k, v in cookie_dict.items()])
                return cookie_string
            time.sleep(1)
        
        raise Exception("Required cookies not found after waiting.")

    except Exception as e:
        print(f"Failed to get cookie for {email}: {e}")
        return None

    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    # Example usage
    email = input("Enter email: ")
    password = input("Enter password: ")
    
    cookie = get_mediafire_cookie(email, password)
    if cookie:
        print(f"Cookie: {cookie}")
    else:
        print("Failed to get cookie")
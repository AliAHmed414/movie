import undetected_chromedriver as uc
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import os
import re

def setup_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")  # Use new headless mode for recent versions
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--remote-debugging-port=0") 
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2
    })

    # Match the major version of your installed Chrome
    return uc.Chrome(options=options)


def apply_cookies(driver):
    cookie_string = '''
    zencookie=5676573621744273232; _yasc=lFP9uRKOFaO9Ms0WTRpOEiyNlRDtugZ2YtykFRQ+tXJU/KoDAW4dKP0hfx5iN8BE2/AI; yandex_login=asadmoahmed405@gmail.com; yandexuid=9624868961753132085; mda2_beacon=1753232750028; Zen-User-Data={%22zen-theme%22:%22light%22%2C%22zen-theme-setting%22:%22light%22}; rec-tech=true; addruid=z1e74V4r2d7Et32A5a3g4C8ut0; editor-poll-times-shown=2; stable_city=2; zen_gid=11485; zen_vk_gid=84; HgGedof=1; zen_session_id=CKARuO9Tm9L7exXv5fDwwl1MGHs7n3gnDSC.1753132331604; Session_id=3:1753232750.5…B_2Pk6RCnXTWg5djX9KcEoJ90INlV5nZeEZcA.1Qh7bJ9TnZSSdmQKAAYUlnH36N5hgykvYA_HzRLh9VU; has_stable_city=true; zen_ms_socdem_pixels=2495139%2C3212785%2C3212791; cmtchd=MTc1MzEzMjMzOTQ5Mg==; crookie=6r1IkEx8oJiwEEe/qeJR14XaYvkdafzhYstSkaz79N74hPZTtFXKkzyMMM0xGrJc4/LfYDl0vFAy/YJ4PIeaeFz5omg=; news_cryproxy_sync_ok=1; cryproxy_sync_ok=1; zen_sso_checked=1; ys=udn.cDp6eGU%3D#c_chck.148314140; sso_status=sso.passport.yandex.ru:synchronized; zen_has_vk_auth_after_sso=1; is_auth_through_phone=true; is_online_stat=false
    '''
    for part in cookie_string.strip().split("; "):
        try:
            name, value = part.split("=", 1)
            driver.add_cookie({
                "name": name,
                "value": value,
                "domain": ".dzen.ru",
                "path": "/"
            })
        except Exception as e:
            print(f"Could not add cookie {name}: {e}")

          
def wait_for_upload(driver):
    # Wait for upload completion with dynamic timeout based on file size
    file_size_mb = os.path.getsize("/home/kda/comdy.mp4") / (1024 * 1024) if os.path.exists("/home/kda/comdy.mp4") else 100
    max_wait = max(300, int(file_size_mb * 8))  # 8 seconds per MB, minimum 5 minutes
    
    try:
        WebDriverWait(driver, max_wait).until(
            EC.any_of(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Загрузили видео')]")),
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='publish-btn']:not([disabled])"))
            )
        )
        return True
    except:
        return False

def login_and_upload(driver, video_path, title="Comedy Video"):
    # Login with cookies
    driver.get("https://dzen.ru")
    time.sleep(1)  # Wait for the page to load
    apply_cookies(driver)
    time.sleep(1)  
    # Navigate and upload
    driver.get("https://dzen.ru/profile/editor/id/687635ef8effd56439915091/publications?state=published")
    time.sleep(2)
    
    # Close modals
    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        driver.execute_script("document.querySelectorAll('[data-testid=\"modal-overlay\"], .modal__overlay').forEach(el => el.style.display = 'none');")
    except: pass
    
    # Upload process
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='add-publication-button']"))).click()
    time.sleep(2)
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//label[@aria-label='Загрузить видео']"))).click()
    time.sleep(2)
    
    # Upload file
    file_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
    file_input.send_keys(video_path)
    print("Video uploaded")
    
    # Wait for upload completion - OPTIMIZED PART
    if not wait_for_upload(driver):
        print("Upload timeout")
        return None
    
    time.sleep(5)
    
    try:
        title_textarea = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "textarea.Texteditor-Control:not(.Texteditor-Control_isHidden)")))
        title_textarea.clear()
        title_textarea.send_keys(title)
        print("Title set")
    except: print("Could not set title")

    url = driver.current_url
    if "videoEditorPublicationId=" in url:
        video_id = url.split("videoEditorPublicationId=")[1].split("&")[0]
    
    # Publish
    WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='publish-btn']"))).click()
    print("Published")
    
    if video_id: return f"https://dzen.ru/video/watch/{video_id}"
    else: return None

def main_with_path(video_path, title="Uploaded Video"):
    if not os.path.exists(video_path):
        return None

    driver = setup_driver()
    try:
        return login_and_upload(driver, video_path, title)
    except:
        return None
    finally:
        driver.quit()

def main():
    return main_with_path("/home/kda/file.mp4", "Comssedy Video")

if __name__ == "__main__":
    result = main()
    print(f"Result: {result}")
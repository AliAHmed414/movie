from selenium import webdriver
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
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2
    })

    # Path to Edge binary
    options.binary_location = "/usr/bin/microsoft-edge"
    
    # Create service object for Edge
    service = Service()  # Will use default msedgedriver path or specify: Service("/path/to/msedgedriver")
    
    return webdriver.Edge(service=service, options=options)


def apply_cookies(driver):
    cookie_string = '''
    HgGedof=1; zencookie=7531797071752581269; zen_sso_checked=1; Session_id=noauth:1752581271; sessar=1.1204.CiDmMfadzG-6eQL9nPlZtaynZYTeiAdB3jA34Gq9taugfg.2tSWBAahKjSBntrBqUTkfQ-Vi41_T9Jt4DPYb51BEvo; yandex_login=; ys=c_chck.4292637706; yandexuid=6610916351752581271; mda2_beacon=1752581271613; sso_status=sso.passport.yandex.ru:synchronized; zen_vk_sso_checked=1; zen_session_id=Mrfsnv6IDZ4xlKg5M5E18ekq6Q8wvCGoog8.1752581273137; _yasc=nR7KKZ56msTkT57bMPXPI7/PXJk/KAtRsC34q7tr3FulibCt543cviv/mLceVRDYRFI=; Zen-User-Data={%22zen-theme%22:%22light%22%2C%22zen-theme-setting%22:%22light%22}; is_auth_through_phone=true; is_online_stat=false; stable_city=0; has_stable_city=true; zen_gid=11485; zen_vk_gid=84; one_day_socdem=+; zen_ms_socdem_pixels=2495135%2C3212781%2C3212787; crookie=thepB5ZcciB+w35i9e4fm8ObluZNu6UseEzz23QTKyLPfcYWn+hbv4R30Y7ovbe6wWpTPPKDyTJiq3Oca9VRa1OYcFs=; cmtchd=MTc1MjU4MTI3OTAxMg==; news_cryproxy_sync_ok=1; cryproxy_sync_ok=1
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
    cookies = [
        {"name": "zencookie", "value": "8297893231744362383"},
        {"name": "yandexuid", "value": "4525498611744362383"},
        {"name": "zen_session_id", "value": "OhYi0aEfWJ4WyVHhBJ0nitiKfdOSDe1FqYd.1751052297362"},
        {"name": "Session_id", "value": "3:1751198729.5.0.1751198729440:hknTnA:ad22.1.0.0:3.1:366200649.3:1749838046|64:10029481.483364.yhJ_JqWAm1v_d9_VrNWAdgGyXPE"}
    ]
    
    for c in cookies:
        try: driver.add_cookie({**c, "domain": ".dzen.ru", "path": "/"})
        except: pass
    
    # Navigate and upload
    driver.get("https://dzen.ru/profile/editor/id/67fe5ca67c0c2872e1590bec/publications?state=published")
    time.sleep(3)
    
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
    return main_with_path("/workspaces/tools/downloads/tt23131648/1080p/tt23131648/1080p_tt23131648.mp4", "Comssedy Video")

if __name__ == "__main__":
    result = main()
    print(f"Result: {result}")
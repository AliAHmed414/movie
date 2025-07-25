import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, os, re

def setup_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})
    return uc.Chrome(options=options)

def apply_cookies(driver):
    cookie_string = '''
    _statid=01365bdc-fbd8-43eb-badb-844efefc810a; bci=-4749589668578836287; __last_online=1753404052619; __dzbd=false; klos=0; _userIds="910160417777,910080290458"; _sAuth910080290458=XmZL7JeLBXOL1H6q4depZQ4GbP3e_rI_tTeFCJrkhOSzGjwxxQccE5or49Grs5WIvar5DgvVQQXV68UoA6KKNBEZYp1s_ybDKCVFDmDt-p2nK2GottoxBQHSribxBzp96B8hEaImbmLxpO-TMA_5; AUTHCODE=XmZL7JeLBXOL1H6q4depZQ4GbP3e_rI_tTeFCJrkhOSzGjwxxQccE5or49Grs5WIvar5DgvVQQXV68UoA6KKNBEZYp1s_ybDKCVFDmDt-p2nK2GottoxBQHSribxBzp96B8hEaImbmLxpO-TMA_5; msg_conf=24685557567925…eme_mode=DARK; vdt=FUc8gCiQJHfRHFOhvVIao2EUK+ZTd25UuyoSHnZwhAoAAABmC4a4MMmoXetAy+jx6J8h2M0uAggT0dnZB2A+sq4uz2k9T3+VWfPp8r8+zlpoyMpXZoYHxVFnmkgEXkZQww1SjqyqUKcgHFEdNC5hiqKlO71S8v0bFUxhvfl2GLv1FwkluPxTH7Q=; cudr=0; _sAuth910160417777=BZTrPGSJgfmcinxSnbXafZxi4F7IsyhkR5fLDlX5V6KeNH-5OrxoD8slAxOU28_Y1_q6SNG78ZhofR2DkZyBST0_fCMduYL8528NspLD-wptT-VGLEideENCdr2B8sUHyq2IfaeDynoNlmeyTA_5; JSESSIONID=b0c1a3eeb7afab8eb1a8949c1aa545643707f534a84989cd.7d99b795; LASTSRV=ok.ru; viewport=1080; TZD=6.941; TZ=6; TD=941; CDN=
     '''
    for part in cookie_string.strip().split("; "):
        try:
            name, value = part.split("=", 1)
            driver.add_cookie({
                "name": name,
                "value": value,
                "domain": ".ok.ru",
                "path": "/"
            })
        except Exception as e:
            print(f"Could not add cookie {name}: {e}")

def safe_click(driver, element):
    for method in [lambda: element.click(), lambda: driver.execute_script("arguments[0].click();", element)]:
        try: method(); return True
        except: continue
    return False

def find_click(driver, selectors, timeout=10):
    for selector in selectors:
        try:
            element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            if safe_click(driver, element): return True
        except: continue
    return False

def main_with_path(video_path):
    """Modified main function that accepts video path as parameter"""
    if not os.path.exists(video_path): 
        print(f"❌ Video not found: {video_path}")
        return None
    
    driver = setup_driver()
    try:
        # Login
        driver.get("https://ok.ru")
        time.sleep(1)  # Wait for the page to load
        apply_cookies(driver)
        time.sleep(1)  
        driver.get("https://ok.ru/video/manager")
        
        file_input = None
        # Based on the HTML structure, look for the specific file input
        selectors_to_try = [
            ".js-fileapi-input",
            "input.video-upload-input", 
            "input[data-module='VideoUploader']",
            "input[accept*='video']",
            "input[type='file']"
        ]
        
        for selector in selectors_to_try:
            try: 
                file_input = driver.find_element(By.CSS_SELECTOR, selector)
                if file_input.is_displayed():
                    break
                else:
                    file_input = None
            except: 
                continue
        
        if not file_input:
            # Try clicking the upload button first
            upload_button_selectors = [
                ".js-upload-button",
                ".button-pro.js-upload-button", 
                "span.button-pro"
            ]
            for selector in upload_button_selectors:
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if btn.is_displayed():
                        safe_click(driver, btn)
                        time.sleep(1)
                        break
                except:
                    continue
            
            # Try again to find file input
            for selector in selectors_to_try:
                try: 
                    file_input = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except: 
                    continue
        
        if not file_input: 
            raise Exception("File input not found")
        
        file_input.send_keys(video_path)
        print("📤 Upload started...")
        
        # Monitor upload progress
        start_time = time.time()
        timeout = 1800  # 30 minutes
        no_status_warnings = 0
        max_warnings = 5
        
        while (time.time() - start_time) < timeout:
            try:
                # Check for publish button (upload complete)
                for selector in [".js-uploader-publish-link", ".publish-btn", "[data-l*='publish']", "a.video-uploader_ac"]:
                    try:
                        btn = driver.find_element(By.CSS_SELECTOR, selector)
                        if btn.is_displayed() and btn.is_enabled():
                            print("✓ Upload complete")
                            break
                    except: continue
                else:
                    # Check for status/progress
                    status = ""
                    for selector in ["[class*='pb_count']", "[class*='percent']", ".video-uploader_status-tx"]:
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            for el in elements:
                                if el.is_displayed():
                                    text = el.text.strip()
                                    if text and ("%" in text or any(k in text.lower() for k in ["upload", "process", "ready"])):
                                        if text != status:
                                            print(f"📤 {text}")
                                            status = text
                                        break
                        except: pass
                    
                    if not status:
                        no_status_warnings += 1
                        if no_status_warnings <= max_warnings:
                            print(f"⚠️ No status detected, checking... ({no_status_warnings}/{max_warnings})")
                        elif no_status_warnings == max_warnings + 1:
                            print("⚠️ Continuing silently...")
                        
                        if no_status_warnings > 40:  # ~2 minutes without status
                            print("⚠️ Assuming upload completed")
                            break
                    else:
                        no_status_warnings = 0
                    
                    time.sleep(3)
                    continue
                break
            except Exception as e:
                if "failed" in str(e).lower():
                    raise e
                time.sleep(2)
        
        # Publish
        if not find_click(driver, [".js-uploader-publish-link", ".publish-btn", "[data-l*='publish']"], 30):
            try: safe_click(driver, WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.video-uploader_ac:nth-child(1)"))))
            except: raise Exception("Publish button not found")
        
        print("✓ Video published")
        
        # Handle dialog
        try: time.sleep(2); safe_click(driver, driver.find_element(By.XPATH, "//button[contains(text(), 'Нет')]"))
        except: pass
        
        time.sleep(5)
        
        # Get URL
        video_url = None
        video_filename = os.path.splitext(os.path.basename(video_path))[0]  # without .mp4

        # First, try to find from current URL or source
        video_match = re.search(r'/video/(\d{13,})', driver.current_url)
        if video_match:
            video_url = f"https://ok.ru/video/{video_match.group(1)}"
        else:
            for pattern in [r'"videoId":"(\d{13,})"', r'video/(\d{13,})']:
                matches = re.findall(pattern, driver.page_source)
                if matches:
                    video_url = f"https://ok.ru/video/{matches[0]}"
                    break

        # If not found yet, go to profile and look for a match by title
        if not video_url:
            try:
                driver.get("https://ok.ru/profile/910080290458/videos")
                time.sleep(3)

                video_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/video/']")
                for el in video_elements:
                    href = el.get_attribute("href")
                    title_el = el.find_element(By.XPATH, ".//div[contains(@class, 'media-text') or contains(@class, 'video-card_text')]")
                    if video_filename in title_el.text or video_filename in href:
                        video_url = href
                        break
            except Exception as e:
                print("⚠ Error while scanning profile videos:", e)
                video_url = None

        if video_url:
            return video_url
        else:
            print("❌ Failed to get video URL")
            return None
        
    except Exception as e: 
        print(f"Error: {e}")
        return None
    finally: 
        driver.quit()

def main():
    """Original main function for backward compatibility"""
    video_path = "/home/kda/comdy.mp4"
    return main_with_path(video_path)

if __name__ == "__main__": 
    print(f"Result: {main()}")
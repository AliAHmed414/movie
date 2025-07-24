import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, os, re

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
    _statid=01365bdc-fbd8-43eb-badb-844efefc810a; bci=-4749589668578836287; __last_online=1753281524789; __dzbd=false; klos=0; _userIds="910160417777,910080290458"; _sAuth910080290458=YVoMCdxmRuvfPrUUFlqjAUXdtKqajNjTGYLyzQNm3Fs__DCv5pG57x0DTcFC8RDBLgOFRUEhfJEM3hAyiCfT8-3GTWPLY8jph9JbUY8mLHIYUhGbbnWIAztxO9qRUNAFVYp5hCwIEJPGT-z8UA_5; AUTHCODE=YVoMCdxmRuvfPrUUFlqjAUXdtKqajNjTGYLyzQNm3Fs__DCv5pG57x0DTcFC8RDBLgOFRUEhfJEM3hAyiCfT8-3GTWPLY8jph9JbUY8mLHIYUhGbbnWIAztxO9qRUNAFVYp5hCwIEJPGT-z8UA_5; msg_conf=24685557567925…eme_mode=DARK; vdt=FUc8gCiQJHfRHFOhvVIao2EUK+ZTd25UuyoSHnZwhAoAAABmC4a4MMmoXetAy+jx6J8h2M0uAggT0dnZB2A+sq4uz2k9T3+VWfPp8r8+zlpoyMpXZoYHxVFnmkgEXkZQww1SjqyqUKcgHFEdNC5hiqKlO71S8v0bFUxhvfl2GLv1FwkluPxTH7Q=; cudr=0; JSESSIONID=aa32ebdb0be67a46c4161b818a694acb2aa9a47d3e420288.4789b9ba; LASTSRV=ok.ru; viewport=1080; TZD=6.588; TZ=6; TD=588; CDN=; _sAuth910160417777=BZTrPGSJgfmcinxSnbXafZxi4F7IsyhkR5fLDlX5V6KeNH-5OrxoD8slAxOU28_Y1_q6SNG78ZhofR2DkZyBST0_fCMduYL8528NspLD-wptT-VGLEideENCdr2B8sUHyq2IfaeDynoNlmeyTA_5
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
        for selector in ["input[type='file']", "input[accept*='video']", ".js-uploader-input input[type='file']"]:
            try: file_input = driver.find_element(By.CSS_SELECTOR, selector); break
            except: continue
        
        if not file_input:
            find_click(driver, ["button[data-l*='upload']", ".js-uploader-button", "[class*='upload']"], 5)
            time.sleep(1)
            for selector in ["input[type='file']", "input[accept*='video']"]:
                try: file_input = driver.find_element(By.CSS_SELECTOR, selector); break
                except: continue
        
        if not file_input: raise Exception("File input not found")
        
        file_input.send_keys(video_path)
        print("📤 Upload started...")
        
        # Monitor upload progress
        upload_complete = False
        start_time = time.time()
        
        while not upload_complete:
            try:
                # Check for different status messages
                status_elements = driver.find_elements(By.CSS_SELECTOR, ".video-uploader_status-tx")
                
                for status_el in status_elements:
                    if not status_el.is_displayed():
                        continue
                        
                    status_text = status_el.text.strip()
                    
                    if "Queued for download" in status_text:
                        print("⏳ Queued for processing...")
                    elif "Uploaded" in status_text and "%" in status_text:
                        # Extract percentage
                        try:
                            percent_el = status_el.find_element(By.CSS_SELECTOR, ".v-upl-card_pb_count")
                            percentage = percent_el.text.strip()
                            print(f"📤 Uploading: {percentage}%")
                        except:
                            print("📤 Uploading...")
                    elif "Video uploaded and ready for publication" in status_text:
                        print("✓ Video uploaded")
                        upload_complete = True
                        break
                    elif "Video published" in status_text:
                        print("✓ Video published")
                        upload_complete = True
                        break
                    elif "No connection to the Internet" in status_text:
                        print("❌ Connection error detected")
                        raise Exception("Internet connection lost")
                    elif status_el.get_attribute("class") and "js-uploader-error" in status_el.get_attribute("class"):
                        error_text = status_text if status_text else "Unknown upload error"
                        print(f"❌ Upload error: {error_text}")
                        raise Exception(f"Upload failed: {error_text}")
                
                if not upload_complete:
                    time.sleep(2)  # Check every 2 seconds
                    
            except Exception as e:
                if "Upload failed" in str(e) or "Connection error" in str(e):
                    raise e
                # Continue on other exceptions (element not found, etc.)
                time.sleep(1)
        
        if not upload_complete:
            print("⚠️ Upload status unclear, proceeding...")
            time.sleep(5)
        
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
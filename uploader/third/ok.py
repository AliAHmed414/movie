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
        upload_complete = False
        start_time = time.time()
        timeout = 1800  # 30 minutes timeout
        last_status = ""
        no_status_count = 0
        
        while not upload_complete and (time.time() - start_time) < timeout:
            try:
                # Look for specific upload progress indicators
                current_status = ""
                found_status = False
                
                # Check for percentage in upload progress
                try:
                    # Look for percentage indicators
                    percent_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='pb_count'], [class*='percent']")
                    for percent_el in percent_elements:
                        if percent_el.is_displayed():
                            percent_text = percent_el.text.strip()
                            if "%" in percent_text:
                                current_status = f"Uploaded {percent_text}"
                                found_status = True
                                break
                except:
                    pass
                
                # If no percentage found, look for other specific status messages
                if not found_status:
                    try:
                        status_selectors = [
                            ".video-uploader_status-tx",
                            ".v-upl-card_status"
                        ]
                        
                        for selector in status_selectors:
                            status_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            for status_el in status_elements:
                                if status_el.is_displayed():
                                    status_text = status_el.text.strip()
                                    # Only capture relevant status messages
                                    if any(keyword in status_text.lower() for keyword in [
                                        "uploaded", "uploading", "processing", "queued", 
                                        "ready", "complete", "загружен", "обработка"
                                    ]) and len(status_text) < 100:  # Avoid capturing large page content
                                        current_status = status_text
                                        found_status = True
                                        break
                            if found_status:
                                break
                    except:
                        pass
                
                # Check for publish button availability (indicates upload complete)
                publish_selectors = [
                    ".js-uploader-publish-link", 
                    ".publish-btn", 
                    "[data-l*='publish']",
                    "a.video-uploader_ac"
                ]
                publish_available = False
                for selector in publish_selectors:
                    try:
                        pub_btn = driver.find_element(By.CSS_SELECTOR, selector)
                        if pub_btn.is_displayed() and pub_btn.is_enabled():
                            publish_available = True
                            print("✓ Upload complete - publish button available")
                            break
                    except:
                        continue
                
                if publish_available:
                    upload_complete = True
                    break
                
                # Print status if it changed
                if current_status and current_status != last_status:
                    print(f"📤 Status: {current_status}")
                    last_status = current_status
                    no_status_count = 0
                elif not found_status:
                    no_status_count += 1
                
                # Check for completion keywords
                completion_keywords = [
                    "uploaded and ready",
                    "ready for publication", 
                    "video published",
                    "upload complete",
                    "processing complete",
                    "готов к публикации"
                ]
                
                if current_status and any(keyword in current_status.lower() for keyword in completion_keywords):
                    print("✓ Video upload completed")
                    upload_complete = True
                    break
                
                # Check for error keywords
                error_keywords = [
                    "error",
                    "failed",
                    "no connection",
                    "upload interrupted",
                    "ошибка"
                ]
                
                if current_status and any(keyword in current_status.lower() for keyword in error_keywords):
                    print(f"❌ Upload error detected: {current_status}")
                    raise Exception(f"Upload failed: {current_status}")
                
                # If no status found for too long, check if upload might be complete
                if no_status_count > 20:  # No status for over a minute (20 * 3 seconds)
                    print(f"⚠️ No status detected for {no_status_count * 3}s, checking if upload completed...")
                    
                    # Check if we're still on the upload page or moved somewhere else
                    if "video/manager" not in driver.current_url:
                        print("⚠️ Page changed, assuming upload completed")
                        upload_complete = True
                        break
                    
                    # Check if there are any upload-related elements still visible
                    upload_indicators = driver.find_elements(By.CSS_SELECTOR, "[class*='upload'], [class*='progress']")
                    active_uploads = [el for el in upload_indicators if el.is_displayed()]
                    
                    if not active_uploads:
                        print("⚠️ No active upload indicators found, assuming completed")
                        upload_complete = True
                        break
                
                time.sleep(3)  # Check every 3 seconds
                    
            except Exception as e:
                if "Upload failed" in str(e) or "error detected" in str(e):
                    raise e
                # Continue on other exceptions (element not found, etc.)
                print(f"⚠️ Exception during status check: {e}")
                time.sleep(2)
        
        if not upload_complete:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                print(f"⚠️ Upload timeout after {timeout/60:.1f} minutes, proceeding anyway...")
            else:
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
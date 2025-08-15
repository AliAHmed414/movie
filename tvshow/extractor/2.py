import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

EXTENSION_PATH = "/workspaces/codespaces-blank/b/uBOLite"

def get_chrome_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument(f"--load-extension={EXTENSION_PATH}")
    chrome_options.add_argument(f"--disable-extensions-except={EXTENSION_PATH}")
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd("Network.enable", {})
    return driver

def extract_media_urls(id,s,e):
    driver = get_chrome_driver()
    m3u8_urls = set()
    vtt_urls = set()

    def handle_performance_logs():
        """Check Chrome DevTools logs for media URLs."""
        for entry in driver.get_log("performance"):
            try:
                msg = json.loads(entry["message"])["message"]
                if msg.get("method") in ["Network.requestWillBeSent", "Network.responseReceived"]:
                    url = msg["params"].get("request", {}).get("url") or msg["params"].get("response", {}).get("url")
                    if not url:
                        continue
                    if ".m3u8" in url:
                        m3u8_urls.add(url)
                    elif ".vtt" in url:
                        vtt_urls.add(url)
            except Exception:
                pass

    try:
        time.sleep(3)
        driver.get("chrome://extensions/")
        driver.save_screenshot("extensions.png")
        driver.get(f"https://player.videasy.net/tv/{id}/{s}/{e}")
        time.sleep(2)  # equivalent to waitUntil: 'networkidle2'

        selectors = [
            "#fixed-container > div.flex.flex-col.items-center.gap-y-3.title-year > button",
            "button"
        ]

        # Click the first visible selector
        for selector in selectors:
            try:
                btn = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    break
            except:
                pass

        # Wait for both m3u8 and vtt URLs
        for _ in range(5):
            handle_performance_logs()
            if m3u8_urls and vtt_urls:
                break
            time.sleep(3)

        result = {
            "m3u8_urls": list(m3u8_urls),
            "vtt_urls": list(vtt_urls),
            "total_m3u8": len(m3u8_urls),
            "total_vtt": len(vtt_urls)
        }

        return result

    finally:
        driver.quit()

if __name__ == "__main__":
    data = extract_media_urls('1399',1,1)
    print(json.dumps(data, indent=2))
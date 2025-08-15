import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

EXTENSION_PATH = "/workspaces/codespaces-blank/b/uBOLite"


def get_chrome_driver():
    caps = DesiredCapabilities.CHROME.copy()
    caps["goog:loggingPrefs"] = {"performance": "ALL"} 

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--load-extension={EXTENSION_PATH}")
    chrome_options.add_argument(f"--disable-extensions-except={EXTENSION_PATH}")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--start-maximized")

    # Merge caps into options
    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd("Network.enable", {})
    return driver



def extract_m3u8_urls(video_id, season, episode):
    driver = get_chrome_driver()
    m3u8_urls = []

    # Listen to requests via CDP
    def capture_request(params):
        url = params.get("request", {}).get("url", "")
        if ".m3u8" in url:
            print("Found M3U8:", url)
            m3u8_urls.append(url)

    driver.request_interceptor = None  # Placeholder, Selenium doesn't natively support this
    driver.execute_cdp_cmd("Network.setRequestInterception", {
        "patterns": [{"urlPattern": "*", "resourceType": "Media", "interceptionStage": "Request"}]
    })

    # Hack: use event listener via polling
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Network.clearBrowserCache", {})

    # Go to extensions page
    # time.sleep(3)
    # driver.get("chrome://extensions/")
    # driver.save_screenshot("extensions.png")

    # Navigate to video page
    url = f"https://multiembed.mov/?video_id={video_id}&s={season}&e={episode}"
    print("Navigating to:", url)
    driver.get(url)
    time.sleep(2)

    # Click play button
    try:
        play_button = driver.find_element(By.XPATH, "/html/body/div[2]/div/div/div[3]")
        play_button.click()
        print("Play button clicked successfully")
    except NoSuchElementException:
        print("Play button not found, trying CSS selector...")
        try:
            driver.find_element(By.CSS_SELECTOR,
                "body > div.main-loader.captcha.fullpage-loader > div > div > div.play-button"
            ).click()
        except Exception as e:
            print("CSS selector also failed:", str(e))
    except ElementClickInterceptedException:
        print("Play button was not clickable")

    # driver.save_screenshot("page_loaded.png")
    # time.sleep(1)

    # Click file2 trigger
    try:
        trigger = driver.find_element(By.CSS_SELECTOR, "div:nth-child(3)")
        trigger.click()
        print("File2 trigger clicked successfully")
    except NoSuchElementException:
        print("File2 trigger not found")
    except ElementClickInterceptedException:
        print("File2 trigger click failed")

    time.sleep(3)

    # Pull captured network logs
    logs = driver.get_log("performance")
    for entry in logs:
        try:
            msg = json.loads(entry["message"])["message"]
            if msg["method"] == "Network.requestWillBeSent":
                request_url = msg["params"]["request"]["url"]
                if ".m3u8" in request_url:
                    m3u8_urls.append(request_url)
        except Exception:
            pass

    driver.quit()
    print(f"Total M3U8 URLs found: {len(m3u8_urls)}")
    return list(set(m3u8_urls))

if __name__ == "__main__":
    data = extract_m3u8_urls("tt1592154", 1, 1)
    print("Final result:", data)
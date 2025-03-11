from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def get_ktc_risers_and_fallers():
    # Setup Chrome Options
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--headless")  # Run in headless mode (no UI)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--log-level=3")

    # Initialize WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        url = "https://keeptradecut.com/dynasty-rankings"
        driver.get(url)

        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "rankings-page")))

        # Check if KTC Comparison is present
        try:
            comparison_modal = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "comparison-wrapper")))
            print("[INFO] KTC Comparison prompt detected. Attempting to bypass...")

            # Click "I don't know all these players" option
            dont_know_button = driver.find_element(By.XPATH, "//button[contains(text(), \"I don't know\")]")
            dont_know_button.click()
            print("[INFO] Clicked 'I don't know all of these players' to skip.")

            # Wait for rankings page again
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "rankings-page")))

        except Exception:
            print("[INFO] No KTC Comparison prompt detected. Proceeding...")

        # Scroll down to ensure dynamic content loads
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)  # Allow time for JavaScript to load elements

        # Extract Risers
        riser_elements = driver.find_elements(By.XPATH, "//div[@class='riser insightWrapper']//div[@class='topFivePlayer']")
        risers = [
            {
                "name": el.find_element(By.CLASS_NAME, "topFiveName").text.strip(),
                "value": el.find_element(By.CLASS_NAME, "topFiveValue").text.strip()
            }
            for el in riser_elements
        ]

        # Extract Fallers
        faller_elements = driver.find_elements(By.XPATH, "//div[@class='faller insightWrapper']//div[@class='topFivePlayer']")
        fallers = [
            {
                "name": el.find_element(By.CLASS_NAME, "topFiveName").text.strip(),
                "value": el.find_element(By.CLASS_NAME, "topFiveValue").text.strip()
            }
            for el in faller_elements
        ]

        # Print results
        print("\n🔥 **Top 5 Risers (30 Days)** 🔥")
        for riser in risers:
            print(f"{riser['name']} - {riser['value']}")

        print("\n❄️ **Top 5 Fallers (30 Days)** ❄️")
        for faller in fallers:
            print(f"{faller['name']} - {faller['value']}")

        return {"risers": risers, "fallers": fallers}

    except Exception as e:
        print("Error:", str(e))
        return {"risers": [], "fallers": []}

    finally:
        driver.quit()

# Run the function
if __name__ == "__main__":
    data = get_ktc_risers_and_fallers()
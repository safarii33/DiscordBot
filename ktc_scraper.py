from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager import web_driver_manager
import time

def get_ktc_risers_and_fallers():

    # Initialize WebDriver
    driver = web_driver_manager.get_driver()
    url = "https://keeptradecut.com/dynasty-rankings"
    driver.get(url)

    # Handle KTC pop-up if needed
    try:
        comparison_modal = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "comparison-wrapper")))
        dont_know_button = driver.find_element(By.XPATH, "//button[contains(text(), \"I don't know\")]")
        dont_know_button.click()
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "rankings-page")))
    except Exception:
        pass  # No pop-up detected

    # Scroll down and wait for content
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)

    # Extract Risers
    risers = [
        {
            "name": el.find_element(By.CLASS_NAME, "topFiveName").text.strip(),
            "value": el.find_element(By.CLASS_NAME, "topFiveValue").text.strip()
        }
        for el in driver.find_elements(By.XPATH, "//div[@class='riser insightWrapper']//div[@class='topFivePlayer']")
    ]

    # Extract Fallers
    fallers = [
        {
            "name": el.find_element(By.CLASS_NAME, "topFiveName").text.strip(),
            "value": el.find_element(By.CLASS_NAME, "topFiveValue").text.strip()
        }
        for el in driver.find_elements(By.XPATH, "//div[@class='faller insightWrapper']//div[@class='topFivePlayer']")
    ]

    return {"risers": risers, "fallers": fallers}

# Run the function
if __name__ == "__main__":
    data = get_ktc_risers_and_fallers()
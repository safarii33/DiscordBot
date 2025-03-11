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

        # Wait for the rankings page to load
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "rankings-page")))

        # Handle KTC comparison prompt if it appears
        try:
            comparison_modal = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "comparison-wrapper")))
            print("[INFO] KTC Comparison prompt detected. Attempting to bypass...")

            dont_know_button = driver.find_element(By.XPATH, "//button[contains(text(), \"I don't know\")]")
            dont_know_button.click()
            print("[INFO] Clicked 'I don't know all of these players' to skip.")

            # Wait for rankings page again
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "rankings-page")))

        except Exception:
            print("[INFO] No KTC Comparison prompt detected. Proceeding...")

        # Scroll to load elements
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        def extract_player_data(section_xpath):
            """Extracts player names and values from the section"""
            player_elements = driver.find_elements(By.XPATH, section_xpath)
            players = []

            for el in player_elements:
                try:
                    name = el.find_element(By.CLASS_NAME, "topFiveName").text.strip()
                    value = el.find_element(By.CLASS_NAME, "topFiveValue").text.strip()
                    players.append({
                        "name": name,
                        "initial_value": value,
                        "url": None  # Will populate later
                    })
                except Exception as e:
                    print(f"[WARNING] Could not extract data for a player: {e}")
            
            return players

        # Extract Risers and Fallers
        risers = extract_player_data("//div[@class='riser insightWrapper']//div[@class='topFivePlayer']")
        fallers = extract_player_data("//div[@class='faller insightWrapper']//div[@class='topFivePlayer']")

        # Extract URLs separately from .insight-link
        insight_links = driver.find_elements(By.CLASS_NAME, "insight-link")
        insight_urls = [link.get_attribute("href") for link in insight_links]

        # Match URLs to players in order
        for i, player in enumerate(risers + fallers):
            if i < len(insight_urls):  # Ensure we don’t exceed available links
                player["url"] = insight_urls[i]

        # Function to fetch new Dynasty Value from a player's page
        def fetch_dynasty_value(player):
            """Navigates to the player's page and retrieves the latest Dynasty Value"""
            if not player["url"]:
                print(f"[ERROR] No URL found for {player['name']}. Skipping...")
                return

            try:
                driver.get(player["url"])
                wait.until(EC.presence_of_element_located((By.ID, "player-details-main")))

                # Get the latest Dynasty Value
                dynasty_value_element = driver.find_element(By.XPATH, "//div[@class='block-value main-value']/p[@class='block-value']")
                dynasty_value = dynasty_value_element.text.strip()

                player["new_dynasty_value"] = dynasty_value
                print(f"[SUCCESS] {player['name']} - New Dynasty Value: {dynasty_value}")

            except Exception as e:
                print(f"[ERROR] Failed to retrieve dynasty value for {player['name']}: {e}")
                player["new_dynasty_value"] = "N/A"

        # Visit each player's page to fetch new Dynasty Value
        for player in risers + fallers:
            fetch_dynasty_value(player)

        # Print results
        print("\n🔥 **Top 5 Risers (30 Days)** 🔥")
        for riser in risers:
            print(f"{riser['name']} - Initial: {riser['initial_value']} → New: {riser['new_dynasty_value']}")

        print("\n❄️ **Top 5 Fallers (30 Days)** ❄️")
        for faller in fallers:
            print(f"{faller['name']} - Initial: {faller['initial_value']} → New: {faller['new_dynasty_value']}")

        return {"risers": risers, "fallers": fallers}

    except Exception as e:
        print("Error:", str(e))
        return {"risers": [], "fallers": []}

    finally:
        driver.quit()

# Run the function
if __name__ == "__main__":
    data = get_ktc_risers_and_fallers()

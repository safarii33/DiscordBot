# webdriver_manager.py
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

class WebDriverManager:
    def __init__(self):
        """Initialize WebDriver once and keep it open."""
        self.chrome_options = Options()
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_argument("--ignore-certificate-errors")
        self.chrome_options.add_argument("--headless")  # Run in headless mode (no UI)
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--log-level=3")

        self.service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
    
    def get_driver(self):
        """Return the active WebDriver instance."""
        return self.driver
    
    def quit_driver(self):
        """Close WebDriver on shutdown."""
        self.driver.quit()

# Initialize WebDriver globally
web_driver_manager = WebDriverManager()

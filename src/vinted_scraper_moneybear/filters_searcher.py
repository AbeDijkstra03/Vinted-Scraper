from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# Set up the WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Function to select language
def select_language(language='United Kingdom'):
    # Adjust the selector based on the page's HTML structure
    language_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Where do you live?')]")
    language_button.click()
    time.sleep(1)  # Allow the dropdown to appear

    # Select the desired language
    language_option = driver.find_element(By.XPATH, f"//button[contains(text(), '{language}')]")
    language_option.click()
    time.sleep(2)  # Allow the page to reload with the selected language

# Function to extract category labels
def extract_category_labels(url):
    driver.get(url)
    time.sleep(5)  # Allow the page to load

    # Select language if necessary
    select_language()

    # Locate the labels on the page
    labels = driver.find_elements(By.CLASS_NAME, 'category-item')  # Adjust the selector based on the page's HTML structure
    category_labels = [label.text for label in labels if label.text != '']  # Extract the text of each label

    return category_labels

# List of Vinted category URLs
categories = [
    'https://www.vinted.com/catalog/1904-women',
    'https://www.vinted.com/catalog/5-men',
    'https://www.vinted.com/catalog/2993-designer',
    'https://www.vinted.com/catalog/1193-kids',
    'https://www.vinted.com/catalog/1918-home',
    'https://www.vinted.com/catalog/2994-electronics'
]

# Extract labels for each category
for url in categories:
    print(f"Extracting labels from {url}...")
    labels = extract_category_labels(url)
    print(f"Labels: {labels}\n")

# Close the WebDriver
driver.quit()

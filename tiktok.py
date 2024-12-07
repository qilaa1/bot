import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
import pickle

class TikTokBot:
    
    def __init__(self, driver):
        self.driver = driver

    def click(self, path):
        try:
            element = self.driver.find_element(By.XPATH, path)
            element.click()
        except Exception as e:
            print(f"Error clicking element: {e}")

    def type_text(self, path, text):
        try:
            element = self.driver.find_element(By.XPATH, path)
            for char in text:
                element.send_keys(char)
                time.sleep(0.05)
        except Exception as e:
            print(f"Error typing text: {e}")
            
    def comment(self, path, text):
        try:
            element = self.driver.find_element(By.XPATH, path)
            for char in text:
                element.send_keys(char)
                time.sleep(0.05)
            element.send_keys(Keys.ENTER)
        except Exception as e:
            print(f"Error commenting: {e}")

def save_cookies(cookies, filename):
    """Save cookies to a file using pickle."""
    try:
        with open(filename, 'wb') as file:
            pickle.dump(cookies, file)
        print(f"Cookies saved successfully to {filename}.")
    except Exception as e:
        print(f"Error saving cookies: {e}")

def load_cookies(filename):
    """Load cookies from a file using pickle."""
    try:
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            with open(filename, 'rb') as file:
                return pickle.load(file)
        else:
            print(f"No valid cookie file found: {filename}")
            return None
    except Exception as e:
        print(f"Error loading cookies: {e}")
        return None

def login(driver, email, password, cookies=None):
    """Login to TikTok using either cookies or manual login."""
    bot = TikTokBot(driver)
    
    # Navigate to TikTok homepage
    driver.get("https://www.tiktok.com")

    # Check if cookies are available for login
    if cookies:
        # Load cookies into the browser
        for cookie in cookies:
            driver.add_cookie(cookie)
        print("Cookies loaded. Skipping login...")
        driver.refresh()  # Refresh the page to apply cookies
        
        # Wait for the page to reload and check for a successful login
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//div[@class="user-info"]'))  # Element only visible after login
            )
            print("Cookies loaded and login successful!")
            return  # Skip manual login if cookies are valid and login is successful
        except Exception as e:
            print(f"Error after loading cookies: {e}")
            print("Login failed or cookies invalid, proceed with manual login.")
            input("Type 'ok' after you've manually logged in: ")

    # No cookies found, proceed with manual login
    driver.get('https://www.tiktok.com/login/phone-or-email/email')

    # Ensure the login page is loaded
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//input[@type="text"]'))
    )

    # Type email and password
    bot.type_text('//input[@type="text"]', email)
    time.sleep(1)
    bot.type_text('//input[@type="password"]', password)
    time.sleep(1)

    # Submit login form
    bot.click('//button[@type="submit"]')
    time.sleep(5)

    # Wait for login to complete (look for an element that is only visible after login)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//div[@class="user-info"]'))  # Modify with actual element after login
        )
        print("Login successful!")
    except Exception as e:
        print("Automatic login failed. Please log in manually.")
        input("Type 'ok' after you've manually logged in: ")

    # Save cookies after manual login
    cookies = driver.get_cookies()
    save_cookies(cookies, 'tiktok_cookies.pkl')
    print("Login successful. Credentials saved for future sessions.")

def get_video_and_comment(driver, video_url, keyword_list=["harga", "produk", "diskon", "cara beli"]):
    """Get a video from the URL and post a reply to comments based on keywords."""
    # Go to the provided video URL
    driver.get(video_url)
    print(f"Video URL opened: {video_url}")

    # Wait for the comment section button to appear
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//div[@role='button' and contains(text(), 'Comment')]"))
    )
    
    # Scroll to ensure comments are loaded
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)  # Wait for page to load

    # Click to open the comments
    comment_button_xpath = "//div[@role='button' and contains(text(), 'Comment')]"  # Adjust as needed
    comment_button = driver.find_element(By.XPATH, comment_button_xpath)
    comment_button.click()
    time.sleep(5)  # Wait for the comment section to load

    # Get all the comments
    comments_elements = driver.find_elements(By.XPATH, '//div[@role="comment"]')

    # Print the number of comments found
    print(f"Found {len(comments_elements)} comments.")

    if not comments_elements:
        print("No comments found.")
        return

    for comment_element in comments_elements:
        try:
            comment_text = comment_element.find_element(By.XPATH, './/p').text.lower()
            username = comment_element.find_element(By.XPATH, './/a').text.strip()

            print(f"Found comment by @{username}: {comment_text}")

            # Check if the comment contains any of the keywords
            if any(keyword in comment_text for keyword in keyword_list):
                # Reply to the comment

                # Find and click the reply button
                reply_button = comment_element.find_element(By.XPATH, './/button[contains(@class, "reply-button-class")]')  # Adjust class
                reply_button.click()

                time.sleep(1)  # Wait for the reply box to appear

                # Find the reply textbox
                response_box = driver.find_element(By.XPATH, '//div[@role="textbox"]')
                response_box.click()

                # Wait for the reply textbox to be clickable
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//div[@role="textbox"]'))
                )

                # Type the reply
                response = f"@{username} Terima kasih atas komentarnya! {comment_text}"
                response_box.send_keys(response)
                response_box.send_keys(Keys.RETURN)  # Send the reply

                print(f"Replied to @{username} with: {response}")
                time.sleep(2)

        except Exception as e:
            print(f"Error while processing comment: {e}")

def run_bot():
    """Main bot function that handles login, posting comments, following users, etc."""
    email = "yiyayuuu"  # Replace with your TikTok email
    password = "FUCKITLIFE1."  # Replace with your TikTok password

    # Load cookies for login
    cookies = load_cookies('tiktok_cookies.pkl')

    # Initialize WebDriver
    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()

    # Login with cookies or manually
    login(driver, email, password, cookies)

    # Set the video URL
    video_url = "https://www.tiktok.com/@yiyayuuu/video/7402587657584315653"  # Replace with the actual video URL

    try:
        get_video_and_comment(driver, video_url)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

# Run the bot
if __name__ == "__main__":
    run_bot()

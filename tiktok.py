import time
import os
import pickle
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from transformers import BertTokenizer, BertForSequenceClassification
import torch
import warnings

warnings.filterwarnings("ignore", message=".*weights.*not initialized.*")

def configure_driver():
    """Configure the Chrome WebDriver with mobile emulation."""
    options = Options()
    options.add_argument('--log-level=3')  # Suppress logs
    options.add_argument(f"--user-data-dir={os.getcwd()}\\profile")  # Save session
    mobile_emulation = {
        "userAgent": "Mozilla/5.0 (Linux; Android 4.2.1; en-us; Nexus 5 Build/JOP40D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/90.0.1025.166 Mobile Safari/535.19"
    }
    options.add_experimental_option("mobileEmulation", mobile_emulation)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
    )
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_window_position(0, 0)
    driver.set_window_size(414, 936)  # Mobile screen resolution
    return driver


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
    driver.get("https://www.tiktok.com")

    if cookies:
        # Load cookies into the browser
        for cookie in cookies:
            driver.add_cookie(cookie)
        print("Cookies loaded. Skipping login...")
        driver.refresh()
    else:
        print("No cookies found. Proceeding with manual login.")
        driver.get('https://www.tiktok.com/login/phone-or-email/email')

        # Wait for login page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@type="text"]'))
        )

        # Type email and password
        driver.find_element(By.XPATH, '//input[@type="text"]').send_keys(email)
        time.sleep(1)
        driver.find_element(By.XPATH, '//input[@type="password"]').send_keys(password)
        time.sleep(1)

        # Submit login form
        driver.find_element(By.XPATH, '//button[@type="submit"]').click()
        time.sleep(5)

    # Save cookies after successful login
    cookies = driver.get_cookies()
    save_cookies(cookies, 'tiktok_cookies.pkl')
    print("Login successful and cookies saved.")


def scroll_comments(driver, container_xpath, max_scroll=10, pause_time=2):
    """
    Scrolls through the comment container to load more comments.
    
    Args:
        driver: Selenium WebDriver instance.
        container_xpath: XPath for the comment container.
        max_scroll: Maximum number of scroll attempts.
        pause_time: Pause time between scrolls (in seconds).
    """
    try:
        container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, container_xpath))
        )
        last_height = driver.execute_script("return arguments[0].scrollHeight", container)
        scroll_count = 0
        
        while scroll_count < max_scroll:
            # Scroll to the bottom of the container
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", container)
            time.sleep(pause_time)
            new_height = driver.execute_script("return arguments[0].scrollHeight", container)
            
            if new_height == last_height:  # No new comments loaded
                print("No more comments to load.")
                break
            
            last_height = new_height
            scroll_count += 1
            print(f"Scrolled {scroll_count} times.")
    except Exception as e:
        print(f"Error while scrolling comments: {e}")


import random
def analyze_comment(comment_text, tokenizer, model):
    """Analyze a comment using a BERT model."""
    inputs = tokenizer(comment_text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    logits = outputs.logits
    predictions = torch.argmax(logits, dim=-1)
    return predictions.item()


def generate_response(comment_text, username):
    """Generate a response based on the content of the comment."""
    if "harga" in comment_text:
        return f"@{username} Produk kami mulai dari Rp100.000. Untuk detail lebih lanjut, silakan hubungi kami!"
    elif "produk" in comment_text:
        return f"@{username} Kami menawarkan produk berkualitas tinggi dengan berbagai pilihan. Untuk informasi lebih lanjut, cek deskripsi produk!"
    elif "cara beli" in comment_text:
        return f"@{username} Anda dapat membeli produk kami dengan mengklik tombol 'Beli Sekarang' atau menghubungi kontak yang tersedia!"
    else:
        return f"@{username} Terima kasih atas komentarnya! Kami akan segera memberikan informasi lebih lanjut."
def is_relevant_comment(comment_text, prediction, keyword_list):
    """
    Determine if a comment is relevant based on keywords or BERT prediction.
    
    Args:
        comment_text: The text of the comment.
        prediction: The prediction from the BERT model (1 = relevant).
        keyword_list: List of keywords to check in the comment.

    Returns:
        True if the comment is relevant, False otherwise.
    """
    # Check if comment contains any keyword
    contains_keyword = any(keyword in comment_text for keyword in keyword_list)

    # Check if BERT prediction indicates relevance (1 = relevant)
    is_relevant = prediction == 1

    # Return true if either condition is met
    return contains_keyword or is_relevant


def monitor_and_reply(driver, video_url, tokenizer, model):
    """
    Monitor a video comment section and reply to new comments.
    
    Args:
        driver: Selenium WebDriver instance.
        video_url: URL of the TikTok video to monitor.
        tokenizer: BERT tokenizer.
        model: BERT model for sequence classification.
    """
    replied_comments = set()  # Track replied comments
    keyword_list = ["harga", "produk", "cara beli", "diskon"]  # Define relevant keywords

    while True:
        try:
            # Reload the video page
            driver.get(video_url)
            print(f"Opened video URL: {video_url}")

            # Pause video
            try:
                video_xpath = '//video'
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, video_xpath)))
                driver.execute_script("document.querySelector('video').pause()")
                print("Video paused.")
            except Exception as e:
                print(f"Error while interacting with video: {e}")
                continue

            # Open comment section
            try:
                comment_button_xpath = '//*[@id="app"]/div/div[2]/div/div[1]/div/div/div/div[1]/div/div[2]/div/div[1]/div/div[2]'
                comment_button = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, comment_button_xpath))
                )
                comment_button.click()
                print("Comment button clicked. Pop-up opened.")
                time.sleep(2)  # Wait for the comment section to load
            except Exception as e:
                print(f"Error while clicking comment button: {e}")
                continue

            # Process comments
            comments_xpath = '//div[contains(@class, "css-147ti1k-DivCommentListContainer")]/div'
            comments_elements = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, comments_xpath)))
            print(f"Found {len(comments_elements)} comments.")

            for idx, comment_element in enumerate(comments_elements):
                try:
                    # Scroll to the comment to make it visible
                    driver.execute_script("arguments[0].scrollIntoView(true);", comment_element)
                    time.sleep(1)

                    # Get comment text
                    try:
                        comment_text_element = comment_element.find_element(
                            By.XPATH, './/p[contains(@data-e2e, "comment-level-1")] | .//div[@data-e2e="comment-text"]'
                        )
                        comment_text = comment_text_element.text.lower()
                        print(f"Comment text at index {idx + 1}: {comment_text}")
                    except Exception as e:
                        print(f"No comment text found at index {idx + 1}.")
                        continue

                    # Get username
                    try:
                        username_element = comment_element.find_element(
                            By.XPATH, './/span[contains(@data-e2e, "comment-username-1")]'
                        )
                        username = username_element.text.strip()
                        print(f"Username at index {idx + 1}: {username}")
                    except Exception as e:
                        username = "user"
                        print(f"Could not locate username for comment at index {idx + 1}.")

                    # Skip comments that were already replied to
                    if comment_text in replied_comments:
                        print(f"Already replied to comment at index {idx + 1}. Skipping...")
                        continue

                    # Analyze the comment using the model
                    prediction = analyze_comment(comment_text, tokenizer, model)
                    print(f"Model prediction for comment: {prediction}")

                    # Check if the comment is relevant
                    if not is_relevant_comment(comment_text, prediction, keyword_list):
                        print(f"Comment at index {idx + 1} is not relevant. Skipping...")
                        continue

                    # Generate response
                    response = generate_response(comment_text, username)

                    # Click on the comment text to activate the reply box
                    try:
                        comment_text_element.click()
                        print(f"Clicked on comment text to open reply box at index {idx + 1}.")
                        time.sleep(2)  # Wait for the reply box to appear
                    except Exception as e:
                        print(f"Failed to click comment text at index {idx + 1}: {e}")
                        continue

                    # Reply to the comment
                    try:
                        reply_box_xpath = '//div[contains(@class, "DraftEditor-root")]//div[@contenteditable="true"]'
                        reply_box = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, reply_box_xpath))
                        )
                        reply_box.send_keys(response)
                        print(f"Typed response for @{username}: {response}")

                        post_button_xpath = '//div[contains(@class, "css-qv0b7z-DivPostButton")]'
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, post_button_xpath))).click()
                        print(f"Replied to @{username}.")
                        replied_comments.add(comment_text)  # Mark this comment as replied
                        time.sleep(random.randint(5, 10))  # Random delay
                    except Exception as e:
                        print(f"Error replying to @{username}: {e}")
                        continue

                except Exception as e:
                    print(f"Error processing comment at index {idx + 1}: {e}")

            print("Reloading page to check for new comments...")
            time.sleep(15)  # Wait before reloading to ensure all comments are processed
        except Exception as e:
            print(f"Error in main loop: {e}")
            break

def run_bot():
    """Run the TikTok bot."""
    video_url = "https://www.tiktok.com/@yiyayuuu/video/7402587657584315653"

    # Load tokenizer and model for BERT
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    model = BertForSequenceClassification.from_pretrained("bert-base-uncased", num_labels=2)

    # Configure WebDriver
    driver = configure_driver()

    # Start monitoring and replying
    monitor_and_reply(driver, video_url, tokenizer, model)


if __name__ == "__main__":
    run_bot()
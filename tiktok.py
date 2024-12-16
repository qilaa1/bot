import time
import os
import pickle
import json
import re
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from transformers import BertTokenizer, BertForSequenceClassification
import torch
import warnings

warnings.filterwarnings("ignore", message=".*weights.*not initialized.*")

# === CONFIGURE DRIVER ===
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

# === COOKIE MANAGEMENT ===
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

# === REPLIED COMMENTS MANAGEMENT ===
def load_replied_comments(filename="replied_comments.json"):
    """Load the list of replied comments from a JSON file."""
    if os.path.exists(filename):
        with open(filename, "r") as file:
            try:
                return json.load(file)  # Load as list of dict
            except json.JSONDecodeError:
                return []  # Return empty list if file is invalid
    return []

def save_replied_comments(replied_comments, filename="replied_comments.json"):
    """Save the list of replied comments to a JSON file."""
    with open(filename, "w") as file:
        json.dump(replied_comments, file, indent=2)
    print("Replied comments saved.")
 
def is_already_replied(username, comment_text, replied_comments):
    """
    Check if the given username and comment_text combination is already in replied comments.
    """
    for replied in replied_comments:
        if replied["username"] == username and replied["comment"] == comment_text:
            return True
    return False

def normalize_comment(comment_text):
    """Normalize comment text by removing dynamic parts like timestamps."""
    return re.sub(r'\d+[a-z]+ ago', '', comment_text).strip()

# === LOGIN MANAGEMENT ===
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

# === COMMENT PROCESSING ===
def analyze_comment(comment_text, tokenizer, model):
    """
    Detect the category (harga, jam buka, cara beli) or analyze sentiment using BERT.
    Returns:
        - category: 'harga', 'jam_buka', 'cara_beli', or 'sentimen'
        - sentiment: None if category detected, else 0, 1, or 2
    """
    # Deteksi kategori menggunakan keyword
    if any(keyword in comment_text for keyword in ["harga", "berapa harga"]):
        return "harga", None
    elif any(keyword in comment_text for keyword in ["jam buka", "kapan buka", "buka jam berapa", "buka dari jam", "besok buka", "hari ini buka"]):
        return "jam_buka", None
    elif any(keyword in comment_text for keyword in ["cara beli", "beli gimana", "beli dimana"]):
        return "cara_beli", None

    # Analisis sentimen jika tidak ada kategori
    inputs = tokenizer(comment_text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    predictions = torch.argmax(outputs.logits, dim=-1).item()

    # Sentimen mapping
    return "sentimen", predictions

def generate_response(category, sentiment, username):
    """
    Generate a response based on detected category or sentiment.
    """
    # Respons kategori spesifik
    if category == "harga":
        return f"@{username} Untuk harga, kami memiliki berbagai pilihan mulai dari Rp100.000. Silakan cek deskripsi untuk detail lebih lanjut!"
    elif category == "jam_buka":
        return f"@{username} Toko kami buka setiap hari dari pukul 08:00 hingga 20:00. Jangan ragu untuk berkunjung ya!"
    elif category == "cara_beli":
        return f"@{username} Anda dapat membeli produk kami melalui tombol 'Beli Sekarang' atau hubungi kontak yang tersedia."

    # Respons berdasarkan sentimen
    if category == "sentimen":
        if sentiment == 0:  # Negative
            return f"@{username} Kami sangat menyesal atas pengalaman buruk Anda. Kami akan berusaha meningkatkan layanan kami ke depannya. Jika ada masalah, silakan hubungi kami."
        elif sentiment == 1:  # Neutral
            return f"@{username} Terima kasih atas komentarnya! Jangan ragu untuk menghubungi kami jika ada pertanyaan lebih lanjut."
        elif sentiment == 2:  # Positive
            return f"@{username} Terima kasih banyak atas dukungannya! Kami senang mendengar Anda puas dengan layanan kami."

    # Respons fallback
    return f"@{username} Terima kasih atas komentarnya! Kami selalu siap membantu Anda."

def is_relevant_comment(comment_text, prediction, keyword_list):
    """
    Determine if a comment is relevant based on keywords or BERT prediction.
    """
    contains_keyword = any(keyword in comment_text for keyword in keyword_list)
    is_relevant = prediction == 1
    return contains_keyword or is_relevant

# === MONITOR AND REPLY ===
def monitor_and_reply(driver, video_url, tokenizer, model):
    """
    Monitor a video comment section and reply to new comments.
    """
    replied_comments = load_replied_comments()  # Load comments as list of dict
    print(f"Loaded replied comments: {replied_comments}")
    keyword_list = ["harga", "produk", "cara beli", "diskon"]  # Keyword relevan

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
                time.sleep(2)
            except Exception as e:
                print(f"Error while clicking comment button: {e}")
                continue

            # Process comments
            comments_xpath = '//div[contains(@class, "css-147ti1k-DivCommentListContainer")]/div'
            comments_elements = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, comments_xpath)))
            print(f"Found {len(comments_elements)} comments.")

            for idx, comment_element in enumerate(comments_elements):
                try:
                    # Ambil teks komentar
                    comment_text_element = comment_element.find_element(
                        By.XPATH, './/p[contains(@data-e2e, "comment-level-1")] | .//div[@data-e2e="comment-text"]'
                    )
                    comment_text = comment_text_element.text.lower()
                    normalized_comment = normalize_comment(comment_text)

                    # Ambil username
                    username_element = comment_element.find_element(
                        By.XPATH, './/span[contains(@data-e2e, "comment-username-1")]'
                    )
                    username = username_element.text.strip()

                    # Lewati komentar yang sudah dibalas
                    if is_already_replied(username, normalized_comment, replied_comments):
                        print(f"Already replied to @{username}'s comment at index {idx + 1}. Skipping...")
                        continue

                    # Analisis komentar
                    category, sentiment = analyze_comment(normalized_comment, tokenizer, model)

                    # Generate response
                    response = generate_response(category, sentiment, username)
                    print(f"Replying to @{username}: {response}")

                    # Reply ke komentar
                    comment_text_element.click()
                    time.sleep(2)
                    reply_box_xpath = '//div[@contenteditable="true"]'
                    reply_box = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, reply_box_xpath))
                    )
                    reply_box.send_keys(response)
                    post_button_xpath = '//div[contains(@class, "css-qv0b7z-DivPostButton")]'
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, post_button_xpath))).click()

                    # Simpan komentar yang sudah dibalas dengan username dan teks komentar
                    replied_comments.append({"username": username, "comment": normalized_comment})
                    save_replied_comments(replied_comments)
                    time.sleep(random.randint(5, 10))  # Delay random

                except Exception as e:
                    print(f"Error processing comment at index {idx + 1}: {e}")
            
            print("Reloading page to check for new comments...")
            time.sleep(30)  # Delay sebelum reload

        except Exception as e:
            print(f"Error in main loop: {e}")
            break


# === RUN BOT ===
def run_bot():
    """Run the TikTok bot."""
    video_url = "https://www.tiktok.com/@yiyayuuu/video/7402587657584315653"
    model_path = r"F:\TikTok-Bot-Automation\indobert_model"
    tokenizer = BertTokenizer.from_pretrained(model_path)
    model = BertForSequenceClassification.from_pretrained(model_path, num_labels=3)
    driver = configure_driver()
    monitor_and_reply(driver, video_url, tokenizer, model)

if __name__ == "__main__":
    run_bot()

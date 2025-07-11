import os
import time
import boto3
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tempfile import mkdtemp
import requests
from datetime import datetime

# Configuration
S3_BUCKET = 'tmp-ai-img-genrator'
S3_PREFIX = 'piktochart-images/'
EMAIL = "rautbalaji321@gmail.com"
PASSWORD = "Balaji@123"
PROMPT = "punes very traffic city"

def setup_driver(download_dir):
    """Configure ChromeDriver for Lambda with enhanced options"""
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-tools")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument(f"--user-data-dir={mkdtemp()}")
    chrome_options.add_argument(f"--data-path={mkdtemp()}")
    chrome_options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    chrome_options.add_argument("--remote-debugging-pipe")
    chrome_options.add_argument("--window-size=1199x1080")
    chrome_options.binary_location = "/opt/chrome/chrome-linux64/chrome"
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(
        executable_path="/opt/chrome-driver/chromedriver-linux64/chromedriver",
        service_log_path="/tmp/chromedriver.log"
    )
    
    driver = webdriver.Chrome(
        service=service,
        options=chrome_options
    )
    return driver

def upload_to_s3(file_path, object_name):
    """Upload file to S3 bucket with error handling"""
    s3 = boto3.client('s3')
    try:
        s3.upload_file(file_path, S3_BUCKET, object_name)
        url = f"https://{S3_BUCKET}.s3.amazonaws.com/{object_name}"
        return url
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        raise

def get_latest_downloaded_file(download_dir, timeout=30):
    """Wait for and return the latest downloaded file"""
    end_time = time.time() + timeout
    while time.time() < end_time:
        files = glob.glob(os.path.join(download_dir, "*"))
        # Filter out directories and system files
        files = [f for f in files if os.path.isfile(f) and not f.startswith('.')]
        if files:
            # Get the most recently modified file
            latest_file = max(files, key=os.path.getmtime)
            # Check if file is still being downloaded (partial files)
            if not latest_file.endswith('.crdownload'):
                return latest_file
        time.sleep(1)
    raise TimeoutError("File download timed out")

def cleanup_directory(directory):
    """Remove directory and its contents"""
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
        os.rmdir(directory)
    except Exception as e:
        print(f"Failed to cleanup directory {directory}. Reason: {e}")

def lambda_handler(event, context):
    driver = None
    try:
        # Create timestamped download directory
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        download_dir = f"/tmp/{timestamp}"
        os.makedirs(download_dir, exist_ok=True)
        
        driver = setup_driver(download_dir)
        
        # Piktochart automation script
        driver.get("https://piktochart.com/infographic-maker/")
        
        # Accept cookies
        accept_all = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-accept-btn-handler"]'))
        )
        accept_all.click()

        # Open navigation
        nav_bar = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/header/div/div/div/nav/button/span'))
        )
        nav_bar.click()

        # Login process
        login_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="masthead"]/div/div/div/nav/div[2]/a[1]'))
        )
        login_button.click()
        
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="user_email"]'))
        )
        email_field.send_keys(EMAIL)
        
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="user_password"]'))
        )
        password_field.send_keys(PASSWORD)
        
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="km_user_login"]'))
        )
        submit_button.click()
        
        # Wait for login to complete
        WebDriverWait(driver, 20).until(
            EC.url_contains("dashboard")
        )
        
        # Navigate to AI editor
        driver.get("https://piktochart.com/generative-ai/editor/")
        
        # Enter prompt and generate image
        prompt_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="topic-input"]'))
        )
        prompt_field.send_keys(PROMPT)
        
        generate_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="__nuxt"]/div/div[2]/div[2]/div[1]/div[3]/div[1]/div/div[3]/div[2]/button'))
        )
        generate_button.click()
        
        # Wait for generation to complete
        time.sleep(10)  # Adjust based on generation time
        
        # Save the image
        save_image = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="__nuxt"]/div/div[1]/div/button'))
        )
        save_image.click()
        
        continue_anyway = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div/div[2]/button'))
        )
        continue_anyway.click()
        
        # Download the image 
        time.sleep(10)
        download_image = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/header/ul[2]/li[1]/button[5]'))
        )
        download_image.click()
        print("clicked on download image")
        
        download_image1 = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="app"]/div[2]/div[1]/div/div[5]/button'))
        )
        time.sleep(10)
        download_image1.click()
        print("downloading image")

        downloaded_file = get_latest_downloaded_file(download_dir)
        print(f"Downloaded file: {downloaded_file}")
        
        # Generate a filename with your desired pattern
        file_extension = os.path.splitext(downloaded_file)[1]
        local_path = os.path.join(download_dir, f"generated_image{file_extension}")
        
        # Rename the downloaded file if needed
        if downloaded_file != local_path:
            os.rename(downloaded_file, local_path)
        
        # Upload to S3
        s3_object_name = f"{S3_PREFIX}{context.aws_request_id}{file_extension}"
        s3_url = upload_to_s3(local_path, s3_object_name)
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'Image generated and uploaded successfully',
                's3_url': s3_url,
                'local_path': local_path
            }
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        # Take screenshot for debugging
        if driver:
            screenshot_path = os.path.join(download_dir, 'error.png')
            driver.save_screenshot(screenshot_path)
            try:
                upload_to_s3(screenshot_path, f"{S3_PREFIX}errors/{context.aws_request_id}.png")
            except Exception as upload_error:
                print(f"Failed to upload error screenshot: {upload_error}")
        
        return {
            'statusCode': 500,
            'body': {
                'message': 'Image generation failed',
                'error': str(e)
            }
        }
        
    finally:
        if driver:
            driver.quit()
        # Clean up the download directory
        cleanup_directory(download_dir)
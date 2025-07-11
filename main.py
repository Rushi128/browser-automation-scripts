import os
import time
import boto3
import glob
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tempfile import mkdtemp
import requests
from datetime import datetime
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Configuration
S3_BUCKET = 'tmp-ai-img-genrator'
S3_PREFIX = 'venngage-images/'
EMAIL = "rautbalaji321@gmail.com"
PASSWORD = "Balaji@123"
PROMPT = "punes very traffic city"

# --- STEALTH/ANTI-DETECTION ---
def add_stealth(driver):
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
                Object.defineProperty(screen, 'colorDepth', {get: () => 24});
                Object.defineProperty(screen, 'pixelDepth', {get: () => 24});
                window.chrome = { runtime: {} };
                """
            }
        )
        logger.info("Stealth scripts injected successfully.")
    except Exception as e:
        logger.warning(f"Stealth script error: {e}")

def setup_driver(download_dir):
    logger.info(f"Setting up ChromeDriver. Download dir: {download_dir}")
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
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    ua = random.choice(user_agents)
    chrome_options.add_argument(f"--user-agent={ua}")
    logger.info(f"Using user agent: {ua}")
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.popups": 2,
        "profile.default_content_setting_values.geolocation": 2,
        "profile.default_content_setting_values.media_stream": 2,
        "profile.default_content_setting_values.automatic_downloads": 1,
        "profile.default_content_setting_values.plugins": 1,
        "profile.default_content_setting_values.images": 1,
        "profile.default_content_setting_values.javascript": 1,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    service = Service(
        executable_path="/opt/chrome-driver/chromedriver-linux64/chromedriver",
        service_log_path="/tmp/chromedriver.log"
    )
    driver = webdriver.Chrome(
        service=service,
        options=chrome_options
    )
    add_stealth(driver)
    logger.info("ChromeDriver setup complete.")
    return driver

def upload_to_s3(file_path, object_name):
    s3 = boto3.client('s3')
    try:
        s3.upload_file(file_path, S3_BUCKET, object_name)
        url = f"https://{S3_BUCKET}.s3.amazonaws.com/{object_name}"
        return url
    except Exception as e:
        logger.error(f"Error uploading to S3: {e}")
        raise

def get_latest_downloaded_file(download_dir, timeout=30):
    end_time = time.time() + timeout
    while time.time() < end_time:
        files = glob.glob(os.path.join(download_dir, "*"))
        files = [f for f in files if os.path.isfile(f) and not f.startswith('.')]
        if files:
            latest_file = max(files, key=os.path.getmtime)
            if not latest_file.endswith('.crdownload'):
                return latest_file
        time.sleep(1)
    raise TimeoutError("File download timed out")

def cleanup_directory(directory):
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.warning(f"Failed to delete {file_path}. Reason: {e}")
        os.rmdir(directory)
    except Exception as e:
        logger.warning(f"Failed to cleanup directory {directory}. Reason: {e}")

def lambda_handler(event, context):
    driver = None
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        download_dir = f"/tmp/{timestamp}"
        os.makedirs(download_dir, exist_ok=True)
        logger.info(f"Created download directory: {download_dir}")
        driver = setup_driver(download_dir)

        # Venngage automation script
        driver.get("https://infograph.venngage.com/universal-generator")
        logger.info("Navigated to Venngage Universal Generator.")

        # Accept cookies if present
        try:
            accept_cookies = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Accept all cookies")]'))
            )
            accept_cookies.click()
            logger.info("Accepted cookies.")
        except Exception as e:
            logger.info(f"No cookie popup or already accepted: {e}")

        # Login process
        email_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//input[@type="email" or @name="email"]'))
        )
        email_field.clear()
        email_field.send_keys(EMAIL)
        logger.info(f"Entered email: {EMAIL}")

        password_field = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//input[@type="password" or @name="password"]'))
        )
        password_field.clear()
        password_field.send_keys(PASSWORD)
        logger.info("Entered password.")

        continue_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Continue")]'))
        )
        continue_button.click()
        logger.info("Clicked Continue button.")

        # Wait for login to complete (look for dashboard or generator loaded)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "universal-generator")]'))
        )
        logger.info("Login successful and generator loaded.")

        # Enter prompt if required (update XPATH as needed)
        try:
            prompt_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//input[@type="text" or @placeholder]'))
            )
            prompt_field.clear()
            prompt_field.send_keys(PROMPT)
            logger.info(f"Entered prompt: {PROMPT}")
        except Exception as e:
            logger.info(f"Prompt field not found or not required: {e}")

        # Click generate or similar button (update XPATH as needed)
        try:
            generate_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Generate") or contains(text(), "Create") or contains(text(), "Start")]'))
            )
            generate_button.click()
            logger.info("Clicked generate button.")
        except Exception as e:
            logger.info(f"Generate button not found or not required: {e}")

        # Wait for generation to complete (adjust time as needed)
        time.sleep(10)
        logger.info("Waiting for generation to complete...")

        # Download or save the generated infographic (update XPATH as needed)
        try:
            download_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Download") or contains(text(), "Save")]'))
            )
            download_button.click()
            logger.info("Clicked download/save button.")
        except Exception as e:
            logger.info(f"Download/Save button not found: {e}")

        # Wait for download
        downloaded_file = get_latest_downloaded_file(download_dir)
        logger.info(f"Downloaded file: {downloaded_file}")

        file_extension = os.path.splitext(downloaded_file)[1]
        local_path = os.path.join(download_dir, f"generated_infographic{file_extension}")
        if downloaded_file != local_path:
            os.rename(downloaded_file, local_path)
            logger.info(f"Renamed downloaded file: {downloaded_file} to {local_path}")

        s3_object_name = f"{S3_PREFIX}{context.aws_request_id}{file_extension}"
        s3_url = upload_to_s3(local_path, s3_object_name)
        logger.info(f"Uploaded file to S3: {s3_url}")

        return {
            'statusCode': 200,
            'body': {
                'message': 'Infographic generated and uploaded successfully',
                's3_url': s3_url,
                'local_path': local_path
            }
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if driver:
            screenshot_path = os.path.join(download_dir, 'error.png')
            driver.save_screenshot(screenshot_path)
            logger.info(f"Saved screenshot to {screenshot_path}")
            try:
                s3_object_name = f"{S3_PREFIX}errors/{context.aws_request_id}.png"
                upload_to_s3(screenshot_path, s3_object_name)
                logger.info(f"Uploaded error screenshot to S3: {s3_object_name}")
            except Exception as upload_error:
                logger.warning(f"Failed to upload error screenshot: {upload_error}")
        return {
            'statusCode': 500,
            'body': {
                'message': 'Infographic generation failed',
                'error': str(e)
            }
        }
    finally:
        if driver:
            driver.quit()
            logger.info("ChromeDriver quit.")
        cleanup_directory(download_dir)
        logger.info(f"Cleaned up directory: {download_dir}")
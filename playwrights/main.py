import os
import time
import boto3
import glob
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tempfile import mkdtemp
from datetime import datetime

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

def setup_driver(download_dir):
    firefox_options = FirefoxOptions()
    firefox_options.add_argument("--headless")  # Headless for Lambda
    firefox_options.set_preference("browser.download.folderList", 2)
    firefox_options.set_preference("browser.download.dir", download_dir)
    firefox_options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf,image/png,image/jpeg,application/octet-stream")
    firefox_options.set_preference("pdfjs.disabled", True)
    firefox_options.set_preference("browser.download.manager.showWhenStarting", False)
    firefox_options.set_preference("browser.download.useDownloadDir", True)
    firefox_options.set_preference("browser.download.viewableInternally.enabledTypes", "")
    driver = webdriver.Firefox(options=firefox_options)
    logger.info("FirefoxDriver setup complete.")
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
            if not latest_file.endswith('.part'):
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

def lambda_handler(event=None, context=None):
    driver = None
    download_dir = None
    screenshot_url = None
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        download_dir = f"/tmp/{timestamp}"
        os.makedirs(download_dir, exist_ok=True)
        logger.info(f"Created download directory: {download_dir}")
        driver = setup_driver(download_dir)

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

        # Screenshot after login and upload to S3
        screenshot_path = os.path.join(download_dir, 'after_login.png')
        driver.save_screenshot(screenshot_path)
        logger.info(f"Saved screenshot after login to {screenshot_path}")
        if context:
            s3_object_name = f"{S3_PREFIX}after_login/{context.aws_request_id}.png"
            upload_to_s3(screenshot_path, s3_object_name)
            logger.info(f"Uploaded screenshot to S3: {s3_object_name}")

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

        s3_object_name = f"{S3_PREFIX}{getattr(context, 'aws_request_id', 'manual')}{file_extension}"
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
        # Try to take a screenshot if possible
        if driver and download_dir:
            screenshot_path = os.path.join(download_dir, 'error.png')
            try:
                driver.save_screenshot(screenshot_path)
                logger.info(f"Saved screenshot to {screenshot_path}")
                s3_object_name = f"{S3_PREFIX}errors/{getattr(context, 'aws_request_id', 'manual')}.png"
                screenshot_url = upload_to_s3(screenshot_path, s3_object_name)
                logger.info(f"Uploaded error screenshot to S3: {s3_object_name}")
            except Exception as upload_error:
                logger.warning(f"Failed to upload error screenshot: {upload_error}")
        else:
            logger.warning("No driver or download_dir available for screenshot.")
        return {
            'statusCode': 500,
            'body': {
                'message': 'Infographic generation failed',
                'error': str(e),
                'screenshot_url': screenshot_url
            }
        }
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("FirefoxDriver quit.")
            except Exception as e:
                logger.warning(f"Error quitting driver: {e}")
        if download_dir:
            try:
                cleanup_directory(download_dir)
                logger.info(f"Cleaned up directory: {download_dir}")
            except Exception as e:
                logger.warning(f"Error cleaning up directory: {e}")

# For local testing
if __name__ == "__main__":
    lambda_handler()
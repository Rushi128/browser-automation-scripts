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
import zipfile
import shutil



def setup_driver(download_dir):
    """Configure ChromeDriver for Lambda with enhanced options"""
    print(f"Setting up ChromeDriver with download directory: {download_dir}")
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
    chrome_options.add_argument("--window-size=1314x1080")
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
    print("ChromeDriver setup complete.")
    return driver

def upload_to_s3(file_path, object_name):
    """Upload file to S3 bucket with error handling"""
    print(f"Uploading {file_path} to S3 as {object_name}...")
    s3 = boto3.client('s3')
    try:
        s3.upload_file(file_path, S3_BUCKET, object_name)
        url = f"https://{S3_BUCKET}.s3.amazonaws.com/{object_name}"
        print(f"Upload successful: {url}")
        return url
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        raise

def get_latest_downloaded_file(download_dir, timeout=10):
    print(f"Waiting for file in {download_dir}...")
    end_time = time.time() + timeout
    while time.time() < end_time:
        files = glob.glob(os.path.join(download_dir, "*"))
        files = [f for f in files if os.path.isfile(f) and not f.startswith('.')]
        if files:
            latest_file = max(files, key=os.path.getmtime)
            if not latest_file.endswith('.crdownload'):
                print(f"Found downloaded file: {latest_file}")
                return latest_file
            else:
                print("File is still downloading...")
        time.sleep(0.2)
    print("File download timed out!")
    raise TimeoutError("File download timed out")

def cleanup_directory(directory):
    """Remove directory and its contents"""
    print(f"Cleaning up directory: {directory}")
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    print(f"Deleted file: {file_path}")
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
        os.rmdir(directory)
        print(f"Removed directory: {directory}")
    except Exception as e:
        print(f"Failed to cleanup directory {directory}. Reason: {e}")

def close_possible_popups(driver, wait_time=1, retries=1):
    """Try to close any popups, overlays, or iframes that may appear."""
    print("Checking and closing possible popups/overlays...")
    popup_xpaths = [
        '//button[contains(@aria-label, "Close")]',
        '//div[contains(@aria-label, "Close Preview")]',
        '//button[contains(text(), "No Thanks")]',
        '//button[contains(text(), "Skip")]',
        '//button[contains(text(), "Dismiss")]',
        '//div[contains(@aria-label, "Do not show again")]',
        '//button[contains(@class, "close")]',
        '//button[@title="Close"]',
        '//button[contains(text(), "Got it")]',
        '//button[contains(text(), "OK")]',
        '//button[contains(text(), "Okay")]',
        '//button[contains(text(), "Continue")]'
    ]
    for xpath in popup_xpaths:
        for _ in range(retries):
            try:
                popup = WebDriverWait(driver, wait_time).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                popup.click()
                print(f"Closed popup with xpath: {xpath}")
                time.sleep(0.2)
                break
            except Exception:
                continue
    # Remove floating iframes that may block clicks
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            iframe_id = iframe.get_attribute("id") or ""
            iframe_class = iframe.get_attribute("class") or ""
            if "ug-tooltip-frame" in iframe_id or "ug-frame-wrapper" in iframe_class:
                driver.execute_script("""
                    var elem = arguments[0];
                    elem.parentNode.removeChild(elem);
                """, iframe)
                print(f"Removed interfering iframe: id={iframe_id}, class={iframe_class}")
    except Exception as e:
        print("No interfering iframes found or error removing them:", e)
    # Remove overlay divs that may block clicks
    try:
        overlays = driver.find_elements(By.XPATH, "//div[contains(@class, 'ug-tooltip-rect-wrapper') or contains(@class, 'themes-preview-reflect-backdrop') or contains(@class, 'ug-sdk__sc-')]")
        for overlay in overlays:
            try:
                driver.execute_script("""
                    var elem = arguments[0];
                    elem.parentNode.removeChild(elem);
                """, overlay)
                print(f"Removed interfering overlay div: {overlay.get_attribute('class')}")
            except Exception:
                print("Overlay div was already removed (stale)")
    except Exception as e:
        print("No interfering overlay divs found or error removing them:", e)
    print("Popup/overlay check complete.")

def safe_click(driver, by, value, timeout=3, retries=2):
    print(f"Attempting to click element: {value}")
    from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
    for attempt in range(retries):
        try:
            close_possible_popups(driver)
            element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
            element.click()
            print(f"Clicked element: {value}")
            return True
        except StaleElementReferenceException:
            print(f"StaleElementReferenceException on click, retrying {attempt+1}/{retries}")
            time.sleep(0.2)
        except TimeoutException:
            print(f"TimeoutException: Could not click element {value}")
            return False
        except Exception as e:
            print(f"Exception during click: {e}")
            time.sleep(0.2)
    print(f"Failed to click element: {value}")
    return False

def extract_image_from_zip(zip_path, extract_to):
    print(f"Extracting image from zip: {zip_path}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    # Find the first image file (png/jpg/jpeg) in the extracted folder
    for root, dirs, files in os.walk(extract_to):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_path = os.path.join(root, file)
                # Move the image to the main download dir if not already there
                dest_path = os.path.join(extract_to, file)
                if image_path != dest_path:
                    shutil.move(image_path, dest_path)
                print(f"Extracted image: {dest_path}")
                return dest_path
    print("No image found in the zip archive!")
    raise FileNotFoundError("No image found in the zip archive.")

def lambda_handler(event, context):
    print("Lambda handler started.")
    # Configuration
    global S3_BUCKET, S3_PREFIX, EMAIL, PASSWORD
    S3_BUCKET =  event.get('S3_BUCKET')
    S3_PREFIX = 'piktochart-images/'
    EMAIL = event.get('EMAIL')
    PASSWORD = event.get('PASSWORD')
    driver = None
    try:
        prompt = event.get('prompt')
        if not prompt:
            print("Prompt missing in event!")
            return {
                'statusCode': 400,
                'body': {
                    'message': 'Prompt is required in the event',
                    'error': 'Missing prompt'
                }
            }
        print(f"Prompt received: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        download_dir = f"/tmp/{timestamp}"
        os.makedirs(download_dir, exist_ok=True)
        print(f"Download directory created: {download_dir}")
        driver = setup_driver(download_dir)
        print("Navigating to Piktochart login page...")
        driver.get("https://piktochart.com/infographic-maker/")
        safe_click(driver, By.XPATH, '//*[@id="onetrust-accept-btn-handler"]', timeout=2)
        safe_click(driver, By.XPATH, '/html/body/div[1]/header/div/div/div/nav/button/span', timeout=2)
        safe_click(driver, By.XPATH, '//*[@id="masthead"]/div/div/div/nav/div[2]/a[1]', timeout=2)
        print("Filling in login credentials...")
        email_field = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="user_email"]'))
        )
        email_field.send_keys(EMAIL)
        password_field = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="user_password"]'))
        )
        password_field.send_keys(PASSWORD)
        safe_click(driver, By.XPATH, '//*[@id="km_user_login"]', timeout=2)
        print("Waiting for dashboard after login...")
        WebDriverWait(driver, 6).until(
            EC.url_contains("dashboard")
        )
        print("Login successful.")
        close_possible_popups(driver)
        print("Navigating to AI editor...")
        driver.get("https://piktochart.com/generative-ai/editor/")
        close_possible_popups(driver)
        print("Navigating through AI editor UI...")
        safe_click(driver, By.XPATH, '/html/body/div[3]/div/div[2]/div[2]/div[1]/div[1]/div[2]/div[2]/div/button[2]', timeout=2)
        close_possible_popups(driver)
        safe_click(driver, By.XPATH, '//*[@id="__nuxt"]/div/div[2]/div[2]/div[1]/ul/li[2]', timeout=2)
        close_possible_popups(driver)
        print("Entering prompt and generating image...")
        prompt_field = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="summarization-input"]'))
        )
        prompt_field.send_keys(prompt)
        close_possible_popups(driver)
        safe_click(driver, By.XPATH, '//*[@id="__nuxt"]/div/div[2]/div[2]/div[1]/div[3]/div[1]/div/div[2]/div[3]/div/button', timeout=3)
        print("Waiting for image generation to complete...")
        WebDriverWait(driver, 15).until(lambda d: "generating" not in d.page_source.lower())
        close_possible_popups(driver)
        print("Waiting extra time for image to be ready...")
        time.sleep(40)
        print("Saving image...")
        # safe_click(driver, By.XPATH, '/html/body/div[1]/div/div[1]/div/button', timeout=3)
        # close_possible_popups(driver)
        # 
        safe_click(driver, By.XPATH, '/html/body/div[3]/div/div[1]/div/button', timeout=3)

        # close_possible_popups(driver)
        # safe_click(driver, By.XPATH, '/html/body/div[3]/div/div[1]/div/button', timeout=3)
        close_possible_popups(driver)
        safe_click(driver, By.XPATH, '/html/body/div[3]/div/div[2]/button', timeout=3)
        close_possible_popups(driver)

        print("Initiating image download...")
        safe_click(driver, By.XPATH, '/html/body/div[3]/div/div[1]/header/ul[2]/li[1]/button[5]', timeout=3)
        close_possible_popups(driver)
        safe_click(driver, By.XPATH, '/html/body/div[3]/div/div[1]/div[2]/div[1]/div/div[5]/button', timeout=3)
        close_possible_popups(driver)
        print("Waiting for image file to download...")
        time.sleep(10)
        downloaded_file = get_latest_downloaded_file(download_dir, timeout=10)
        file_extension = os.path.splitext(downloaded_file)[1].lower()
        if file_extension == '.zip':
            try:
                print("Downloaded file is a zip. Extracting image...")
                extracted_image = extract_image_from_zip(downloaded_file, download_dir)
                os.remove(downloaded_file)
                upload_file_path = extracted_image
                upload_ext = os.path.splitext(extracted_image)[1]
            except Exception as e:
                print(f"Failed to extract image from zip: {e}")
                raise Exception(f"Failed to extract image from zip: {e}")
        else:
            print("Downloaded file is an image.")
            upload_file_path = downloaded_file
            upload_ext = file_extension
        local_path = os.path.join(download_dir, f"generated_image{upload_ext}")
        if upload_file_path != local_path:
            os.rename(upload_file_path, local_path)
        print(f"Uploading image to S3: {local_path}")
        s3_object_name = f"{S3_PREFIX}{context.aws_request_id}{upload_ext}"
        s3_url = upload_to_s3(local_path, s3_object_name)
        print(f"Image uploaded to S3: {s3_url}")
        return {
            'statusCode': 200,
            'body': {
                'status': 'success',
                'message': 'Image generated and uploaded successfully',
                's3_key': s3_object_name,
                's3_url': s3_url
            }
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        if driver:
            screenshot_path = os.path.join(download_dir, 'error.png')
            driver.save_screenshot(screenshot_path)
            print(f"Saved error screenshot to: {screenshot_path}")
            try:
                upload_to_s3(screenshot_path, f"{S3_PREFIX}errors/{context.aws_request_id}.png")
                print("Uploaded error screenshot to S3.")
            except Exception as upload_error:
                print(f"Failed to upload error screenshot: {upload_error}")
        return {
            'statusCode': 500,
            'body': {
                'status': 'error',
                'message': 'Image generation failed',
                'error': str(e)
            }
        }
    finally:
        if driver:
            driver.quit()
            print("Browser closed.")
        cleanup_directory(download_dir)
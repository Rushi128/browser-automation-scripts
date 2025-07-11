import os
import time
import boto3
import glob
from playwright.sync_api import sync_playwright
from datetime import datetime

# Configuration
S3_BUCKET = 'tmp-ai-img-genrator'
S3_PREFIX = 'piktochart-images/'
EMAIL = "rautbalaji321@gmail.com"
PASSWORD = "Earth@123"
PROMPT = "punes very traffic city"

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

def capture_error_screenshot(page, download_dir, context):
    """Capture screenshot of error and upload to S3"""
    try:
        if page:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            screenshot_filename = f"error_{timestamp}.png"
            screenshot_path = os.path.join(download_dir, screenshot_filename)
            page.screenshot(path=screenshot_path)
            
            # Generate S3 object name with request ID if available
            object_name = f"{S3_PREFIX}errors/"
            if context and hasattr(context, 'aws_request_id'):
                object_name += f"{context.aws_request_id}/"
            object_name += screenshot_filename
            
            try:
                s3_url = upload_to_s3(screenshot_path, object_name)
                print(f"Error screenshot uploaded to S3: {s3_url}")
                return s3_url
            except Exception as upload_error:
                print(f"Failed to upload error screenshot: {upload_error}")
                return None
    except Exception as e:
        print(f"Failed to capture error screenshot: {e}")
        return None

def lambda_handler(event, context):
    with sync_playwright() as playwright:
        browser = None
        page = None
        try:
            # Create timestamped download directory
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            download_dir = f"/tmp/{timestamp}"
            os.makedirs(download_dir, exist_ok=True)
            print(timestamp)
            
            # Launch browser with download options
            browser = playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process"
                ]
            )
            
            # Create a new context with download settings
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                accept_downloads=True,
                extra_http_headers={
                    "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": "https://infograph.venngage.com",
                    "Priority": "u=1, i",
                    "Referer": "https://infograph.venngage.com/",
                    "Sec-Ch-Ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Linux"',
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "cross-site",
                    "Sec-Fetch-Storage-Access": "active"
                }
            )
            
            # Set up download path
            page = context.new_page()
            
            print("Navigating to Piktochart")
            page.goto("https://infograph.venngage.com/universal-generator", timeout=60000)
            
            # Accept cookies
            print("Accepting cookies")
            page.click('xpath=/html/body/div[1]/div/div/button[2]', timeout=20000)
            
            print("Logging in")
            page.fill('xpath=//*[@id="user_email"]', EMAIL, timeout=20000)
            page.click('xpath=//*[@id="btn_login"]', timeout=20000)
            
            page.fill('xpath=//*[@id="user_password"]', PASSWORD, timeout=20000)
            page.click('xpath=//*[@id="btn_login"]', timeout=20000)
            
            print("Verifying login success")
            page.wait_for_selector('xpath=//h1[contains(@class, "chakra-text") and contains(text(), "AI Design Generator")]', timeout=60000)
            print("Successfully logged in and verified AI Design Generator page")
            
            print("Creating new design")
            page.click('xpath=/html/body/div[1]/div/div[3]/div[1]/div[2]/button[2]', timeout=20000)
            time.sleep(4)
            
            print("Entering prompt")
            page.fill('xpath=//*[@id="prompt-input"]', PROMPT, timeout=20000)
            
            print("Generating image")
            page.click('xpath=//*[@id="chat-input-button"]', timeout=20000)
            time.sleep(60)  # Generation time
            
            print("Customizing image")
            page.click('xpath=//*[@id="root"]/div/div[3]/div[2]/form/div[3]/div[1]/div/div[3]/button[2]', timeout=30000)
            time.sleep(30)
            
            time.sleep(40)
            
            return {
                'statusCode': 200,
                'body': {
                    'message': 'Image generated and uploaded successfully',
                }
            }
        
        except Exception as e:
            print(f"Error: {str(e)}")
            # Capture and upload error screenshot
            screenshot_url = capture_error_screenshot(page, download_dir, context)
            
            error_response = {
                'statusCode': 500,
                'body': {
                    'message': 'Image generation failed',
                    'error': str(e)
                }
            }
            
            if screenshot_url:
                error_response['body']['screenshot_url'] = screenshot_url
            
            return error_response
        
        finally:
            if page:
                page.close()
            if context:
                context.close()
            if browser:
                browser.close()
            # Clean up the download directory
            # cleanup_directory(download_dir)
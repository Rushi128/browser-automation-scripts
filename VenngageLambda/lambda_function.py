import os
import time
import boto3
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright
import glob

def solve_recaptcha(sitekey, url, api_key):
    data = {
        'key': api_key,
        'method': 'userrecaptcha',
        'googlekey': sitekey,
        'pageurl': url,
        'json': 1
    }
    response = requests.post('http://2captcha.com/in.php', data=data)
    if response.json().get('status') != 1:
        print("2Captcha upload failed:", response.text)
        return None
    captcha_id = response.json()['request']
    for _ in range(24):
        res = requests.get(f'http://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}&json=1')
        result = res.json()
        if result.get('status') == 0 and result.get('request') == 'CAPCHA_NOT_READY':
            time.sleep(5)
        elif result.get('status') == 1:
            return result['request']
        else:
            print("2Captcha solve failed:", res.text)
            return None
    print("2Captcha timeout.")
    return None

def find_sitekey(page):
    try:
        sitekey = page.get_attribute('[data-sitekey]', 'data-sitekey')
        if sitekey:
            print(f"Found sitekey using [data-sitekey]: {sitekey}")
            return sitekey
    except:
        pass
    for f in page.frames:
        try:
            sitekey = f.get_attribute('[data-sitekey]', 'data-sitekey')
            if sitekey:
                print(f"Found sitekey in frame: {sitekey}")
                return sitekey
        except:
            continue
    print("No sitekey found.")
    return None

def upload_error_screenshot(page, bucket_name, key_prefix):
    try:
        if page and not page.is_closed():
            screenshot_path = f"/tmp/error_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            s3 = boto3.client('s3')
            key = f"{key_prefix}/error_screenshot.png"
            s3.upload_file(screenshot_path, bucket_name, key)
            print(f"Uploaded error screenshot to s3://{bucket_name}/{key}")
        else:
            print("No page available for screenshot.")
    except Exception as e:
        print(f"Failed to upload error screenshot: {e}")

def lambda_handler(event, context):
    EMAIL = os.environ.get("VENNGAGE_EMAIL")
    PASSWORD = os.environ.get("VENNGAGE_PASSWORD")
    API_KEY_2CAPTCHA = os.environ.get("API_KEY_2CAPTCHA")
    BUCKET_NAME = os.environ.get("S3_BUCKET")
    PROMPT = event.get("prompt", "default_prompt")

    with sync_playwright() as p:
        browser = None
        page = None
        
        try:
            # Launch browser with specific args for Lambda
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--single-process',
                    '--no-zygote',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            context = browser.new_context(
                accept_downloads=True,
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()

            print("Navigating to Venngage...")
            page.goto("https://infograph.venngage.com/universal-generator", timeout=60000)
            time.sleep(2)

            try:
                page.click('button:has-text("Accept all cookies")', timeout=5000)
            except:
                pass

            print("Logging in...")
            page.fill('input[type="email"]', EMAIL)
            page.click('button:has-text("Continue")')
            time.sleep(2)
            page.fill('input[type="password"]', PASSWORD)
            page.click('button:has-text("Log in")')
            time.sleep(3)

            # reCAPTCHA Handling
            sitekey = find_sitekey(page)
            if sitekey:
                token = solve_recaptcha(sitekey, page.url, API_KEY_2CAPTCHA)
                if token:
                    page.evaluate("""
                        (token) => {
                            const recaptcha = document.getElementById('g-recaptcha-response');
                            if (recaptcha) {
                                recaptcha.style.display = 'block';
                                recaptcha.value = token;
                                recaptcha.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        }
                    """, token)
                    page.evaluate("""
                        const forms = document.querySelectorAll('form');
                        forms.forEach(form => {
                            if (form.contains(document.getElementById('g-recaptcha-response'))) {
                                form.submit();
                            }
                        });
                    """)
                    try:
                        page.wait_for_url("**/dashboard", timeout=10000)
                        print("Login successful")
                    except:
                        print("No redirect, possibly already logged in")
                else:
                    raise Exception("reCAPTCHA token not obtained")
            else:
                print("No reCAPTCHA sitekey found.")

            print(f"Prompt received: {PROMPT}")
            page.click('button:has-text("Infographics")', timeout=10000)
            time.sleep(2)

            page.fill('textarea#prompt-input', PROMPT)
            time.sleep(1)
            page.click('button:has-text("Generate infographic")', timeout=5000)
            print(f"Submitted prompt: {PROMPT}")

            page.wait_for_selector('button:has-text("Customize")', timeout=60000)
            page.click('button:has-text("Customize")')
            print("Clicked on 'Customize'")

            page.wait_for_selector('button[data-testid="download-infograph-button"]', timeout=15000)
            page.click('button[data-testid="download-infograph-button"]')
            print("Clicked on 'Download'")

            # try:
            #     page.wait_for_selector('footer > button', timeout=10000)
            #     page.click('footer > button')
            #     print("Clicked final footer button")
            # except Exception as e:
            #     print(f"Footer button not found, retrying using XPath: {e}")
            #     page.locator('xpath=//*[@id="tabs-:rb1:--tabpanel-2"]/footer/button').click()
            #     print("Clicked via XPath")
            time.sleep(5)  # Wait for download to complete
            # Find the most recent file in /tmp (assuming that's where downloads go)
            # downloaded_files = glob.glob("/tmp/*")
            # if not downloaded_files:
            #     raise Exception("No files found in /tmp after download")
            # latest_file = max(downloaded_files, key=os.path.getctime)

            # # Rename the file with current timestamp
            # timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            # file_ext = os.path.splitext(latest_file)[1]
            # new_filename = f"/tmp/venngage_{timestamp}{file_ext}"
            # os.rename(latest_file, new_filename)

            # # Upload to S3
            # s3 = boto3.client('s3')
            # s3_key = f"venngage/{os.path.basename(new_filename)}"
            # s3.upload_file(new_filename, BUCKET_NAME, s3_key)
            # print(f"Uploaded downloaded file to s3://{BUCKET_NAME}/{s3_key}")
            # Save result screenshot
            screenshot_path = f"/tmp/result_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            page.screenshot(path=screenshot_path, full_page=True)

            # Upload to S3
            s3 = boto3.client('s3')
            s3_key = f"venngage/{os.path.basename(screenshot_path)}"
            s3.upload_file(screenshot_path, BUCKET_NAME, s3_key)
            print(f"Uploaded screenshot to s3://{BUCKET_NAME}/{s3_key}")

            return {
                'statusCode': 200,
                'body': f"Prompt processed successfully: {PROMPT}"
            }

        except Exception as e:
            print(f"Automation failed: {e}")
            if page and not page.is_closed():
                upload_error_screenshot(page, BUCKET_NAME, "venngage/errors")
            return {
                'statusCode': 500,
                'body': f"Error: {str(e)}"
            }
        finally:
            try:
                if page and not page.is_closed():
                    page.close()
                if context:
                    context.close()
                if browser:
                    browser.close()
            except Exception as e:
                print(f"Cleanup error: {e}")
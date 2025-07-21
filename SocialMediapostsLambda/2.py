import json
import requests
import base64

def lambda_handler(event, context):
    # Required parameters
    caption = event.get('caption', '')
    image_url = event.get('image_url')
    message = event.get('message', '')
    file_name = event.get('fileName', image_url.split('/')[-1] if image_url else 'image.jpg')
    page_id = event.get('page', '519351091272803')  # Default page ID

    if not image_url:
        return {
            'statusCode': 400,
            'body': json.dumps("Missing image_url in event.")
        }

    try:
        # 1. Download the image
        img_response = requests.get(image_url, timeout=10)
        img_response.raise_for_status()
        image_data = img_response.content
        
        # 2. Prepare the payload structure that Make.com expects
        payload = {
            "page": page_id,
            "message": message,
            "photos": [{
                "data": {
                    "files": [{
                        "data": base64.b64encode(image_data).decode('utf-8'),  # Base64 required by Make
                        "name": file_name
                    }]
                },
                "I want to": "data",  # Required by Make's mapping
                "Caption": caption
            }]
        }

        # 3. Send to Make.com webhook
        make_webhook_url = "https://hook.us2.make.com/ldc7f8id1de7xxl3srjmnnu7swwk8gw6"
        response = requests.post(make_webhook_url, json=payload)
        response.raise_for_status()
        
        return {
            'statusCode': 200,
            'body': json.dumps(response.json())
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }

# Test locally
if __name__ == "__main__":
    test_event = {
        "caption": "Test caption",
        "image_url": "https://plus.unsplash.com/premium_photo-1673292293042-cafd9c8a3ab3?fm=jpg&q=60&w=3000&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8bmF0dXJlfGVufDB8fDB8fHww",
        "message": "Test message",
        "fileName": "test.png",
        "page": "519351091272803"
    }
    print(lambda_handler(test_event, None))
import json
import requests

def lambda_handler(event, context):
    caption = event.get('caption', '')
    image_url = event.get('image_url', '')
    message = event.get('message', '')
    file_name = event.get('fileName', '')

    # --- Zapier Webhook (Working) ---
    zapier_webhook_url = "https://hooks.zapier.com/hooks/catch/23828445/u2kk3cc/"
    zapier_payload = {
        "caption": caption,
        "image": image_url,
        "fileName": file_name,
        # "message": message
    }
    response = requests.post(zapier_webhook_url, json=zapier_payload)

    # --- Pabbly Webhook (Working) ---
    # pabbly_webhook_url = "https://connect.pabbly.com/workflow/sendwebhookfiledata/IjU3NjEwNTY0MDYzMzA0MzQ1MjY4NTUzZCI_3D_pc/IjU3NjYwNTZhMDYzNjA0M2M1MjY4NTUzNDUxMzci_pc"
    # pabbly_payload = {
    #     "caption": caption,
    #     "image_url": image_url,
    #     "fileName": file_name,
    #     "message": message
    # }
    # response = requests.post(pabbly_webhook_url, json=pabbly_payload)

    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.text)
    }

if __name__ == "__main__":
    test_event = {
        "caption": "Test caption",
        "image_url": "https://thumbs.dreamstime.com/b/beautiful-rain-forest-ang-ka-nature-trail-doi-inthanon-national-park-thailand-36703721.jpg",
        "message": "Test message",
        "fileName": "12345.png"
    }
    print(lambda_handler(test_event, None))
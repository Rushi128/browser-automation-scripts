import json
import requests
import base64
from requests_toolbelt.multipart.encoder import MultipartEncoder

def lambda_handler(event, context):
    caption = event.get('caption')
    image_url = event.get('image_url')
    message = event.get('message')
    file_name = event.get('fileName')  # default fallback
    location_id = 106442706060302

    if not file_name:
        file_name = image_url.split('/')[-1].split('?')[0]

    try:
        # Download the image
        img_response = requests.get(image_url)
        img_response.raise_for_status()
        
        # Create multipart form data
        multipart_data = MultipartEncoder(
            fields={
                'page': event.get('page', '519351091272803'),
                'message': message,
                'caption': caption,
                'file': (file_name, img_response.content, 'image/png'),
                'image_url': image_url,
                'location_id': str(location_id)  # Ensure location_id is a string
            }
        )
        
        # Post to Make.com with proper headers
        response = requests.post(
            "https://hook.us2.make.com/ldc7f8id1de7xxl3srjmnnu7swwk8gw6",
            data=multipart_data,
            headers={'Content-Type': multipart_data.content_type}
        )
        
        response.raise_for_status()
        return {'statusCode': 200, 'body': 'Success'}
        
    except Exception as e:
        return {'statusCode': 500, 'body': f"Error: {str(e)}"}
    # Your active Make.com webhook
    # make_webhook_url = "https://hook.us2.make.com/ldc7f8id1de7xxl3srjmnnu7swwk8gw6"

    # # Construct payload with image URL instead of base64
    # payload = {
    #     "caption": caption,
    #     "message": message,
    #     "image": {
    #         "url": image_url,
    #         "fileName": file_name
    #     }
    # }

    # print("Payload to Make:", payload)
    # try:
    #     response = requests.post(make_webhook_url, json=payload)
    #     print("Response from Make:", response.text)
    #     response.raise_for_status()
    # except Exception as e:
    #     return {
    #         'statusCode': 502,
    #         'body': json.dumps(f"Failed to post to Make webhook: {str(e)}")
    #     }

    # return {
    #     'statusCode': response.status_code,
    #     'body': json.dumps("Success: " + response.text)
    # }


    # --- Zapier Webhook (Commented) ---
    # zapier_webhook_url = "https://hooks.zapier.com/hooks/catch/23828445/u2kk3cc/"
    # zapier_payload = {
    #     "caption": caption,
    #     "image": image_url,
    #     "fileName": file_name,
    # }
    # response = requests.post(zapier_webhook_url, json=zapier_payload)

    # --- Pabbly Webhook (Commented) ---
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
        "image_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQ0nEQLJTxD4IQpMiPeTNisMxXqk0K60SF5wJZ6nmbycC5WbvV2OTo6ru7ldA6BCNU6kWk&usqp=CAU",
        "message": "Test message",
        "fileName": "12345.png"
    }
    print(lambda_handler(test_event, None))
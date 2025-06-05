from flask import Flask, request
import threading
import requests
import os
import json

app = Flask(__name__)

# ATR credentials and endpoint
ATR_USERNAME = "ChatbotTestuser"
ATR_PASSWORD = "User@1234"
ATR_BASE_URL = "https://dh1-internalatrgm.atrmywizard-aiops.com"

def handle_slack_command(text, response_url):
    try:
        # Step 1: Get JWT token
        token_url = f"{ATR_BASE_URL}/atr-gateway/identity-management/api/v1/auth/token?useDeflate=true"
        auth_payload = {
            "username": ATR_USERNAME,
            "password": ATR_PASSWORD
        }
        token_response = requests.post(token_url, json=auth_payload)
        token_response.raise_for_status()
        jwt_token = token_response.json().get("token")

        # Step 2: Query ATR
        query_url = f"{ATR_BASE_URL}/atr-gateway/bot/api/v1/query"
        headers = {
            "accept": "application/json",
            "apiToken": jwt_token,
            "Content-Type": "application/json"
        }
        query_payload = {
            "query": [text],
            "lang": "en"
        }
        atr_response = requests.post(query_url, headers=headers, json=query_payload)
        atr_response.raise_for_status()
        atr_data = atr_response.json()

        print("ATR API Response:")
        print(json.dumps(atr_data, indent=2))

        speech = atr_data.get("result", {}).get("speech", "")
        attachments = atr_data.get("attachments")

        if attachments:
            blocks = []

            # Handle TextBlock and other items in body
            for item in attachments.get("body", []):
                if item["type"] == "TextBlock":
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": item.get("text", "")
                        }
                    })
                elif item["type"] == "Input.ChoiceSet":
                    options = [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": choice["title"]
                            },
                            "value": choice["value"]
                        }
                        for choice in item.get("choices", []) if choice.get("title")
                    ]
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{item.get('label', 'Choose')}*"
                        },
                        "accessory": {
                            "type": "static_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": item.get("placeholder", "Select")
                            },
                            "options": options,
                            "action_id": item.get("id", "choice_action")
                        }
                    })
                elif item["type"] == "ActionSet":
                    button_elements = [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": button["title"]
                            },
                            "value": button["data"]["msteams"]["text"],
                            "action_id": "button_action"
                        }
                        for button in item.get("actions", [])
                    ]
                    blocks.append({
                        "type": "actions",
                        "elements": button_elements
                    })

            # Handle final actions
            if attachments.get("actions"):
                action_buttons = [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": action["title"]
                        },
                        "value": action["data"]["msteams"]["text"],
                        "action_id": "final_action"
                    }
                    for action in attachments["actions"]
                ]
                blocks.append({
                    "type": "actions",
                    "elements": action_buttons
                })

            slack_payload = {
                "response_type": "in_channel",
                "blocks": blocks
            }
        else:
            slack_payload = {
                "response_type": "in_channel",
                "text": f"*Query:* {text}\n*ATR Reply:* {speech or 'No response from ATR.'}"
            }

        requests.post(response_url, json=slack_payload)

    except Exception as e:
        error_payload = {
            "response_type": "ephemeral",
            "text": f"❌ Error processing request: {str(e)}"
        }
        requests.post(response_url, json=error_payload)

@app.route("/")
def index():
    return "✅ Flask app for Slack and ATR is running on Render!"

@app.route('/slack/commands', methods=['POST'])
def slack_commands():
    text = request.form.get('text')
    response_url = request.form.get('response_url')
    threading.Thread(target=handle_slack_command, args=(text, response_url)).start()
    return "", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# ATR credentials and endpoint
ATR_USERNAME = "ChatbotTestuser"
ATR_PASSWORD = "User@1234"
ATR_BASE_URL = "https://dh1-internalatrgm.atrmywizard-aiops.com"

def get_atr_response(text):
    token_url = f"{ATR_BASE_URL}/atr-gateway/identity-management/api/v1/auth/token?useDeflate=true"
    auth_payload = {"username": ATR_USERNAME, "password": ATR_PASSWORD}
    jwt_token = requests.post(token_url, json=auth_payload).json().get("token")

    query_url = f"{ATR_BASE_URL}/atr-gateway/bot/api/v1/query"
    headers = {
        "accept": "application/json",
        "apiToken": jwt_token,
        "Content-Type": "application/json"
    }
    query_payload = {"query": [text], "lang": "en"}
    return requests.post(query_url, headers=headers, json=query_payload).json()

def format_blocks_from_attachments(attachments):
    blocks = []
    for item in attachments.get("body", []):
        if item["type"] == "TextBlock":
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": item.get("text", "")}})
        elif item["type"] == "Input.ChoiceSet":
            options = [
                {"text": {"type": "plain_text", "text": choice["title"]}, "value": choice["value"]}
                for choice in item.get("choices", []) if choice.get("title")
            ]
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{item.get('label', 'Choose')}*"},
                "accessory": {
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": item.get("placeholder", "Select")},
                    "options": options,
                    "action_id": item.get("id", "choice_action")
                }
            })
        elif item["type"] == "ActionSet":
            button_elements = [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": button["title"]},
                    "value": button.get("data", {}).get("msteams", {}).get("text", button["title"]),
                    "action_id": "button_action"
                }
                for button in item.get("actions", [])
            ]
            blocks.append({"type": "actions", "elements": button_elements})

    if attachments.get("actions"):
        action_buttons = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": action["title"]},
                "value": action.get("data", {}).get("msteams", {}).get("text", action["title"]),
                "action_id": "final_action"
            }
            for action in attachments["actions"]
        ]
        blocks.append({"type": "actions", "elements": action_buttons})

    return blocks

@app.route("/")
def index():
    return "✅ Flask app for Slack and ATR is running on Render!"

@app.route('/slack/commands', methods=['POST'])
def slack_commands():
    text = request.form.get('text')
    response_url = request.form.get('response_url')

    try:
        atr_data = get_atr_response(text)
        print("ATR API Response:", json.dumps(atr_data, indent=2))

        speech = atr_data.get("result", {}).get("speech", "")
        attachments = atr_data.get("attachments")

        if attachments:
            blocks = format_blocks_from_attachments(attachments)
            slack_payload = {"response_type": "in_channel", "blocks": blocks}
        else:
            slack_payload = {"response_type": "in_channel", "text": f"*Query:* {text}\n*ATR Reply:* {speech or 'No response from ATR.'}"}

        requests.post(response_url, json=slack_payload)

    except Exception as e:
        requests.post(response_url, json={"response_type": "ephemeral", "text": f"❌ Error: {str(e)}"})

    return "", 200

@app.route('/slack/interactions', methods=['POST'])
def slack_interactions():
    payload = json.loads(request.form.get("payload"))
    print("Slack Interaction Payload:", json.dumps(payload, indent=2))

    action = payload.get("actions")[0]
    selected_value = (
        action.get("selected_option", {}).get("value") or
        action.get("value") or
        action.get("text", {}).get("text") or
        ""
    )
    response_url = payload.get("response_url")
    print(f"Selected value: {selected_value}")

    try:
        atr_data = get_atr_response(selected_value)
        print("ATR API Response:", json.dumps(atr_data, indent=2))

        speech = atr_data.get("result", {}).get("speech", "")
        attachments = atr_data.get("attachments")

        if attachments:
            blocks = format_blocks_from_attachments(attachments)
            slack_payload = {"response_type": "in_channel", "replace_original": True, "blocks": blocks}
        else:
            slack_payload = {"response_type": "in_channel", "replace_original": True, "text": f"*Query:* {selected_value}\n*ATR Reply:* {speech or 'No response from ATR.'}"}

        requests.post(response_url, json=slack_payload)

    except Exception as e:
        requests.post(response_url, json={"response_type": "ephemeral", "text": f"❌ Error: {str(e)}"})

    return "", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

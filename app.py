from flask import Flask, request
import threading
import requests
import json

app = Flask(__name__)

# Hardcoded for now
ATR_USERNAME = "ChatbotTestuser"
ATR_PASSWORD = "User@1234"
ATR_BASE_URL = "https://dh1-internalatrgm.atrmywizard-aiops.com"


def handle_slack_command(text, response_url):
    try:
        # Step 1: Authenticate with ATR
        token_url = f"{ATR_BASE_URL}/atr-gateway/identity-management/api/v1/auth/token?useDeflate=true"
        auth_payload = {"username": ATR_USERNAME, "password": ATR_PASSWORD}
        token_response = requests.post(token_url, json=auth_payload)
        token_response.raise_for_status()
        jwt_token = token_response.json().get("token")

        # Step 2: Send query to ATR
        query_url = f"{ATR_BASE_URL}/atr-gateway/bot/api/v1/query"
        headers = {
            "accept": "application/json",
            "apiToken": jwt_token,
            "Content-Type": "application/json"
        }
        query_payload = {"query": [text], "lang": "en"}
        atr_response = requests.post(query_url, headers=headers, json=query_payload)
        atr_response.raise_for_status()
        atr_data = atr_response.json()

        # Step 3: Build Slack message
        speech = atr_data.get("result", {}).get("speech", "")
        attachment = atr_data.get("attachments")

        if attachment and attachment.get("actions"):
            # Map Adaptive Card buttons to Slack interactive buttons
            blocks = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": speech or "Please choose an option:"}
                },
                {
                    "type": "actions",
                    "elements": []
                }
            ]
            for action in attachment.get("actions", []):
                title = action.get("title")
                value = action.get("data", {}).get("msteams", {}).get("text", title)
                blocks[1]["elements"].append({
                    "type": "button",
                    "text": {"type": "plain_text", "text": title},
                    "value": value,
                    "action_id": value
                })

            slack_payload = {
                "response_type": "in_channel",
                "blocks": blocks
            }
        else:
            slack_payload = {
                "response_type": "in_channel",
                "text": f"*Query:* {text}\n*ATR Reply:* {speech or 'No response'}"
            }

        requests.post(response_url, json=slack_payload)

    except Exception as e:
        error_payload = {
            "response_type": "ephemeral",
            "text": f"❌ Error: {str(e)}"
        }
        requests.post(response_url, json=error_payload)


@app.route("/")
def index():
    return "✅ Flask app for Slack and ATR is running!"


@app.route('/slack/commands', methods=['POST'])
def slack_commands():
    text = request.form.get('text')
    response_url = request.form.get('response_url')
    threading.Thread(target=handle_slack_command, args=(text, response_url)).start()
    return "", 200


@app.route('/slack/interactions', methods=['POST'])
def slack_interactions():
    payload = json.loads(request.form.get('payload'))
    user_input = payload.get("actions", [{}])[0].get("value", "")
    response_url = payload.get("response_url")
    threading.Thread(target=handle_slack_command, args=(user_input, response_url)).start()
    return "", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

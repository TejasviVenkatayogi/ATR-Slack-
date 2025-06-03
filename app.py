from flask import Flask, request
import threading
import requests

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

        # Step 3: Format reply
        atr_reply = atr_data.get("answers", [{}])[0].get("answer", "No response from ATR.")

        # Step 4: Respond to Slack
        slack_payload = {
            "response_type": "in_channel",
            "text": f"*Query:* {text}\n*ATR Reply:* {atr_reply}"
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

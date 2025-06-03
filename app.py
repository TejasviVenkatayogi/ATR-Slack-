
from flask import Flask, request, jsonify
import requests
import hashlib
import hmac
import time

app = Flask(__name__)

SLACK_BOT_TOKEN = 'xoxb-8954890085095-9016266247392-xAqcNtlmihlpJaRFXH7KwStH'
SLACK_SIGNING_SECRET = '64afcc485b93649acb7f6f45f2158158'
ATR_BASE_URL = 'https://dh1-internalatrgm.atrmywizard-aiops.com'
ATR_USERNAME = 'ChatbotTestuser'
ATR_PASSWORD = 'User@1234'

def get_atr_jwt_token():
    url = f'{ATR_BASE_URL}/atr-gateway/identity-management/api/v1/auth/token?useDeflate=true'
    payload = {"username": ATR_USERNAME, "password": ATR_PASSWORD}
    response = requests.post(url, json=payload)
    if response.ok:
        return response.json().get("token")
    else:
        return None

def query_atr_bot(query_text, jwt_token):
    url = f'{ATR_BASE_URL}/atr-gateway/bot/api/v1/query'
    headers = {"Authorization": f"Bearer {jwt_token}", "Content-Type": "application/json"}
    payload = {"query": [query_text], "lang": "en"}
    response = requests.post(url, headers=headers, json=payload)
    if response.ok:
        return response.json()
    else:
        return {"error": "ATR Query Failed"}

def verify_slack_request(req):
    timestamp = req.headers.get('X-Slack-Request-Timestamp')
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False
    sig_basestring = f"v0:{timestamp}:{req.get_data(as_text=True)}"
    my_signature = 'v0=' + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    slack_signature = req.headers.get('X-Slack-Signature')
    return hmac.compare_digest(my_signature, slack_signature)

@app.route('/slack/commands', methods=['POST'])
def slack_commands():
    if not verify_slack_request(request):
        return "Invalid request", 400

    data = request.form
    command_text = data.get('text')
    channel_id = data.get('channel_id')

    jwt_token = get_atr_jwt_token()
    if not jwt_token:
        return jsonify({"response_type": "ephemeral", "text": "Failed to authenticate with ATR."})

    atr_response = query_atr_bot(command_text, jwt_token)
    atr_message = atr_response.get("result", "No result from ATR.") if "result" in atr_response else str(atr_response)

    requests.post(
        'https://slack.com/api/chat.postMessage',
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        json={"channel": channel_id, "text": atr_message}
    )

    return '', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


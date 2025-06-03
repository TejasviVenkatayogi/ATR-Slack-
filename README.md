
# Flask Slack ATR App

This is a Flask application that connects Slack with ATR using a slash command.

## Setup Instructions

1. Create a GitHub repository and push these files.
2. Go to [Render.com](https://render.com) and create a new Web Service.
3. Connect your GitHub repo to Render.
4. Set the start command: `python app.py`.
5. Render will provide a public URL. Use it in your Slack Slash Command.
6. Test in Slack with `/atrquery Hello`.

## Files
- app.py: Flask application
- requirements.txt: Required Python packages
- render.yaml: Render deployment configuration

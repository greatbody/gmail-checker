# Mail Checker

A Python script that monitors Gmail for unread emails, analyzes their importance using Deepseek API, and sends notifications for important emails via Enterprise WeChat webhook.

## Setup

1. Set up virtual environment:
```bash
# Make setup script executable
chmod +x setup.sh

# Run setup script
./setup.sh

# Activate virtual environment
source venv/bin/activate
```

2. Set up Gmail API:
   a. Go to [Google Cloud Console](https://console.cloud.google.com/)
   b. Create a new project or select an existing one
   c. Enable the Gmail API:
      - In the sidebar, navigate to "APIs & Services" > "Library"
      - Search for "Gmail API"
      - Click "Enable"
   d. Create OAuth 2.0 credentials:
      - Go to "APIs & Services" > "Credentials"
      - Click "Create Credentials" > "OAuth client ID"
      - Choose "Desktop application" as the application type
      - Give it a name (e.g., "Mail Checker")
      - Click "Create"
      - Download the credentials JSON file
      - Rename it to `credentials.json` and place it in your project root directory
   
   Note: The `token.json` file will be automatically created when you first run the script.

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Add your Deepseek API key
   - Add your Enterprise WeChat webhook URL

## Usage

Make sure the virtual environment is activated:
```bash
source venv/bin/activate
```

Run the script:
```bash
python mail_checker.py
```

On first run:
1. A browser window will open automatically
2. Sign in to your Google account
3. Grant the requested permissions to access your Gmail
4. The script will automatically create `token.json` for future use

## Features

- Monitors unread emails in Gmail
- Analyzes email importance using Deepseek AI
- Sends notifications for important emails via Enterprise WeChat
- Supports markdown formatting in WeChat notifications

## Note

- Make sure to keep your API keys and credentials secure. Never commit them to version control.
- Always run the script within the virtual environment to ensure proper dependency isolation.
- If you encounter authentication issues, delete `token.json` and run the script again to re-authenticate. 
import os
import base64
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Gmail API configuration
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.modify"  # Add modify scope for label changes
]

# File paths
DATA_DIR = "data"
TOKEN_PATH = os.path.join(DATA_DIR, "token.json")
CREDENTIALS_PATH = os.path.join(DATA_DIR, "credentials.json")

def get_gmail_service():
    """Get Gmail API service instance."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(f"Credentials file not found at {CREDENTIALS_PATH}")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Ensure data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def create_processed_label(service):
    """Create 'Processed' label if it doesn't exist."""
    try:
        # Try to get the label first
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])

        for label in labels:
            if label["name"] == "Processed":
                return label["id"]

        # Create label if it doesn't exist
        label = {
            "name": "Processed",
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
        created_label = (
            service.users().labels().create(userId="me", body=label).execute()
        )
        return created_label["id"]
    except Exception as e:
        print(f"Error creating label: {str(e)}")
        return None


def mark_as_processed(service, message_id, label_id):
    """Add 'Processed' label to the email."""
    try:
        service.users().messages().modify(
            userId="me", id=message_id, body={"addLabelIds": [label_id]}
        ).execute()
        print(f"Marked message {message_id} as processed")
    except Exception as e:
        print(f"Error marking message as processed: {str(e)}")


def get_unread_emails(service):
    """Fetch unread emails from Gmail."""
    try:
        # Modify the query to exclude processed emails
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["UNREAD"],
                q="-label:Processed",  # Exclude emails with Processed label
            )
            .execute()
        )

        messages = results.get("messages", [])
        if not messages:
            return []

        emails = []
        for message in messages:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=message["id"], format="full")
                .execute()
            )

            headers = msg["payload"]["headers"]
            subject = next(
                h["value"] for h in headers if h["name"].lower() == "subject"
            )
            print("Found subject: ", subject)
            # Get email body
            if "parts" in msg["payload"]:
                parts = msg["payload"]["parts"]
                data = parts[0]["body"].get("data", "")
            else:
                data = msg["payload"]["body"].get("data", "")

            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8")
            else:
                body = ""

            emails.append({"id": message["id"], "subject": subject, "body": body})

        return emails
    except Exception as e:
        print(f"Error fetching emails: {str(e)}")
        return []


def analyze_with_deepseek(subject, body):
    """Analyze email importance using Deepseek API."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    api_url = (
        os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
        + "/chat/completions"
    )

    system_prompt = """You are an email importance analyzer. Your task is to determine if an email is important based on its subject and content. 
Analyze the urgency, sender's role, content significance, and required actions. Respond with a JSON object containing 'is_important' (boolean) and 'reason' (string)."""

    user_prompt = f"""Email Subject: {subject}
Email Content: {body}

Analyze this email and determine if it's important. Consider:
- Urgency of the matter
- Sender's role and relationship
- Content significance
- Required actions

Respond ONLY with a valid JSON object containing:
{{"is_important": boolean, "reason": "string"}}, remember the reason should be written in Chinese"""

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 500,
        "stream": False,
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

        if "choices" not in result or not result["choices"]:
            print("No choices in response")
            return None

        content = result["choices"][0]["message"]["content"]

        return json.loads(content)
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return None
    except Exception as e:
        print(f"Other error: {str(e)}")
        return None


def send_wechat_notification(email_data, analysis):
    """Send notification to Enterprise WeChat."""
    webhook_url = os.getenv("WECHAT_WEBHOOK_URL")

    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"""### 重要邮件提醒
> **主题**: {email_data['subject']}
> **重要原因**: {analysis['reason']}

邮件内容预览:
{email_data['body'][:200]}..."""
        },
    }

    try:
        response = requests.post(webhook_url, json=message)
        response.raise_for_status()
        print("WeChat notification sent successfully")
    except Exception as e:
        print(f"Error sending WeChat notification: {str(e)}")


def main():
    # Initialize Gmail service
    service = get_gmail_service()

    # Create or get the Processed label
    processed_label_id = create_processed_label(service)
    if not processed_label_id:
        print("Failed to create/get Processed label")
        return

    # Get unread emails
    unread_emails = get_unread_emails(service)

    for email in unread_emails:
        # Analyze email importance
        print("Analyzing email: ", email["subject"])
        analysis = analyze_with_deepseek(email["subject"], email["body"])

        if analysis and analysis["is_important"]:
            # Send notification for important emails
            send_wechat_notification(email, analysis)

        # Mark email as processed
        mark_as_processed(service, email["id"], processed_label_id)


if __name__ == "__main__":
    main()

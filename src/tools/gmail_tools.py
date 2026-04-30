"""
Gmail Integration Tools
Handles reading important unread emails from the user's Gmail account.
"""

import os.path
import base64
from typing import Dict, Any, List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import dateutil.parser as parser

# If modifying these scopes, delete the file token.json.
# Using ReadOnly scope for security
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']

# Paths
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'credentials.json')
TOKEN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'token.json')


def _get_gmail_service():
    """Gets an authenticated Gmail API service instance."""
    creds = None

    # Check if we have an existing token
    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception as e:
            print(f"Error loading existing token: {e}")

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed: {e}")
                creds = None

        if not creds:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Gmail API credentials not found at {CREDENTIALS_PATH}. "
                    "Please download OAuth Client ID JSON from Google Cloud Console."
                )

            # Start local server to handle authentication flow
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            print("\n" + "="*60)
            print("GMAIL AUTHENTICATION REQUIRED")
            print("Opening browser to authorize ARIA to read your emails...")
            print("="*60 + "\n")

            # Use fixed port to avoid issues
            creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def _get_header(headers: list, name: str) -> str:
    """Extract a specific header value from email headers."""
    for header in headers:
        if header['name'].lower() == name.lower():
            return header['value']
    return ""


def _decode_body(payload: dict) -> str:
    """Decode the email body from base64url format."""
    body = ""

    # If it's a simple text email
    if 'data' in payload.get('body', {}):
        try:
            data = payload['body']['data']
            # Replace URL-safe base64 characters
            data = data.replace('-', '+').replace('_', '/')
            # Pad with '=' if necessary
            data += '=' * (-len(data) % 4)
            # Decode
            body = base64.b64decode(data).decode('utf-8')
        except Exception:
            pass

    # If it's a multipart email
    elif 'parts' in payload:
        for part in payload['parts']:
            # Prefer plain text over HTML
            if part.get('mimeType') == 'text/plain':
                body += _decode_body(part)
            # Recursively check nested parts
            elif part.get('mimeType', '').startswith('multipart/'):
                body += _decode_body(part)

    return body


def get_important_unread_emails(max_results: int = 5) -> Dict[str, Any]:
    """
    Retrieves important unread emails from the user's Gmail inbox.
    Uses Gmail's built-in importance markers.

    Args:
        max_results: Maximum number of emails to retrieve (default: 5)

    Returns:
        dict: List of formatted emails with sender, subject, and snippet
    """
    try:
        service = _get_gmail_service()

        # Query for unread emails that Gmail marks as important
        # The 'is:important' flag uses Google's AI to filter out newsletters/spam
        query = "is:unread is:important"

        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            return {
                "success": True,
                "message": "You have no important unread emails right now.",
                "data": {"emails": [], "count": 0}
            }

        email_data = []

        for msg in messages:
            # Get full message details
            msg_detail = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()

            headers = msg_detail['payload']['headers']

            # Extract key information
            subject = _get_header(headers, 'Subject') or "No Subject"
            sender = _get_header(headers, 'From') or "Unknown Sender"
            date_str = _get_header(headers, 'Date')

            # Clean up sender name (remove email address if name exists)
            sender_name = sender.split('<')[0].strip().replace('"', '') if '<' in sender else sender

            # Get snippet (Gmail's auto-generated preview)
            snippet = msg_detail.get('snippet', '')

            # Optionally get full body if snippet is too short
            body = ""
            if len(snippet) < 20:
                body = _decode_body(msg_detail['payload'])
                # Truncate body if it's too long
                if len(body) > 200:
                    body = body[:197] + "..."

            # Format date for better reading
            try:
                date_obj = parser.parse(date_str)
                formatted_date = date_obj.strftime("%I:%M %p")
            except Exception:
                formatted_date = date_str

            email_data.append({
                "id": msg['id'],
                "sender": sender_name,
                "subject": subject,
                "snippet": snippet or body,
                "time": formatted_date
            })

        return {
            "success": True,
            "message": f"Found {len(email_data)} important unread emails.",
            "data": {
                "emails": email_data,
                "count": len(email_data)
            },
            "summary": f"You have {len(email_data)} important unread emails." +
                      (" The latest is from " + email_data[0]["sender"] + " about '" + email_data[0]["subject"] + "'." if email_data else "")
        }

    except HttpError as error:
        error_msg = f"An API error occurred: {error}"
        print(error_msg)
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}


def read_specific_email(email_id: str) -> Dict[str, Any]:
    """
    Reads the full content of a specific email.

    Args:
        email_id: The ID of the email to read

    Returns:
        dict: Full email content and details
    """
    try:
        service = _get_gmail_service()

        msg_detail = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()

        headers = msg_detail['payload']['headers']

        subject = _get_header(headers, 'Subject') or "No Subject"
        sender = _get_header(headers, 'From') or "Unknown Sender"
        date_str = _get_header(headers, 'Date')

        # Get full body
        body = _decode_body(msg_detail['payload'])

        # Mark as read (remove UNREAD label)
        # Note: This requires modify permissions, so we skip it if we only have readonly
        if 'https://www.googleapis.com/auth/gmail.modify' in SCOPES:
            service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

        return {
            "success": True,
            "message": f"Reading email: {subject}",
            "data": {
                "id": email_id,
                "sender": sender,
                "subject": subject,
                "date": date_str,
                "body": body.strip()
            }
        }

    except Exception as e:
        error_msg = f"An error occurred: {str(e)}"
        return {"success": False, "error": error_msg}


def send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Sends an email using the user's Gmail account.
    
    Args:
        to (str): Recipient email address.
        subject (str): Subject of the email.
        body (str): Body content of the email.
        
    Returns:
        dict: Success status and message
    """
    try:
        from email.mime.text import MIMEText
        import base64
        
        service = _get_gmail_service()
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw_msg = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': raw_msg}
        
        service.users().messages().send(userId='me', body=create_message).execute()
        return {'success': True, 'message': f'Email sent successfully to {to}.'}
    except Exception as e:
        return {'success': False, 'error': str(e), 'message': 'Failed to send email.'}

"""Gmail provider implementation using the Gmail API."""

import base64
import logging
import pickle
import json
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from stoppls.email_providers.base import EmailMessage, EmailProvider


class GmailProvider(EmailProvider):
    """Gmail provider implementation using the Gmail API."""

    # Gmail API scopes
    SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

    def __init__(self, credentials_path: str, token_path: str):
        """Initialize the Gmail provider.

        Args:
            credentials_path: Path to the credentials.json file.
            token_path: Path to store the token.json file.
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.logger = logging.getLogger(__name__)

    def _load_credentials(self):
        """Load credentials from the token file.

        Returns:
            dict: The credentials as a dictionary, or None if not found.
        """
        try:
            token_path = Path(self.token_path)
            if token_path.exists():
                with open(token_path, "rb") as token:
                    creds = pickle.load(token)
                    if creds and creds.valid:
                        return json.loads(creds.to_json())
            
            # If we get here, either the token doesn't exist or is invalid
            return None
        except Exception as e:
            self.logger.error(f"Error loading credentials: {e}")
            return None

    def connect(self) -> bool:
        """Connect to the Gmail API.

        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            creds = None
            token_path = Path(self.token_path)

            # Load existing token if it exists
            if token_path.exists():
                with open(token_path, "rb") as token:
                    creds = pickle.load(token)

            # If credentials don't exist or are invalid, refresh or create new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save the credentials for the next run
                with open(token_path, "wb") as token:
                    pickle.dump(creds, token)

            # Build the Gmail API service
            self.service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            return True

        except Exception as e:
            self.logger.error(f"Error connecting to Gmail API: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from the Gmail API.

        Returns:
            bool: True if disconnection was successful, False otherwise.
        """
        if self.service:
            self.service.close()
            self.service = None
            return True
        return False

    def is_connected(self) -> bool:
        """Check if currently connected to the Gmail API.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self.service is not None

    def get_messages(
        self,
        from_addresses: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[EmailMessage]:
        """Retrieve messages from Gmail.

        Args:
            from_addresses: Optional list of sender email addresses to filter by.
            since: Optional datetime to filter messages received after this time.
            limit: Maximum number of messages to retrieve.

        Returns:
            List[EmailMessage]: List of email messages.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Gmail API")

        # Build the query
        query_parts = []

        if from_addresses:
            from_query = " OR ".join([f"from:{addr}" for addr in from_addresses])
            query_parts.append(f"({from_query})")

        if since:
            timestamp = int(since.timestamp())
            query_parts.append(f"after:{timestamp}")

        query = " ".join(query_parts) if query_parts else ""

        # Get message IDs
        results = (
            self.service.users()
            .messages()
            .list(userId="me", q=query, maxResults=limit)
            .execute()
        )

        messages = results.get("messages", [])
        email_messages = []

        # Get full message details for each message ID
        for msg in messages:
            msg_id = msg["id"]
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )

            # Extract message details
            email_msg = self._parse_message(message)
            email_messages.append(email_msg)

        return email_messages

    def _create_reply(
        self,
        original_message: EmailMessage,
        reply_text: str,
        reply_html: Optional[str] = None,
    ) -> Dict:
        """Create a reply message for the Gmail API.

        Args:
            original_message: The original message to reply to.
            reply_text: The plain text content of the reply.
            reply_html: Optional HTML content of the reply.

        Returns:
            Dict: The message in the format expected by the Gmail API.
        """
        # Create message
        message = MIMEMultipart("alternative")
        message["To"] = original_message.sender
        message["Subject"] = f"Re: {original_message.subject}"
        message["In-Reply-To"] = original_message.message_id
        message["References"] = original_message.message_id

        # Attach parts
        message.attach(MIMEText(reply_text, "plain"))
        if reply_html:
            message.attach(MIMEText(reply_html, "html"))

        # Encode message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Create the message body
        return {"raw": encoded_message, "threadId": original_message.thread_id}

    def send_reply(
        self,
        original_message: EmailMessage,
        reply_text: str,
        reply_html: Optional[str] = None,
    ) -> bool:
        """Send a reply to an email message.

        Args:
            original_message: The original message to reply to.
            reply_text: The plain text content of the reply.
            reply_html: Optional HTML content of the reply.

        Returns:
            bool: True if the reply was sent successfully, False otherwise.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Gmail API")

        try:
            # Create the reply message
            message = self._create_reply(original_message, reply_text, reply_html)

            # Send the message
            self.service.users().messages().send(userId="me", body=message).execute()
            self.logger.info(f"Sent reply to: {original_message.sender}")
            return True

        except Exception as e:
            self.logger.error(f"Error sending reply: {e}")
            return False

    def archive_message(self, message: EmailMessage) -> bool:
        """Archive an email message.

        Args:
            message: The message to archive.

        Returns:
            bool: True if the message was archived successfully, False otherwise.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Gmail API")

        try:
            # Remove INBOX label
            self.service.users().messages().modify(
                userId="me", id=message.message_id, body={"removeLabelIds": ["INBOX"]}
            ).execute()
            self.logger.info(f"Archived message: {message.subject}")
            return True

        except Exception as e:
            self.logger.error(f"Error archiving message: {e}")
            return False

    def apply_label(self, message: EmailMessage, label: str) -> bool:
        """Apply a label to an email message.

        Args:
            message: The message to label.
            label: The label to apply.

        Returns:
            bool: True if the label was applied successfully, False otherwise.

        Raises:
            ConnectionError: If not connected to the email provider.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Gmail")

        try:
            # Check if the label exists, create it if it doesn't
            label_id = self._get_or_create_label(label)

            # Apply the label to the message
            self.service.users().messages().modify(
                userId="me",
                id=message.message_id,
                body={"addLabelIds": [label_id]},
            ).execute()

            self.logger.info(f"Applied label '{label}' to message: {message.subject}")
            return True

        except Exception as e:
            self.logger.error(f"Error applying label to message: {e}")
            return False

    def _get_or_create_label(self, label_name: str) -> str:
        """Get a label ID by name, creating it if it doesn't exist.

        Args:
            label_name: The name of the label.

        Returns:
            str: The label ID.
        """
        # List all labels
        results = self.service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])

        # Check if label exists
        for label in labels:
            if label["name"] == label_name:
                return label["id"]

        # Create label if it doesn't exist
        label = {
            "name": label_name,
        }
        created_label = (
            self.service.users().labels().create(userId="me", body=label).execute()
        )
        return created_label["id"]

    def send_email(
        self, to: str, subject: str, body_text: str, body_html: Optional[str] = None
    ) -> bool:
        """Send an email.

        Args:
            to: The recipient email address.
            subject: The subject of the email.
            body_text: The plain text content of the email.
            body_html: The HTML content of the email (optional).

        Returns:
            bool: True if the email was sent successfully, False otherwise.

        Raises:
            ConnectionError: If not connected to the email provider.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Gmail")

        try:
            # Create the message
            message = self._create_message(
                to=to,
                subject=subject,
                body_text=body_text,
                body_html=body_html
            )

            # Send the message
            self.service.users().messages().send(
                userId="me",
                body=message
            ).execute()

            self.logger.info(f"Sent email to {to} with subject: {subject}")
            return True

        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False
            
    def _create_message(
        self, to: str, subject: str, body_text: str, body_html: Optional[str] = None
    ) -> Dict:
        """Create a message for the Gmail API.

        Args:
            to: The recipient email address.
            subject: The subject of the email.
            body_text: The plain text content of the email.
            body_html: The HTML content of the email (optional).

        Returns:
            Dict: The message in the format expected by the Gmail API.
        """
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import base64

        # Create the message container
        message = MIMEMultipart("alternative")
        message["to"] = to
        message["subject"] = subject

        # Add the plain text part
        text_part = MIMEText(body_text, "plain")
        message.attach(text_part)

        # Add the HTML part if provided
        if body_html:
            html_part = MIMEText(body_html, "html")
            message.attach(html_part)

        # Encode the message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        return {"raw": encoded_message}
        
    def _parse_message(self, message: Dict[str, Any]) -> EmailMessage:
        """Parse a Gmail API message into an EmailMessage.

        Args:
            message: The Gmail API message.

        Returns:
            EmailMessage: The parsed email message.
        """
        # Extract headers
        headers = {
            header["name"]: header["value"] for header in message["payload"]["headers"]
        }

        # Get message ID
        message_id = message["id"]

        # Get thread ID
        thread_id = message["threadId"]

        # Get sender
        sender = headers.get("From", "")

        # Get recipients
        to_header = headers.get("To", "")
        recipients = [r.strip() for r in to_header.split(",")] if to_header else []

        # Get subject
        subject = headers.get("Subject", "(No Subject)")

        # Get date
        date_str = headers.get("Date", "")
        date = None
        if date_str:
            try:
                # This is a simplified approach - real implementation would need
                # more robust date parsing
                date = datetime.strptime(date_str[:25], "%a, %d %b %Y %H:%M:%S")
            except ValueError:
                pass

        # Extract body
        body_text = ""
        body_html = None

        if "parts" in message["payload"]:
            for part in message["payload"]["parts"]:
                if part["mimeType"] == "text/plain":
                    body_text = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )
                elif part["mimeType"] == "text/html":
                    body_html = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )
        elif "body" in message["payload"] and "data" in message["payload"]["body"]:
            body_text = base64.urlsafe_b64decode(
                message["payload"]["body"]["data"]
            ).decode("utf-8")

        # Create EmailMessage
        return EmailMessage(
            message_id=message_id,
            thread_id=thread_id,
            sender=sender,
            recipients=recipients,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            date=date,
        )

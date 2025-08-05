"""In-memory email provider for testing."""

from datetime import datetime
from typing import Dict, List, Optional

from stoppls.email_providers.base import EmailMessage, EmailProvider


class InMemoryEmailProvider(EmailProvider):
    """In-memory email provider for testing.

    This provider stores messages in memory and doesn't interact with any external services.
    It's useful for testing and integration tests.
    """

    def __init__(self):
        """Initialize the in-memory email provider."""
        self._connected = False
        self.messages: List[EmailMessage] = []
        self.replied_messages: List[Dict] = []
        self.archived_messages: List[EmailMessage] = []
        self.labeled_messages: List[Dict] = []
        self.sent_emails: List[Dict] = []

    def connect(self) -> bool:
        """Connect to the email provider.

        Returns:
            bool: True if connection was successful, False otherwise.
        """
        self._connected = True
        return True

    def disconnect(self) -> bool:
        """Disconnect from the email provider.

        Returns:
            bool: True if disconnection was successful, False otherwise.
        """
        self._connected = False
        return True

    def is_connected(self) -> bool:
        """Check if connected to the email provider.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self._connected

    def get_messages(
        self, from_addresses: Optional[List[str]] = None, since: Optional[datetime] = None, limit: int = 10
    ) -> List[EmailMessage]:
        """Get messages from the email provider.

        Args:
            from_addresses: List of email addresses to filter by.
            since: Only return messages received after this time.
            limit: Maximum number of messages to return.

        Returns:
            List[EmailMessage]: List of email messages.

        Raises:
            ConnectionError: If not connected to the email provider.
        """
        if not self._connected:
            raise ConnectionError("Not connected to email provider")

        filtered_messages = self.messages.copy()

        # Filter by from_addresses if provided
        if from_addresses:
            filtered_messages = [
                msg
                for msg in filtered_messages
                if any(addr.lower() in msg.sender.lower() for addr in from_addresses)
            ]

        # Filter by since if provided
        if since:
            filtered_messages = [
                msg for msg in filtered_messages if msg.date and msg.date > since
            ]

        return filtered_messages[:limit]

    def send_reply(
        self, original_message: EmailMessage, reply_text: str, reply_html: Optional[str] = None
    ) -> bool:
        """Send a reply to an email message.

        Args:
            original_message: The original message to reply to.
            reply_text: The plain text content of the reply.
            reply_html: The HTML content of the reply (optional).

        Returns:
            bool: True if the reply was sent successfully, False otherwise.

        Raises:
            ConnectionError: If not connected to the email provider.
        """
        if not self._connected:
            raise ConnectionError("Not connected to email provider")

        self.replied_messages.append({
            "original_message": original_message,
            "reply_text": reply_text,
            "reply_html": reply_html,
        })
        return True

    def archive_message(self, message: EmailMessage) -> bool:
        """Archive an email message.

        Args:
            message: The message to archive.

        Returns:
            bool: True if the message was archived successfully, False otherwise.

        Raises:
            ConnectionError: If not connected to the email provider.
        """
        if not self._connected:
            raise ConnectionError("Not connected to email provider")

        self.archived_messages.append(message)
        return True

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
        if not self._connected:
            raise ConnectionError("Not connected to email provider")

        self.labeled_messages.append({
            "message": message,
            "label": label,
        })
        return True
        
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
        if not self._connected:
            raise ConnectionError("Not connected to email provider")

        self.sent_emails.append({
            "to": to,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "timestamp": datetime.now(),
        })
        return True

    def add_message(self, message: EmailMessage) -> None:
        """Add a message to the in-memory provider.

        This method is specific to the in-memory provider and is used for testing.

        Args:
            message: The message to add.
        """
        self.messages.append(message)

    def clear_messages(self) -> None:
        """Clear all messages from the in-memory provider.

        This method is specific to the in-memory provider and is used for testing.
        """
        self.messages.clear()
        self.replied_messages.clear()
        self.archived_messages.clear()
        self.labeled_messages.clear()
        self.sent_emails.clear()
"""Base classes for email providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class EmailMessage:
    """Represents an email message.

    Attributes:
        message_id: Unique identifier for the message
        thread_id: Identifier for the thread the message belongs to
        sender: Email address of the sender
        recipients: List of recipient email addresses
        subject: Subject of the message
        body_text: Plain text body of the message
        body_html: HTML body of the message (optional)
        date: Date and time the message was sent
    """

    message_id: str
    thread_id: str
    sender: str
    recipients: List[str]
    subject: str
    body_text: str
    body_html: Optional[str] = None
    date: Optional[datetime] = None


class EmailProvider(ABC):
    """Abstract base class for email providers.

    This class defines the interface that all email providers must implement.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the email provider.

        Returns:
            bool: True if connection was successful, False otherwise.
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the email provider.

        Returns:
            bool: True if disconnection was successful, False otherwise.
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to the email provider.

        Returns:
            bool: True if connected, False otherwise.
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def archive_message(self, message: EmailMessage) -> bool:
        """Archive an email message.

        Args:
            message: The message to archive.

        Returns:
            bool: True if the message was archived successfully, False otherwise.

        Raises:
            ConnectionError: If not connected to the email provider.
        """
        pass

    @abstractmethod
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
        pass
        
    @abstractmethod
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
        pass

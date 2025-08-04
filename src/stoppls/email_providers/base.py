"""
Base interface for email providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class EmailMessage:
    """Data class representing an email message."""
    message_id: str
    sender: str
    recipients: List[str]
    subject: str
    body_text: str
    body_html: Optional[str] = None
    date: Optional[datetime] = None
    labels: Optional[List[str]] = None
    thread_id: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    raw_data: Optional[Dict[str, Any]] = None


class EmailProvider(ABC):
    """Base interface for email providers."""

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish a connection to the email provider.
        
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the email provider.
        
        Returns:
            bool: True if disconnection was successful, False otherwise.
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if currently connected to the email provider.
        
        Returns:
            bool: True if connected, False otherwise.
        """
        pass
    
    @abstractmethod
    def get_messages(self, 
                     from_addresses: Optional[List[str]] = None, 
                     since: Optional[datetime] = None,
                     limit: int = 10) -> List[EmailMessage]:
        """
        Retrieve messages from the email provider.
        
        Args:
            from_addresses: Optional list of sender email addresses to filter by.
            since: Optional datetime to filter messages received after this time.
            limit: Maximum number of messages to retrieve.
            
        Returns:
            List[EmailMessage]: List of email messages.
        """
        pass
    
    @abstractmethod
    def send_reply(self, 
                  original_message: EmailMessage, 
                  reply_text: str,
                  reply_html: Optional[str] = None) -> bool:
        """
        Send a reply to an email message.
        
        Args:
            original_message: The original message to reply to.
            reply_text: The plain text content of the reply.
            reply_html: Optional HTML content of the reply.
            
        Returns:
            bool: True if the reply was sent successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def archive_message(self, message: EmailMessage) -> bool:
        """
        Archive an email message.
        
        Args:
            message: The message to archive.
            
        Returns:
            bool: True if the message was archived successfully, False otherwise.
        """
        pass
    
    @abstractmethod
    def apply_label(self, message: EmailMessage, label: str) -> bool:
        """
        Apply a label to an email message.
        
        Args:
            message: The message to label.
            label: The label to apply.
            
        Returns:
            bool: True if the label was applied successfully, False otherwise.
        """
        pass
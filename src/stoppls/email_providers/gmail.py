"""
Gmail provider implementation using the Gmail API.
"""
import base64
import os
import pickle
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from stoppls.email_providers.base import EmailProvider, EmailMessage


class GmailProvider(EmailProvider):
    """Gmail provider implementation using the Gmail API."""
    
    # Gmail API scopes
    SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
    
    def __init__(self, credentials_path: str, token_path: str):
        """
        Initialize the Gmail provider.
        
        Args:
            credentials_path: Path to the credentials.json file.
            token_path: Path to store the token.json file.
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
    
    def connect(self) -> bool:
        """
        Connect to the Gmail API.
        
        Returns:
            bool: True if connection was successful, False otherwise.
        """
        try:
            creds = None
            token_path = Path(self.token_path)
            
            # Load existing token if it exists
            if token_path.exists():
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # If credentials don't exist or are invalid, refresh or create new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            # Build the Gmail API service
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        
        except Exception as e:
            print(f"Error connecting to Gmail API: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect from the Gmail API.
        
        Returns:
            bool: True if disconnection was successful, False otherwise.
        """
        if self.service:
            self.service.close()
            self.service = None
            return True
        return False
    
    def is_connected(self) -> bool:
        """
        Check if currently connected to the Gmail API.
        
        Returns:
            bool: True if connected, False otherwise.
        """
        return self.service is not None
    
    def get_messages(self, 
                     from_addresses: Optional[List[str]] = None, 
                     since: Optional[datetime] = None,
                     limit: int = 10) -> List[EmailMessage]:
        """
        Retrieve messages from Gmail.
        
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
            # Format date as YYYY/MM/DD
            date_str = since.strftime("%Y/%m/%d")
            query_parts.append(f"after:{date_str}")
        
        query = " ".join(query_parts) if query_parts else ""
        
        # Get message IDs
        results = self.service.users().messages().list(
            userId='me', q=query, maxResults=limit).execute()
        
        messages = results.get('messages', [])
        email_messages = []
        
        # Get full message details for each message ID
        for msg in messages:
            msg_id = msg['id']
            message = self.service.users().messages().get(
                userId='me', id=msg_id, format='full').execute()
            
            # Extract message details
            email_msg = self._parse_message(message)
            email_messages.append(email_msg)
        
        return email_messages
    
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
        if not self.is_connected():
            raise ConnectionError("Not connected to Gmail API")
        
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['To'] = original_message.sender
            message['Subject'] = f"Re: {original_message.subject}"
            message['In-Reply-To'] = original_message.message_id
            message['References'] = original_message.message_id
            
            # Attach parts
            message.attach(MIMEText(reply_text, 'plain'))
            if reply_html:
                message.attach(MIMEText(reply_html, 'html'))
            
            # Encode message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Create the message body
            body = {
                'raw': encoded_message,
                'threadId': original_message.thread_id
            }
            
            # Send the message
            self.service.users().messages().send(userId='me', body=body).execute()
            return True
            
        except Exception as e:
            print(f"Error sending reply: {e}")
            return False
    
    def archive_message(self, message: EmailMessage) -> bool:
        """
        Archive an email message.
        
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
                userId='me',
                id=message.message_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            return True
            
        except Exception as e:
            print(f"Error archiving message: {e}")
            return False
    
    def apply_label(self, message: EmailMessage, label: str) -> bool:
        """
        Apply a label to an email message.
        
        Args:
            message: The message to label.
            label: The label to apply.
            
        Returns:
            bool: True if the label was applied successfully, False otherwise.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to Gmail API")
        
        try:
            # Check if label exists, create if not
            label_id = self._get_or_create_label(label)
            
            # Apply label
            self.service.users().messages().modify(
                userId='me',
                id=message.message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            return True
            
        except Exception as e:
            print(f"Error applying label: {e}")
            return False
    
    def _get_or_create_label(self, label_name: str) -> str:
        """
        Get a label ID by name, creating it if it doesn't exist.
        
        Args:
            label_name: The name of the label.
            
        Returns:
            str: The label ID.
        """
        # List all labels
        results = self.service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        # Check if label exists
        for label in labels:
            if label['name'] == label_name:
                return label['id']
        
        # Create label if it doesn't exist
        label = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        created_label = self.service.users().labels().create(
            userId='me', body=label).execute()
        return created_label['id']
    
    def _parse_message(self, message: Dict[str, Any]) -> EmailMessage:
        """
        Parse a Gmail API message into an EmailMessage.
        
        Args:
            message: The Gmail API message.
            
        Returns:
            EmailMessage: The parsed email message.
        """
        # Extract headers
        headers = {header['name']: header['value'] 
                  for header in message['payload']['headers']}
        
        # Get message ID
        message_id = message['id']
        
        # Get thread ID
        thread_id = message['threadId']
        
        # Get sender
        sender = headers.get('From', '')
        
        # Get recipients
        to_header = headers.get('To', '')
        recipients = [r.strip() for r in to_header.split(',')] if to_header else []
        
        # Get subject
        subject = headers.get('Subject', '(No Subject)')
        
        # Get date
        date_str = headers.get('Date', '')
        date = None
        if date_str:
            try:
                # This is a simplified approach - real implementation would need
                # more robust date parsing
                date = datetime.strptime(date_str[:25], '%a, %d %b %Y %H:%M:%S')
            except ValueError:
                pass
        
        # Get labels
        labels = message.get('labelIds', [])
        
        # Extract body
        body_text = ""
        body_html = None
        
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body_text = base64.urlsafe_b64decode(
                        part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    body_html = base64.urlsafe_b64decode(
                        part['body']['data']).decode('utf-8')
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            body_text = base64.urlsafe_b64decode(
                message['payload']['body']['data']).decode('utf-8')
        
        # Create EmailMessage
        return EmailMessage(
            message_id=message_id,
            sender=sender,
            recipients=recipients,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            date=date,
            labels=labels,
            thread_id=thread_id,
            attachments=None,  # Attachment parsing would be added in a real implementation
            raw_data=message
        )
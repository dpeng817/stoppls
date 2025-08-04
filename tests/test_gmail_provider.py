"""
Tests for the Gmail provider.
"""
import os
import pickle
from datetime import datetime
from unittest.mock import MagicMock, patch, mock_open

import pytest
from googleapiclient.discovery import build

from stoppls.email_providers.base import EmailMessage
from stoppls.email_providers.gmail import GmailProvider


class TestGmailProvider:
    """Tests for the GmailProvider class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.credentials_path = "config/credentials.json"
        self.token_path = "config/token.json"
        self.provider = GmailProvider(self.credentials_path, self.token_path)
    
    @patch('stoppls.email_providers.gmail.build')
    @patch('stoppls.email_providers.gmail.InstalledAppFlow.from_client_secrets_file')
    @patch('stoppls.email_providers.gmail.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.load')
    @patch('pickle.dump')
    def test_connect_new_credentials(self, mock_pickle_dump, mock_pickle_load, 
                                    mock_open_file, mock_path_exists, 
                                    mock_flow, mock_build):
        """Test connecting with new credentials."""
        # Mock path.exists to return False (no token file)
        mock_path_exists.return_value = False
        
        # Mock the flow and credentials
        mock_creds = MagicMock()
        mock_flow.return_value.run_local_server.return_value = mock_creds
        
        # Mock the build function
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Call connect
        result = self.provider.connect()
        
        # Assertions
        assert result is True
        mock_flow.assert_called_once_with(self.credentials_path, GmailProvider.SCOPES)
        mock_flow.return_value.run_local_server.assert_called_once_with(port=0)
        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_creds)
        mock_pickle_dump.assert_called_once()
        assert self.provider.service == mock_service

    
    @patch('stoppls.email_providers.gmail.build')
    @patch('stoppls.email_providers.gmail.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.load')
    def test_connect_existing_valid_credentials(self, mock_pickle_load, 
                                              mock_open_file, mock_path_exists, 
                                              mock_build):
        """Test connecting with existing valid credentials."""
        # Mock path.exists to return True (token file exists)
        mock_path_exists.return_value = True
        
        # Mock the credentials
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_pickle_load.return_value = mock_creds
        
        # Mock the build function
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Call connect
        result = self.provider.connect()
        
        # Assertions
        assert result is True
        mock_pickle_load.assert_called_once()
        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_creds)
        assert self.provider.service == mock_service
    
    @patch('stoppls.email_providers.gmail.build')
    @patch('stoppls.email_providers.gmail.Request')
    @patch('stoppls.email_providers.gmail.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('pickle.load')
    @patch('pickle.dump')
    def test_connect_refresh_expired_credentials(self, mock_pickle_dump, 
                                               mock_pickle_load, mock_open_file, 
                                               mock_path_exists, mock_request, 
                                               mock_build):
        """Test connecting with expired credentials that need refreshing."""
        # Mock path.exists to return True (token file exists)
        mock_path_exists.return_value = True
        
        # Mock the credentials
        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = True
        mock_pickle_load.return_value = mock_creds
        
        # Mock the build function
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Call connect
        result = self.provider.connect()
        
        # Assertions
        assert result is True
        mock_pickle_load.assert_called_once()
        mock_creds.refresh.assert_called_once()
        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_creds)
        mock_pickle_dump.assert_called_once()
        assert self.provider.service == mock_service
    
    def test_disconnect_when_connected(self):
        """Test disconnecting when connected."""
        # Set up a mock service
        mock_service = MagicMock()
        self.provider.service = mock_service
        
        # Call disconnect
        result = self.provider.disconnect()
        
        # Assertions
        assert result is True
        mock_service.close.assert_called_once()
        assert self.provider.service is None
    
    def test_disconnect_when_not_connected(self):
        """Test disconnecting when not connected."""
        # Ensure service is None
        self.provider.service = None
        
        # Call disconnect
        result = self.provider.disconnect()
        
        # Assertions
        assert result is False
    
    def test_is_connected_when_connected(self):
        """Test is_connected when connected."""
        # Set up a mock service
        self.provider.service = MagicMock()
        
        # Call is_connected
        result = self.provider.is_connected()
        
        # Assertions
        assert result is True
    
    def test_is_connected_when_not_connected(self):
        """Test is_connected when not connected."""
        # Ensure service is None
        self.provider.service = None
        
        # Call is_connected
        result = self.provider.is_connected()
        
        # Assertions
        assert result is False
    
    def test_get_messages_when_not_connected(self):
        """Test get_messages when not connected."""
        # Ensure service is None
        self.provider.service = None
        
        # Call get_messages and expect an exception
        with pytest.raises(ConnectionError):
            self.provider.get_messages()
    
    @patch('stoppls.email_providers.gmail.GmailProvider._parse_message')
    def test_get_messages_with_no_filters(self, mock_parse_message):
        """Test get_messages with no filters."""
        # Set up a mock service
        self.provider.service = MagicMock()
        
        # Mock the messages.list response
        mock_messages_list = MagicMock()
        self.provider.service.users().messages().list.return_value.execute.return_value = {
            'messages': [{'id': 'msg1'}, {'id': 'msg2'}]
        }
        
        # Mock the messages.get response
        mock_message1 = {'id': 'msg1', 'payload': {'headers': []}}
        mock_message2 = {'id': 'msg2', 'payload': {'headers': []}}
        
        def mock_get_side_effect(userId, id, format):
            if id == 'msg1':
                return MagicMock(execute=MagicMock(return_value=mock_message1))
            else:
                return MagicMock(execute=MagicMock(return_value=mock_message2))
        
        self.provider.service.users().messages().get.side_effect = mock_get_side_effect
        
        # Mock the parse_message method
        mock_email1 = EmailMessage(message_id='msg1', sender='sender1@example.com', 
                                  recipients=['recipient1@example.com'], 
                                  subject='Subject 1', body_text='Body 1')
        mock_email2 = EmailMessage(message_id='msg2', sender='sender2@example.com', 
                                  recipients=['recipient2@example.com'], 
                                  subject='Subject 2', body_text='Body 2')
        
        mock_parse_message.side_effect = [mock_email1, mock_email2]
        
        # Call get_messages
        result = self.provider.get_messages()
        
        # Assertions
        self.provider.service.users().messages().list.assert_called_once_with(
            userId='me', q='', maxResults=10)
        assert mock_parse_message.call_count == 2
        assert len(result) == 2
        assert result[0] == mock_email1
        assert result[1] == mock_email2
    
    @patch('stoppls.email_providers.gmail.GmailProvider._parse_message')
    def test_get_messages_with_from_filter(self, mock_parse_message):
        """Test get_messages with from_addresses filter."""
        # Set up a mock service
        self.provider.service = MagicMock()
        
        # Mock the messages.list response
        self.provider.service.users().messages().list.return_value.execute.return_value = {
            'messages': [{'id': 'msg1'}]
        }
        
        # Mock the messages.get response
        mock_message = {'id': 'msg1', 'payload': {'headers': []}}
        self.provider.service.users().messages().get.return_value.execute.return_value = mock_message
        
        # Mock the parse_message method
        mock_email = EmailMessage(message_id='msg1', sender='sender@example.com', 
                                recipients=['recipient@example.com'], 
                                subject='Subject', body_text='Body')
        mock_parse_message.return_value = mock_email
        
        # Call get_messages with from_addresses
        from_addresses = ['sender@example.com', 'other@example.com']
        result = self.provider.get_messages(from_addresses=from_addresses)
        
        # Assertions
        expected_query = "(from:sender@example.com OR from:other@example.com)"
        self.provider.service.users().messages().list.assert_called_once_with(
            userId='me', q=expected_query, maxResults=10)
        assert len(result) == 1
        assert result[0] == mock_email
    
    @patch('stoppls.email_providers.gmail.GmailProvider._parse_message')
    def test_get_messages_with_since_filter(self, mock_parse_message):
        """Test get_messages with since filter."""
        # Set up a mock service
        self.provider.service = MagicMock()
        
        # Mock the messages.list response
        self.provider.service.users().messages().list.return_value.execute.return_value = {
            'messages': [{'id': 'msg1'}]
        }
        
        # Mock the messages.get response
        mock_message = {'id': 'msg1', 'payload': {'headers': []}}
        self.provider.service.users().messages().get.return_value.execute.return_value = mock_message
        
        # Mock the parse_message method
        mock_email = EmailMessage(message_id='msg1', sender='sender@example.com', 
                                recipients=['recipient@example.com'], 
                                subject='Subject', body_text='Body')
        mock_parse_message.return_value = mock_email
        
        # Call get_messages with since
        since = datetime(2023, 1, 1)
        result = self.provider.get_messages(since=since)
        
        # Assertions
        expected_query = "after:2023/01/01"
        self.provider.service.users().messages().list.assert_called_once_with(
            userId='me', q=expected_query, maxResults=10)
        assert len(result) == 1
        assert result[0] == mock_email

    def test_send_reply_when_not_connected(self):
        """Test send_reply when not connected."""
        # Ensure service is None
        self.provider.service = None
        
        # Create a mock message
        mock_message = EmailMessage(
            message_id='msg1',
            sender='sender@example.com',
            recipients=['recipient@example.com'],
            subject='Subject',
            body_text='Body'
        )
        
        # Call send_reply and expect an exception
        with pytest.raises(ConnectionError):
            self.provider.send_reply(mock_message, "Reply text")
    
    @patch('stoppls.email_providers.gmail.base64.urlsafe_b64encode')
    def test_send_reply_success(self, mock_b64encode):
        """Test send_reply success."""
        # Set up a mock service
        self.provider.service = MagicMock()
        
        # Create a mock message
        mock_message = EmailMessage(
            message_id='msg1',
            sender='sender@example.com',
            recipients=['recipient@example.com'],
            subject='Subject',
            body_text='Body',
            thread_id='thread1'
        )
        
        # Mock base64 encoding
        mock_b64encode.return_value.decode.return_value = "encoded_message"
        
        # Call send_reply
        result = self.provider.send_reply(mock_message, "Reply text", "Reply HTML")
        
        # Assertions
        assert result is True
        self.provider.service.users().messages().send.assert_called_once_with(
            userId='me', 
            body={
                'raw': 'encoded_message',
                'threadId': 'thread1'
            }
        )
    
    def test_archive_message_when_not_connected(self):
        """Test archive_message when not connected."""
        # Ensure service is None
        self.provider.service = None
        
        # Create a mock message
        mock_message = EmailMessage(
            message_id='msg1',
            sender='sender@example.com',
            recipients=['recipient@example.com'],
            subject='Subject',
            body_text='Body'
        )
        
        # Call archive_message and expect an exception
        with pytest.raises(ConnectionError):
            self.provider.archive_message(mock_message)
    
    def test_archive_message_success(self):
        """Test archive_message success."""
        # Set up a mock service
        self.provider.service = MagicMock()
        
        # Create a mock message
        mock_message = EmailMessage(
            message_id='msg1',
            sender='sender@example.com',
            recipients=['recipient@example.com'],
            subject='Subject',
            body_text='Body'
        )
        
        # Call archive_message
        result = self.provider.archive_message(mock_message)
        
        # Assertions
        assert result is True
        self.provider.service.users().messages().modify.assert_called_once_with(
            userId='me',
            id='msg1',
            body={'removeLabelIds': ['INBOX']}
        )
    
    def test_apply_label_when_not_connected(self):
        """Test apply_label when not connected."""
        # Ensure service is None
        self.provider.service = None
        
        # Create a mock message
        mock_message = EmailMessage(
            message_id='msg1',
            sender='sender@example.com',
            recipients=['recipient@example.com'],
            subject='Subject',
            body_text='Body'
        )
        
        # Call apply_label and expect an exception
        with pytest.raises(ConnectionError):
            self.provider.apply_label(mock_message, "TestLabel")
    
    @patch('stoppls.email_providers.gmail.GmailProvider._get_or_create_label')
    def test_apply_label_success(self, mock_get_or_create_label):
        """Test apply_label success."""
        # Set up a mock service
        self.provider.service = MagicMock()
        
        # Create a mock message
        mock_message = EmailMessage(
            message_id='msg1',
            sender='sender@example.com',
            recipients=['recipient@example.com'],
            subject='Subject',
            body_text='Body'
        )
        
        # Mock _get_or_create_label
        mock_get_or_create_label.return_value = "label123"
        
        # Call apply_label
        result = self.provider.apply_label(mock_message, "TestLabel")
        
        # Assertions
        assert result is True
        mock_get_or_create_label.assert_called_once_with("TestLabel")
        self.provider.service.users().messages().modify.assert_called_once_with(
            userId='me',
            id='msg1',
            body={'addLabelIds': ['label123']}
        )
    
    def test_get_or_create_label_existing(self):
        """Test _get_or_create_label with an existing label."""
        # Set up a mock service
        self.provider.service = MagicMock()
        
        # Mock the labels.list response
        self.provider.service.users().labels().list.return_value.execute.return_value = {
            'labels': [
                {'id': 'label1', 'name': 'Label1'},
                {'id': 'label2', 'name': 'TestLabel'},
                {'id': 'label3', 'name': 'Label3'}
            ]
        }
        
        # Call _get_or_create_label
        result = self.provider._get_or_create_label("TestLabel")
        
        # Assertions
        assert result == 'label2'
        self.provider.service.users().labels().list.assert_called_once_with(userId='me')
        self.provider.service.users().labels().create.assert_not_called()
    
    def test_get_or_create_label_new(self):
        """Test _get_or_create_label with a new label."""
        # Set up a mock service
        self.provider.service = MagicMock()
        
        # Mock the labels.list response
        self.provider.service.users().labels().list.return_value.execute.return_value = {
            'labels': [
                {'id': 'label1', 'name': 'Label1'},
                {'id': 'label3', 'name': 'Label3'}
            ]
        }
        
        # Mock the labels.create response
        self.provider.service.users().labels().create.return_value.execute.return_value = {
            'id': 'newlabel',
            'name': 'TestLabel'
        }
        
        # Call _get_or_create_label
        result = self.provider._get_or_create_label("TestLabel")
        
        # Assertions
        assert result == 'newlabel'
        self.provider.service.users().labels().list.assert_called_once_with(userId='me')
        self.provider.service.users().labels().create.assert_called_once_with(
            userId='me',
            body={
                'name': 'TestLabel',
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
        )
    
    def test_parse_message(self):
        """Test _parse_message."""
        # Create a mock Gmail API message
        mock_api_message = {
            'id': 'msg1',
            'threadId': 'thread1',
            'labelIds': ['INBOX', 'UNREAD'],
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'To', 'value': 'recipient1@example.com, recipient2@example.com'},
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'Date', 'value': 'Mon, 01 Jan 2023 12:34:56 +0000'}
                ],
                'parts': [
                    {
                        'mimeType': 'text/plain',
                        'body': {'data': 'VGVzdCBib2R5'}  # Base64 for "Test body"
                    },
                    {
                        'mimeType': 'text/html',
                        'body': {'data': 'PGgxPlRlc3QgYm9keTwvaDE+'}  # Base64 for "<h1>Test body</h1>"
                    }
                ]
            }
        }
        
        # Call _parse_message
        result = self.provider._parse_message(mock_api_message)
        
        # Assertions
        assert result.message_id == 'msg1'
        assert result.thread_id == 'thread1'
        assert result.sender == 'sender@example.com'
        assert result.recipients == ['recipient1@example.com', 'recipient2@example.com']
        assert result.subject == 'Test Subject'
        assert result.body_text == 'Test body'
        assert result.body_html == '<h1>Test body</h1>'
        assert result.labels == ['INBOX', 'UNREAD']
        assert result.date.year == 2023
        assert result.date.month == 1
        assert result.date.day == 1
        assert result.raw_data == mock_api_message
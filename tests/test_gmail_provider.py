"""Tests for the Gmail provider."""

import base64
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from stoppls.email_providers.base import EmailMessage
from stoppls.email_providers.gmail import GmailProvider


class TestGmailProvider:
    """Tests for the GmailProvider class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.provider = GmailProvider(
            credentials_path="test_credentials.json", token_path="test_token.pickle"
        )

    def test_init(self):
        """Test initialization."""
        assert self.provider.credentials_path == "test_credentials.json"
        assert self.provider.token_path == "test_token.pickle"
        assert self.provider.service is None
        assert not self.provider.is_connected()

    @patch("stoppls.email_providers.gmail.build")
    @patch("stoppls.email_providers.gmail.InstalledAppFlow.from_client_secrets_file")
    @patch("stoppls.email_providers.gmail.pickle.load")
    @patch("stoppls.email_providers.gmail.Path.exists")
    @patch("builtins.open", new_callable=MagicMock)
    def test_connect_success(
        self, mock_open, mock_exists, mock_pickle_load, mock_flow, mock_build
    ):
        """Test successful connection."""
        # Mock the token file exists
        mock_exists.return_value = True
        
        # Mock the credentials
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_pickle_load.return_value = mock_creds
        
        # Mock the service
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        # Connect
        result = self.provider.connect()
        
        # Verify the result
        assert result is True
        assert self.provider.service == mock_service
        assert self.provider.is_connected()

    @patch("stoppls.email_providers.gmail.InstalledAppFlow.from_client_secrets_file")
    @patch("stoppls.email_providers.gmail.Path.exists")
    def test_connect_no_credentials(self, mock_exists, mock_flow):
        """Test connection with no credentials."""
        # Mock the token file doesn't exist
        mock_exists.return_value = False
        
        # Mock the flow to raise an exception
        mock_flow.side_effect = Exception("Test error")
        
        # Connect
        result = self.provider.connect()
        
        # Verify the result
        assert result is False
        assert self.provider.service is None
        assert not self.provider.is_connected()

    @patch("stoppls.email_providers.gmail.build")
    @patch("stoppls.email_providers.gmail.InstalledAppFlow.from_client_secrets_file")
    @patch("stoppls.email_providers.gmail.pickle.load")
    @patch("stoppls.email_providers.gmail.Path.exists")
    @patch("builtins.open", new_callable=MagicMock)
    def test_connect_error(
        self, mock_open, mock_exists, mock_pickle_load, mock_flow, mock_build
    ):
        """Test connection error."""
        # Mock the token file exists
        mock_exists.return_value = True
        
        # Mock the credentials
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_pickle_load.return_value = mock_creds
        
        # Mock the service to raise an exception
        mock_build.side_effect = Exception("Test error")
        
        # Connect
        result = self.provider.connect()
        
        # Verify the result
        assert result is False
        assert self.provider.service is None
        assert not self.provider.is_connected()

    def test_disconnect(self):
        """Test disconnection."""
        # Set up a mock service
        self.provider.service = MagicMock()

        # Disconnect
        result = self.provider.disconnect()

        # Verify the result
        assert result is True
        assert self.provider.service is None
        assert not self.provider.is_connected()

    def test_is_connected(self):
        """Test is_connected."""
        # Initially not connected
        assert not self.provider.is_connected()

        # Set up a mock service
        self.provider.service = MagicMock()

        # Now connected
        assert self.provider.is_connected()

    def test_get_messages_when_not_connected(self):
        """Test get_messages when not connected."""
        # Ensure service is None
        self.provider.service = None

        # Call get_messages and expect an exception
        with pytest.raises(ConnectionError):
            self.provider.get_messages()

    @patch("stoppls.email_providers.gmail.GmailProvider._parse_message")
    def test_get_messages_with_no_filters(self, mock_parse_message):
        """Test get_messages with no filters."""
        # Set up a mock service
        self.provider.service = MagicMock()

        # Mock the messages.list response
        self.provider.service.users().messages().list.return_value.execute.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}]
        }

        # Mock the messages.get response
        mock_message1 = {"id": "msg1", "payload": {"headers": []}}
        mock_message2 = {"id": "msg2", "payload": {"headers": []}}

        def mock_get_side_effect(userId, id, format):
            if id == "msg1":
                return MagicMock(execute=MagicMock(return_value=mock_message1))
            else:
                return MagicMock(execute=MagicMock(return_value=mock_message2))

        self.provider.service.users().messages().get.side_effect = mock_get_side_effect

        # Mock the parse_message method
        mock_email1 = EmailMessage(
            message_id="msg1",
            thread_id="thread1",  # Add thread_id
            sender="sender1@example.com",
            recipients=["recipient1@example.com"],
            subject="Subject 1",
            body_text="Body 1",
        )
        mock_email2 = EmailMessage(
            message_id="msg2",
            thread_id="thread2",  # Add thread_id
            sender="sender2@example.com",
            recipients=["recipient2@example.com"],
            subject="Subject 2",
            body_text="Body 2",
        )

        def mock_parse_side_effect(message):
            if message["id"] == "msg1":
                return mock_email1
            else:
                return mock_email2

        mock_parse_message.side_effect = mock_parse_side_effect

        # Get messages
        messages = self.provider.get_messages()

        # Verify the messages
        assert len(messages) == 2
        assert messages[0] == mock_email1
        assert messages[1] == mock_email2

        # Verify the mocks were called with the correct arguments
        # Note: We're now expecting q="" in the call
        self.provider.service.users().messages().list.assert_called_once_with(
            userId="me", q="", maxResults=10
        )
        self.provider.service.users().messages().get.assert_any_call(
            userId="me", id="msg1", format="full"
        )
        self.provider.service.users().messages().get.assert_any_call(
            userId="me", id="msg2", format="full"
        )
        mock_parse_message.assert_any_call(mock_message1)
        mock_parse_message.assert_any_call(mock_message2)

    @patch("stoppls.email_providers.gmail.GmailProvider._parse_message")
    def test_get_messages_with_from_filter(self, mock_parse_message):
        """Test get_messages with from_addresses filter."""
        # Set up a mock service
        self.provider.service = MagicMock()

        # Mock the messages.list response
        self.provider.service.users().messages().list.return_value.execute.return_value = {
            "messages": [{"id": "msg1"}]
        }

        # Mock the messages.get response
        mock_message = {"id": "msg1", "payload": {"headers": []}}
        self.provider.service.users().messages().get.return_value.execute.return_value = mock_message

        # Mock the parse_message method
        mock_email = EmailMessage(
            message_id="msg1",
            thread_id="thread1",  # Add thread_id
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Subject",
            body_text="Body",
        )
        mock_parse_message.return_value = mock_email

        # Get messages with from_addresses filter
        messages = self.provider.get_messages(from_addresses=["sender@example.com"])

        # Verify the messages
        assert len(messages) == 1
        assert messages[0] == mock_email

        # Verify the mocks were called with the correct arguments
        # Note: We're now expecting q="(from:sender@example.com)" in the call
        self.provider.service.users().messages().list.assert_called_once_with(
            userId="me",
            q="(from:sender@example.com)",
            maxResults=10,
        )

    @patch("stoppls.email_providers.gmail.GmailProvider._parse_message")
    def test_get_messages_with_since_filter(self, mock_parse_message):
        """Test get_messages with since filter."""
        # Set up a mock service
        self.provider.service = MagicMock()

        # Mock the messages.list response
        self.provider.service.users().messages().list.return_value.execute.return_value = {
            "messages": [{"id": "msg1"}]
        }

        # Mock the messages.get response
        mock_message = {"id": "msg1", "payload": {"headers": []}}
        self.provider.service.users().messages().get.return_value.execute.return_value = mock_message

        # Mock the parse_message method
        mock_email = EmailMessage(
            message_id="msg1",
            thread_id="thread1",  # Add thread_id
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Subject",
            body_text="Body",
        )
        mock_parse_message.return_value = mock_email

        # Get messages with since filter
        since = datetime(2023, 1, 1)
        messages = self.provider.get_messages(since=since)

        # Verify the messages
        assert len(messages) == 1
        assert messages[0] == mock_email

        # Verify the mocks were called
        self.provider.service.users().messages().list.assert_called_once_with(
            userId="me",
            maxResults=10,
            q="after:2023/01/01",
        )

    def test_send_reply_when_not_connected(self):
        """Test send_reply when not connected."""
        # Ensure service is None
        self.provider.service = None

        # Create a mock message
        mock_message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",  # Add thread_id
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Subject",
            body_text="Body",
        )

        # Try to send a reply
        with pytest.raises(ConnectionError):
            self.provider.send_reply(mock_message, "Reply text")

    @patch("stoppls.email_providers.gmail.GmailProvider._create_reply")
    def test_send_reply_success(self, mock_create_reply):
        """Test send_reply success."""
        # Set up a mock service
        self.provider.service = MagicMock()

        # Mock the _create_reply method
        mock_reply = {"raw": "test_raw_message"}
        mock_create_reply.return_value = mock_reply

        # Create a mock message
        mock_message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",  # Add thread_id
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Subject",
            body_text="Body",
        )

        # Send a reply
        result = self.provider.send_reply(mock_message, "Reply text")

        # Verify the result
        assert result is True

        # Verify the mocks were called
        mock_create_reply.assert_called_once_with(
            mock_message, "Reply text", None
        )
        self.provider.service.users().messages().send.assert_called_once_with(
            userId="me", body=mock_reply
        )

    def test_archive_message_when_not_connected(self):
        """Test archive_message when not connected."""
        # Ensure service is None
        self.provider.service = None

        # Create a mock message
        mock_message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",  # Add thread_id
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Subject",
            body_text="Body",
        )

        # Try to archive a message
        with pytest.raises(ConnectionError):
            self.provider.archive_message(mock_message)

    def test_archive_message_success(self):
        """Test archive_message success."""
        # Set up a mock service
        self.provider.service = MagicMock()

        # Create a mock message
        mock_message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",  # Add thread_id
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Subject",
            body_text="Body",
        )

        # Archive a message
        result = self.provider.archive_message(mock_message)

        # Verify the result
        assert result is True

        # Verify the mocks were called
        self.provider.service.users().messages().modify.assert_called_once_with(
            userId="me",
            id="msg1",
            body={"removeLabelIds": ["INBOX"]},
        )

    def test_apply_label_when_not_connected(self):
        """Test apply_label when not connected."""
        # Ensure service is None
        self.provider.service = None

        # Create a mock message
        mock_message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",  # Add thread_id
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Subject",
            body_text="Body",
        )

        # Try to apply a label
        with pytest.raises(ConnectionError):
            self.provider.apply_label(mock_message, "Test Label")

    @patch("stoppls.email_providers.gmail.GmailProvider._get_or_create_label")
    def test_apply_label_success(self, mock_get_or_create_label):
        """Test apply_label success."""
        # Set up a mock service
        self.provider.service = MagicMock()

        # Create a mock message
        mock_message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",  # Add thread_id
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Subject",
            body_text="Body",
        )

        # Mock the _get_or_create_label method
        mock_get_or_create_label.return_value = "label_id"

        # Apply a label
        result = self.provider.apply_label(mock_message, "Test Label")

        # Verify the result
        assert result is True

        # Verify the mocks were called
        mock_get_or_create_label.assert_called_once_with("Test Label")
        self.provider.service.users().messages().modify.assert_called_once_with(
            userId="me",
            id="msg1",
            body={"addLabelIds": ["label_id"]},
        )

    def test_get_or_create_label_existing(self):
        """Test _get_or_create_label with an existing label."""
        # Set up a mock service
        self.provider.service = MagicMock()

        # Mock the labels.list response
        self.provider.service.users().labels().list.return_value.execute.return_value = {
            "labels": [
                {"id": "label1", "name": "Label 1"},
                {"id": "label2", "name": "Test Label"},
            ]
        }

        # Get or create a label
        label_id = self.provider._get_or_create_label("Test Label")

        # Verify the label ID
        assert label_id == "label2"

        # Verify the mocks were called
        self.provider.service.users().labels().list.assert_called_once_with(userId="me")
        self.provider.service.users().labels().create.assert_not_called()

    def test_get_or_create_label_new(self):
        """Test _get_or_create_label with a new label."""
        # Set up a mock service
        self.provider.service = MagicMock()

        # Mock the labels.list response
        self.provider.service.users().labels().list.return_value.execute.return_value = {
            "labels": [
                {"id": "label1", "name": "Label 1"},
                {"id": "label2", "name": "Label 2"},
            ]
        }

        # Mock the labels.create response
        self.provider.service.users().labels().create.return_value.execute.return_value = {
            "id": "new_label",
            "name": "Test Label",
        }

        # Get or create a label
        label_id = self.provider._get_or_create_label("Test Label")

        # Verify the label ID
        assert label_id == "new_label"

        # Verify the mocks were called
        self.provider.service.users().labels().list.assert_called_once_with(userId="me")
        self.provider.service.users().labels().create.assert_called_once_with(
            userId="me", body={"name": "Test Label"}
        )

    def test_parse_message(self):
        """Test _parse_message."""
        # Create a mock Gmail API message
        mock_api_message = {
            "id": "msg1",
            "threadId": "thread1",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {
                        "name": "To",
                        "value": "recipient1@example.com, recipient2@example.com",
                    },
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "Date", "value": "Mon, 01 Jan 2023 12:34:56 +0000"},
                ],
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": "VGVzdCBib2R5"},  # Base64 for "Test body"
                    },
                    {
                        "mimeType": "text/html",
                        "body": {
                            "data": "PGgxPlRlc3QgYm9keTwvaDE+"  # Base64 for "<h1>Test body</h1>"
                        },
                    },
                ],
            },
        }

        # Call _parse_message
        result = self.provider._parse_message(mock_api_message)

        # Verify the result
        assert result.message_id == "msg1"
        assert result.thread_id == "thread1"
        assert result.sender == "sender@example.com"
        assert result.recipients == ["recipient1@example.com", "recipient2@example.com"]
        assert result.subject == "Test Subject"
        assert result.body_text == "Test body"
        assert result.body_html == "<h1>Test body</h1>"
        assert result.date.year == 2023
        assert result.date.month == 1
        assert result.date.day == 1
        assert result.date.hour == 12
        assert result.date.minute == 34
        assert result.date.second == 56

    def test_parse_message_no_parts(self):
        """Test _parse_message with no parts."""
        # Create a mock Gmail API message with no parts
        mock_api_message = {
            "id": "msg1",
            "threadId": "thread1",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Subject", "value": "Test Subject"},
                ],
                "body": {"data": "VGVzdCBib2R5"},  # Base64 for "Test body"
            },
        }

        # Call _parse_message
        result = self.provider._parse_message(mock_api_message)

        # Verify the result
        assert result.message_id == "msg1"
        assert result.thread_id == "thread1"
        assert result.sender == "sender@example.com"
        assert result.recipients == ["recipient@example.com"]
        assert result.subject == "Test Subject"
        assert result.body_text == "Test body"
        assert result.body_html is None

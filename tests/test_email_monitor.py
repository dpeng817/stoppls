"""Tests for the email monitoring service."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from stoppls.config import NaturalLanguageRule, RuleAction
from stoppls.email_monitor import EmailMonitor
from stoppls.email_providers.base import EmailMessage, EmailProvider
from stoppls.rule_engine import RuleResult


class MockEmailProvider(EmailProvider):
    """Mock email provider for testing."""

    def __init__(self):
        self._connected = False
        self.messages = []
        self.archived_messages = []
        self.labeled_messages = []
        self.replied_messages = []
        self.sent_emails = []

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> bool:
        self._connected = False
        return True

    def is_connected(self) -> bool:
        return self._connected

    def get_messages(self, from_addresses=None, since=None, limit=10):
        if not self._connected:
            raise ConnectionError("Not connected")

        filtered_messages = self.messages.copy()

        if from_addresses:
            filtered_messages = [
                msg
                for msg in filtered_messages
                if any(addr in msg.sender for addr in from_addresses)
            ]

        if since:
            filtered_messages = [
                msg for msg in filtered_messages if msg.date and msg.date > since
            ]

        return filtered_messages[:limit]

    def send_reply(self, original_message, reply_text, reply_html=None):
        if not self._connected:
            raise ConnectionError("Not connected")

        self.replied_messages.append(
            {
                "original_message": original_message,
                "reply_text": reply_text,
                "reply_html": reply_html,
            }
        )
        return True

    def archive_message(self, message):
        if not self._connected:
            raise ConnectionError("Not connected")

        self.archived_messages.append(message)
        return True

    def apply_label(self, message, label):
        if not self._connected:
            raise ConnectionError("Not connected")

        self.labeled_messages.append({"message": message, "label": label})
        return True
        
    def get_message_by_id(self, message_id):
        """Get a specific message by its ID.

        Args:
            message_id: The ID of the message to retrieve.

        Returns:
            Optional[EmailMessage]: The email message if found, None otherwise.

        Raises:
            ConnectionError: If not connected to the email provider.
        """
        if not self._connected:
            raise ConnectionError("Not connected")

        # Find the message with the matching ID
        for message in self.messages:
            if message.message_id == message_id:
                return message
                
        return None
        
    def send_email(self, to, subject, body_text, body_html=None):
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
            raise ConnectionError("Not connected")

        self.sent_emails.append({
            "to": to,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "timestamp": datetime.now(),
        })
        return True

    def add_test_message(self, message):
        """Add a test message to the mock provider."""
        self.messages.append(message)


class TestEmailMonitor:
    """Tests for the EmailMonitor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.provider = MockEmailProvider()
        self.monitor = EmailMonitor(
            email_provider=self.provider,
            check_interval=1,  # 1 second interval for testing
            monitored_addresses=["important@example.com", "updates@example.com"],
        )

    def test_init(self):
        """Test initialization."""
        assert self.monitor.email_provider == self.provider
        assert self.monitor.check_interval == 1
        assert self.monitor.monitored_addresses == [
            "important@example.com",
            "updates@example.com",
        ]
        assert self.monitor.last_check_time is None
        assert not self.monitor.is_running
        assert self.monitor.rule_config is None
        assert self.monitor.rule_engine is None
        assert not self.monitor.read_only  # Default should be False

    def test_init_with_read_only(self):
        """Test initialization with read_only mode."""
        monitor = EmailMonitor(
            email_provider=self.provider,
            read_only=True,
        )
        assert monitor.read_only is True

    def test_init_with_rules(self):
        """Test initialization with rule configuration."""
        with patch("stoppls.email_monitor.load_rules") as mock_load_rules:
            with patch("stoppls.email_monitor.RuleEngine") as mock_rule_engine:
                # Mock the rule config
                mock_rule_config = MagicMock()
                mock_load_rules.return_value = mock_rule_config

                # Create monitor with rule config
                monitor = EmailMonitor(
                    email_provider=self.provider,
                    rule_config_path="/path/to/rules.yaml",
                    anthropic_api_key="test_api_key",
                )

                # Verify rule config was loaded
                mock_load_rules.assert_called_once_with("/path/to/rules.yaml")

                # Verify rule engine was created
                mock_rule_engine.assert_called_once_with(
                    rule_config=mock_rule_config, anthropic_api_key="test_api_key"
                )

                assert monitor.rule_config == mock_rule_config
                assert monitor.rule_engine == mock_rule_engine.return_value

    def test_start_stop(self):
        """Test starting and stopping the monitor."""
        # Start the monitor
        self.monitor.start()
        assert self.monitor.is_running
        assert self.provider.is_connected()

        # Stop the monitor
        self.monitor.stop()
        assert not self.monitor.is_running
        assert not self.provider.is_connected()

    @patch("stoppls.email_monitor.EmailMonitor.process_message")
    def test_check_for_new_messages(self, mock_process_message):
        """Test checking for new messages."""
        # Create test messages
        now = datetime.now()
        message1 = EmailMessage(
            message_id="msg1",
            thread_id="thread1",
            sender="important@example.com",
            recipients=["me@example.com"],
            subject="Important Message",
            body_text="This is important",
            date=now - timedelta(minutes=30),
        )
        message2 = EmailMessage(
            message_id="msg2",
            thread_id="thread2",
            sender="updates@example.com",
            recipients=["me@example.com"],
            subject="Update",
            body_text="This is an update",
            date=now - timedelta(minutes=15),
        )

        # Add messages to the provider
        self.provider.add_test_message(message1)
        self.provider.add_test_message(message2)

        # Connect the provider
        self.provider.connect()

        # Set last check time to 1 hour ago
        self.monitor.last_check_time = now - timedelta(hours=1)

        # Check for new messages
        self.monitor.check_for_new_messages()

        # Verify process_message was called for both messages
        assert mock_process_message.call_count == 2
        mock_process_message.assert_any_call(message1)
        mock_process_message.assert_any_call(message2)

        # Verify last_check_time was updated
        assert self.monitor.last_check_time > now - timedelta(seconds=5)

    @patch("stoppls.email_monitor.EmailMonitor.process_message")
    def test_check_for_new_messages_with_no_messages(self, mock_process_message):
        """Test checking for new messages when there are none."""
        # Connect the provider
        self.provider.connect()

        # Set last check time to 1 hour ago
        now = datetime.now()
        self.monitor.last_check_time = now - timedelta(hours=1)

        # Check for new messages
        self.monitor.check_for_new_messages()

        # Verify process_message was not called
        mock_process_message.assert_not_called()

        # Verify last_check_time was updated
        assert self.monitor.last_check_time > now - timedelta(seconds=5)

    @patch("stoppls.email_monitor.EmailMonitor.process_message")
    def test_check_for_new_messages_first_run(self, mock_process_message):
        """Test checking for new messages on first run."""
        # Create test messages
        now = datetime.now()
        message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",
            sender="important@example.com",
            recipients=["me@example.com"],
            subject="Important Message",
            body_text="This is important",
            date=now - timedelta(days=7),  # Old message
        )

        # Add message to the provider
        self.provider.add_test_message(message)

        # Connect the provider
        self.provider.connect()

        # Ensure last_check_time is None (first run)
        self.monitor.last_check_time = None

        # Check for new messages
        self.monitor.check_for_new_messages()

        # Verify process_message was not called for old messages on first run
        mock_process_message.assert_not_called()

        # Verify last_check_time was set
        assert self.monitor.last_check_time is not None

    @patch("stoppls.email_monitor.EmailMonitor.execute_actions")
    def test_process_message_with_rule_engine(self, mock_execute_actions):
        """Test processing a message with rule engine."""
        # Create a test message
        message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",
            sender="important@example.com",
            recipients=["me@example.com"],
            subject="Important Message",
            body_text="This is important",
            date=datetime.now(),
        )

        # Create a mock rule engine
        mock_rule_engine = MagicMock()
        self.monitor.rule_engine = mock_rule_engine

        # Create mock rule results
        rule = NaturalLanguageRule(
            name="Test Rule",
            description="Test rule description",
            prompt="Test prompt",
            actions=[RuleAction(type="reply", parameters={"text": "Test reply"})],
        )
        rule_result = RuleResult(rule=rule, matched=True, actions=rule.actions)
        mock_rule_engine.evaluate_email.return_value = [rule_result]

        # Connect the provider
        self.provider.connect()

        # Process the message
        self.monitor.process_message(message)

        # Verify rule engine was called
        mock_rule_engine.evaluate_email.assert_called_once_with(message)

        # Verify execute_actions was called
        mock_execute_actions.assert_called_once_with(message, rule_result)

    def test_process_message_without_rule_engine(self):
        """Test processing a message without rule engine."""
        # Create a test message
        message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",
            sender="important@example.com",
            recipients=["me@example.com"],
            subject="Important Message",
            body_text="This is important",
            date=datetime.now(),
        )

        # Ensure rule engine is None
        self.monitor.rule_engine = None

        # Connect the provider
        self.provider.connect()

        # Process the message
        self.monitor.process_message(message)

        # No assertions needed, just verify it doesn't raise an exception

    def test_execute_actions_reply(self):
        """Test executing reply action."""
        # Create a test message
        message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",
            sender="important@example.com",
            recipients=["me@example.com"],
            subject="Important Message",
            body_text="This is important",
            date=datetime.now(),
        )

        # Create a rule result with reply action
        rule = NaturalLanguageRule(
            name="Reply Rule",
            description="Rule to test reply action",
            prompt="Test prompt",
            actions=[RuleAction(type="reply", parameters={"text": "Test reply"})],
        )
        rule_result = RuleResult(rule=rule, matched=True, actions=rule.actions)

        # Connect the provider
        self.provider.connect()

        # Execute actions
        self.monitor.execute_actions(message, rule_result)

        # Verify reply was sent
        assert len(self.provider.replied_messages) == 1
        assert self.provider.replied_messages[0]["original_message"] == message
        assert self.provider.replied_messages[0]["reply_text"] == "Test reply"

    def test_execute_actions_archive(self):
        """Test executing archive action."""
        # Create a test message
        message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",
            sender="important@example.com",
            recipients=["me@example.com"],
            subject="Important Message",
            body_text="This is important",
            date=datetime.now(),
        )

        # Create a rule result with archive action
        rule = NaturalLanguageRule(
            name="Archive Rule",
            description="Rule to test archive action",
            prompt="Test prompt",
            actions=[RuleAction(type="archive", parameters={})],
        )
        rule_result = RuleResult(rule=rule, matched=True, actions=rule.actions)

        # Connect the provider
        self.provider.connect()

        # Execute actions
        self.monitor.execute_actions(message, rule_result)

        # Verify message was archived
        assert len(self.provider.archived_messages) == 1
        assert self.provider.archived_messages[0] == message

    def test_execute_actions_label(self):
        """Test executing label action."""
        # Create a test message
        message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",
            sender="important@example.com",
            recipients=["me@example.com"],
            subject="Important Message",
            body_text="This is important",
            date=datetime.now(),
        )

        # Create a rule result with label action
        rule = NaturalLanguageRule(
            name="Label Rule",
            description="Rule to test label action",
            prompt="Test prompt",
            actions=[RuleAction(type="label", parameters={"label": "Important"})],
        )
        rule_result = RuleResult(rule=rule, matched=True, actions=rule.actions)

        # Connect the provider
        self.provider.connect()

        # Execute actions
        self.monitor.execute_actions(message, rule_result)

        # Verify label was applied
        assert len(self.provider.labeled_messages) == 1
        assert self.provider.labeled_messages[0]["message"] == message
        assert self.provider.labeled_messages[0]["label"] == "Important"

    def test_execute_actions_unknown_action(self):
        """Test executing unknown action."""
        # Create a test message
        message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",
            sender="important@example.com",
            recipients=["me@example.com"],
            subject="Important Message",
            body_text="This is important",
            date=datetime.now(),
        )

        # Create a rule result with unknown action
        rule = NaturalLanguageRule(
            name="Unknown Action Rule",
            description="Rule to test unknown action",
            prompt="Test prompt",
            actions=[RuleAction(type="unknown", parameters={})],
        )
        rule_result = RuleResult(rule=rule, matched=True, actions=rule.actions)

        # Connect the provider
        self.provider.connect()

        # Execute actions
        self.monitor.execute_actions(message, rule_result)

        # Verify no actions were executed
        assert len(self.provider.replied_messages) == 0
        assert len(self.provider.archived_messages) == 0
        assert len(self.provider.labeled_messages) == 0

    @patch("logging.Logger.info")
    def test_execute_actions_read_only_mode(self, mock_logger_info):
        """Test executing actions in read-only mode."""
        # Create a monitor with read_only=True
        monitor = EmailMonitor(
            email_provider=self.provider,
            read_only=True,
        )

        # Create a test message
        message = EmailMessage(
            message_id="msg1",
            thread_id="thread1",
            sender="important@example.com",
            recipients=["me@example.com"],
            subject="Important Message",
            body_text="This is important",
            date=datetime.now(),
        )

        # Create a rule result with multiple actions
        rule = NaturalLanguageRule(
            name="Multi-Action Rule",
            description="Rule with multiple actions",
            prompt="Test prompt",
            actions=[
                RuleAction(type="reply", parameters={"text": "Test reply"}),
                RuleAction(type="archive", parameters={}),
                RuleAction(type="label", parameters={"label": "Important"}),
            ],
        )
        rule_result = RuleResult(rule=rule, matched=True, actions=rule.actions)

        # Connect the provider
        self.provider.connect()

        # Execute actions in read-only mode
        monitor.execute_actions(message, rule_result)

        # Verify no actual actions were executed
        assert len(self.provider.replied_messages) == 0
        assert len(self.provider.archived_messages) == 0
        assert len(self.provider.labeled_messages) == 0

        # Verify that actions were logged
        mock_logger_info.assert_any_call(f"[READ-ONLY] Would execute actions for rule: {rule.name}")
        mock_logger_info.assert_any_call("[READ-ONLY] Would reply to message: Important Message")
        mock_logger_info.assert_any_call("[READ-ONLY] Would archive message: Important Message")
        mock_logger_info.assert_any_call("[READ-ONLY] Would apply label 'Important' to message: Important Message")

    @patch("time.sleep", side_effect=lambda x: None)  # Don't actually sleep in tests
    def test_run_loop(self, mock_sleep):
        """Test the run loop."""
        # Mock check_for_new_messages to count calls and then stop after 3 iterations
        call_count = 0

        def mock_check():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                self.monitor.stop()

        self.monitor.check_for_new_messages = mock_check

        # Start the monitor
        self.monitor.start()

        # Run the loop
        self.monitor._run_loop()

        # Verify check_for_new_messages was called 3 times
        assert call_count == 3

        # Verify sleep was called with the check interval at least once
        mock_sleep.assert_any_call(1)

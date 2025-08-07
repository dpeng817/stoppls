"""Integration tests for location filtering functionality."""

from datetime import datetime
from unittest.mock import patch

from stoppls.config import NaturalLanguageRule, RuleAction, RuleConfig
from stoppls.email_monitor import EmailMonitor
from stoppls.email_providers.memory import InMemoryEmailProvider
from stoppls.rule_engine import RuleEngine


class TestLocationIntegration:
    """Integration tests for location filtering."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create an in-memory email provider
        self.email_provider = InMemoryEmailProvider()
        self.email_provider.connect()

        # Create test rules with location filters
        self.inbox_rule = NaturalLanguageRule(
            name="Inbox Only Rule",
            description="Only apply to emails in the inbox",
            prompt="The email contains important information",
            enabled=True,
            location="INBOX",
            actions=[
                RuleAction(
                    type="reply", parameters={"text": "Thank you for your email!"}
                )
            ],
        )

        self.spam_rule = NaturalLanguageRule(
            name="Spam Only Rule",
            description="Only apply to emails in spam",
            prompt="The email is spam",
            enabled=True,
            location="SPAM",
            actions=[RuleAction(type="archive", parameters={})],
        )

        self.any_location_rule = NaturalLanguageRule(
            name="Any Location Rule",
            description="Apply to emails in any location",
            prompt="The email contains a keyword",
            enabled=True,
            actions=[RuleAction(type="label", parameters={"label": "Keyword"})],
        )

        # Create rule config
        self.rule_config = RuleConfig(
            rules=[self.inbox_rule, self.spam_rule, self.any_location_rule]
        )

        # Create test emails with different locations
        self.inbox_email = self.email_provider.add_message_with_location(
            message_id="msg1",
            thread_id="thread1",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Important Email",
            body_text="This is an important email.",
            location="INBOX",
            date=datetime.now(),
        )

        self.spam_email = self.email_provider.add_message_with_location(
            message_id="msg2",
            thread_id="thread2",
            sender="spammer@example.com",
            recipients=["recipient@example.com"],
            subject="Spam Email",
            body_text="This is a spam email.",
            location="SPAM",
            date=datetime.now(),
        )

    @patch("stoppls.rule_engine.RuleEngine._evaluate_rule_with_ai")
    def test_email_monitor_with_location_filtering(self, mock_evaluate_rule_with_ai):
        """Test that EmailMonitor correctly applies location filtering."""
        # Mock the _evaluate_rule_with_ai method to always return True
        mock_evaluate_rule_with_ai.return_value = True

        # Create a rule engine with our test config
        rule_engine = RuleEngine(
            rule_config=self.rule_config, anthropic_api_key="test_api_key"
        )

        # Create an email monitor
        email_monitor = EmailMonitor(
            email_provider=self.email_provider,
            check_interval=60,
            monitored_addresses=["sender@example.com", "spammer@example.com"],
            read_only=True,  # Use read-only mode for testing
            enable_reports=False,
        )

        # Set the rule engine directly
        email_monitor.rule_engine = rule_engine

        # Process the inbox email
        email_monitor.process_message(self.inbox_email)

        # Verify that only the inbox rule and any_location rule were considered
        # Since we're in read-only mode, no actual actions are taken
        assert mock_evaluate_rule_with_ai.call_count == 2
        rule_names = [
            call_args[0][0].name
            for call_args in mock_evaluate_rule_with_ai.call_args_list
        ]
        assert "Inbox Only Rule" in rule_names
        assert "Any Location Rule" in rule_names
        assert "Spam Only Rule" not in rule_names

        # Reset the mock
        mock_evaluate_rule_with_ai.reset_mock()

        # Process the spam email
        email_monitor.process_message(self.spam_email)

        # Verify that only the spam rule and any_location rule were considered
        assert mock_evaluate_rule_with_ai.call_count == 2
        rule_names = [
            call_args[0][0].name
            for call_args in mock_evaluate_rule_with_ai.call_args_list
        ]
        assert "Spam Only Rule" in rule_names
        assert "Any Location Rule" in rule_names
        assert "Inbox Only Rule" not in rule_names

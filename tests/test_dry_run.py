"""Tests for the dry-run command."""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from stoppls.email_providers.base import EmailMessage
from stoppls.email_providers.memory import InMemoryEmailProvider
from stoppls.config import RuleConfig, NaturalLanguageRule, RuleAction
from stoppls.rule_engine import RuleEngine


class TestDryRun(unittest.TestCase):
    """Test the dry-run command functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a test email message
        self.test_email = EmailMessage(
            message_id="test123",
            thread_id="thread123",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Test Subject",
            body_text="This is a test email body.",
            date=datetime.now(),
        )

        # Create a test rule
        self.test_rule = NaturalLanguageRule(
            name="Test Rule",
            description="A test rule",
            prompt="Any email containing the word 'test'",
            enabled=True,
            actions=[
                RuleAction(type="reply", parameters={"text": "This is an automated reply"}),
                RuleAction(type="archive", parameters={}),
            ],
        )

        # Create a rule config with the test rule
        self.rule_config = RuleConfig(rules=[self.test_rule])

        # Create an in-memory email provider
        self.email_provider = InMemoryEmailProvider()
        self.email_provider.connect()
        self.email_provider.add_message(self.test_email)

    @patch("stoppls.cli.GmailProvider")
    @patch("stoppls.cli.load_rules")
    def test_dry_run_command(self, mock_load_rules, mock_gmail_provider):
        """Test the dry-run command with a valid email ID."""
        from stoppls.cli import dry_run

        # Mock the load_rules function to return our test rule config
        mock_load_rules.return_value = self.rule_config

        # Mock the GmailProvider to return our in-memory provider
        mock_provider_instance = MagicMock()
        mock_provider_instance.get_message_by_id.return_value = self.test_email
        mock_gmail_provider.return_value = mock_provider_instance

        # Create mock arguments
        args = MagicMock()
        args.email_id = "test123"
        args.credentials = "test_credentials.json"
        args.token = "test_token.pickle"
        args.rules = "test_rules.yaml"
        args.anthropic_key = "test_key"
        args.verbose = True

        # Run the dry-run command
        with patch("stoppls.cli.setup_logging"):
            dry_run(args)

        # Verify the provider was connected to
        mock_provider_instance.connect.assert_called_once()

        # Verify the message was retrieved
        mock_provider_instance.get_message_by_id.assert_called_once_with("test123")

    @patch("stoppls.cli.GmailProvider")
    @patch("stoppls.cli.load_rules")
    def test_dry_run_email_not_found(self, mock_load_rules, mock_gmail_provider):
        """Test the dry-run command when the email ID is not found."""
        from stoppls.cli import dry_run

        # Mock the load_rules function to return our test rule config
        mock_load_rules.return_value = self.rule_config

        # Mock the GmailProvider to return None for the email
        mock_provider_instance = MagicMock()
        mock_provider_instance.get_message_by_id.return_value = None
        mock_gmail_provider.return_value = mock_provider_instance

        # Create mock arguments
        args = MagicMock()
        args.email_id = "nonexistent123"
        args.credentials = "test_credentials.json"
        args.token = "test_token.pickle"
        args.rules = "test_rules.yaml"
        args.anthropic_key = "test_key"
        args.verbose = True

        # Run the dry-run command and check for error
        with patch("stoppls.cli.setup_logging"), \
             patch("logging.getLogger") as mock_get_logger:
            # Set up the mock logger
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Run the dry-run command
            dry_run(args)
            
            # Check that the error was logged
            mock_logger.error.assert_any_call(f"Email with ID {args.email_id} not found")

    @patch("stoppls.cli.GmailProvider")
    @patch("stoppls.cli.load_rules")
    @patch("stoppls.cli.RuleEngine")
    def test_dry_run_rule_evaluation(self, mock_rule_engine, mock_load_rules, mock_gmail_provider):
        """Test that rules are evaluated correctly in dry-run mode."""
        from stoppls.cli import dry_run

        # Mock the load_rules function to return our test rule config
        mock_load_rules.return_value = self.rule_config

        # Mock the GmailProvider to return our test email
        mock_provider_instance = MagicMock()
        mock_provider_instance.get_message_by_id.return_value = self.test_email
        mock_gmail_provider.return_value = mock_provider_instance

        # Mock the RuleEngine
        mock_rule_engine_instance = MagicMock()
        mock_rule_engine.return_value = mock_rule_engine_instance

        # Create mock arguments
        args = MagicMock()
        args.email_id = "test123"
        args.credentials = "test_credentials.json"
        args.token = "test_token.pickle"
        args.rules = "test_rules.yaml"
        args.anthropic_key = "test_key"
        args.verbose = True

        # Run the dry-run command
        with patch("stoppls.cli.setup_logging"):
            dry_run(args)

        # Verify the rule engine was created with the correct parameters
        mock_rule_engine.assert_called_once_with(
            rule_config=mock_load_rules.return_value,
            anthropic_api_key=args.anthropic_key
        )

        # Verify the email was evaluated against the rules
        mock_rule_engine_instance.evaluate_email.assert_called_once_with(self.test_email)
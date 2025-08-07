"""Tests for rule location filtering functionality."""

from datetime import datetime
from unittest.mock import patch

from stoppls.config import NaturalLanguageRule, RuleAction, RuleConfig
from stoppls.email_providers.base import EmailMessage
from stoppls.rule_engine import RuleEngine


class TestRuleLocationFilter:
    """Tests for rule location filtering."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test rules with location filters
        self.inbox_rule = NaturalLanguageRule(
            name="Inbox Only Rule",
            description="Only apply to emails in the inbox",
            prompt="The email contains important information",
            enabled=True,
            location="INBOX",  # This rule should only apply to inbox emails
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
            location="SPAM",  # This rule should only apply to spam emails
            actions=[RuleAction(type="archive", parameters={})],
        )

        self.any_location_rule = NaturalLanguageRule(
            name="Any Location Rule",
            description="Apply to emails in any location",
            prompt="The email contains a keyword",
            enabled=True,
            # No location specified means apply to all locations
            actions=[RuleAction(type="label", parameters={"label": "Keyword"})],
        )

        # Create rule config
        self.config = RuleConfig(
            rules=[self.inbox_rule, self.spam_rule, self.any_location_rule]
        )

        # Create test emails with different locations
        self.inbox_email = EmailMessage(
            message_id="msg1",
            thread_id="thread1",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Test Email",
            body_text="This is a test email.",
            date=datetime.now(),
            location="INBOX",  # This email is in the inbox
        )

        self.spam_email = EmailMessage(
            message_id="msg2",
            thread_id="thread2",
            sender="spammer@example.com",
            recipients=["recipient@example.com"],
            subject="Spam Email",
            body_text="This is a spam email.",
            date=datetime.now(),
            location="SPAM",  # This email is in spam
        )

    @patch("stoppls.rule_engine.RuleEngine._evaluate_rule_with_ai")
    def test_evaluate_email_with_location_filter(self, mock_evaluate_rule_with_ai):
        """Test evaluating an email against rules with location filters."""
        # Mock the _evaluate_rule_with_ai method to always return True
        # We're testing the location filter, not the AI evaluation
        mock_evaluate_rule_with_ai.return_value = True

        # Create the rule engine
        engine = RuleEngine(rule_config=self.config, anthropic_api_key="test_api_key")

        # Evaluate the inbox email
        inbox_results = engine.evaluate_email(self.inbox_email)

        # Verify that only the inbox rule and any_location rule were applied
        assert len(inbox_results) == 2
        rule_names = [result.rule.name for result in inbox_results]
        assert "Inbox Only Rule" in rule_names
        assert "Any Location Rule" in rule_names
        assert "Spam Only Rule" not in rule_names

        # Evaluate the spam email
        spam_results = engine.evaluate_email(self.spam_email)

        # Verify that only the spam rule and any_location rule were applied
        assert len(spam_results) == 2
        rule_names = [result.rule.name for result in spam_results]
        assert "Spam Only Rule" in rule_names
        assert "Any Location Rule" in rule_names
        assert "Inbox Only Rule" not in rule_names

    def test_rule_location_serialization(self):
        """Test that rule location is properly serialized and deserialized."""
        # Convert rule to dict
        rule_dict = self.inbox_rule.to_dict()

        # Verify location is in the dict
        assert "location" in rule_dict
        assert rule_dict["location"] == "INBOX"

        # Deserialize the rule
        deserialized_rule = NaturalLanguageRule.from_dict(rule_dict)

        # Verify location was preserved
        assert hasattr(deserialized_rule, "location")
        assert deserialized_rule.location == "INBOX"

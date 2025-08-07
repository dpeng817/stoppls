"""Tests for the rule engine."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from stoppls.config import NaturalLanguageRule, RuleAction, RuleConfig
from stoppls.email_providers.base import EmailMessage
from stoppls.rule_engine import RuleEngine, RuleResult


class TestRuleEngine:
    """Tests for the RuleEngine class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test rules
        self.rule1 = NaturalLanguageRule(
            name="Reply to Example",
            description="Reply to emails from example.com",
            prompt="The email is from example.com",
            enabled=True,
            actions=[
                RuleAction(
                    type="reply", parameters={"text": "Thank you for your email!"}
                )
            ],
        )

        self.rule2 = NaturalLanguageRule(
            name="Archive Newsletters",
            description="Archive newsletter emails",
            prompt="The email is a newsletter or marketing email",
            enabled=True,
            actions=[RuleAction(type="archive", parameters={})],
        )

        self.rule3 = NaturalLanguageRule(
            name="Label Important",
            description="Label important emails",
            prompt="The email contains urgent information or requires immediate action",
            enabled=True,
            actions=[RuleAction(type="label", parameters={"label": "Important"})],
        )

        # Create a disabled rule
        self.disabled_rule = NaturalLanguageRule(
            name="Disabled Rule",
            description="This rule is disabled",
            prompt="This rule should not be evaluated",
            enabled=False,
            actions=[
                RuleAction(type="reply", parameters={"text": "This should not be sent"})
            ],
        )

        # Create rule config
        self.config = RuleConfig(
            rules=[self.rule1, self.rule2, self.rule3, self.disabled_rule]
        )

        # Create test email
        self.email = EmailMessage(
            message_id="msg1",
            thread_id="thread1",  # Add thread_id
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Test Email",
            body_text="This is a test email.",
            date=datetime.now(),
        )

    @patch("stoppls.rule_engine.RuleEngine._evaluate_rule_with_ai")
    def test_evaluate_email(self, mock_evaluate_rule_with_ai):
        """Test evaluating an email against rules."""

        # Mock the _evaluate_rule_with_ai method to return True for rule1 and rule3
        def mock_evaluate_side_effect(rule, email):
            if rule == self.rule1 or rule == self.rule3:
                return True
            return False

        mock_evaluate_rule_with_ai.side_effect = mock_evaluate_side_effect

        # Create the rule engine
        engine = RuleEngine(rule_config=self.config, anthropic_api_key="test_api_key")

        # Evaluate the email
        results = engine.evaluate_email(self.email)

        # Verify that _evaluate_rule_with_ai was called for each enabled rule
        assert mock_evaluate_rule_with_ai.call_count == 3
        mock_evaluate_rule_with_ai.assert_any_call(self.rule1, self.email)
        mock_evaluate_rule_with_ai.assert_any_call(self.rule2, self.email)
        mock_evaluate_rule_with_ai.assert_any_call(self.rule3, self.email)

        # Verify that the disabled rule was not evaluated
        for call_args in mock_evaluate_rule_with_ai.call_args_list:
            assert call_args[0][0] != self.disabled_rule

        # Verify that the results contain the matching rules
        assert len(results) == 2
        assert results[0].rule == self.rule1
        assert results[0].matched is True
        assert results[0].actions == self.rule1.actions
        assert results[1].rule == self.rule3
        assert results[1].matched is True
        assert results[1].actions == self.rule3.actions

    @patch("stoppls.rule_engine.RuleEngine._evaluate_rule_with_ai")
    def test_evaluate_email_no_matches(self, mock_evaluate_rule_with_ai):
        """Test evaluating an email with no matching rules."""
        # Mock the _evaluate_rule_with_ai method to return False for all rules
        mock_evaluate_rule_with_ai.return_value = False

        # Create the rule engine
        engine = RuleEngine(rule_config=self.config, anthropic_api_key="test_api_key")

        # Evaluate the email
        results = engine.evaluate_email(self.email)

        # Verify that _evaluate_rule_with_ai was called for each enabled rule
        assert mock_evaluate_rule_with_ai.call_count == 3

        # Verify that the results are empty
        assert len(results) == 0

    @patch("anthropic.Anthropic")
    def test_evaluate_rule_with_ai(self, mock_anthropic):
        """Test evaluating a rule with AI."""
        # Mock the Anthropic client
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        # Mock the messages.create method
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "Yes, this email matches the rule."
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        # Create the rule engine
        engine = RuleEngine(rule_config=self.config, anthropic_api_key="test_api_key")

        # Evaluate the rule
        result = engine._evaluate_rule_with_ai(self.rule1, self.email)

        # Verify that the Anthropic client was called
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args[1]
        assert call_args["model"] == "claude-3-haiku-20240307"
        assert call_args["temperature"] == 0.0

        # Verify that the result is True
        assert result is True

    @patch("anthropic.Anthropic")
    def test_evaluate_rule_with_ai_non_matching(self, mock_anthropic):
        """Test evaluating a rule with AI that doesn't match."""
        # Mock the Anthropic client
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        # Mock the messages.create method
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "No, this email does not match the rule."
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        # Create the rule engine
        engine = RuleEngine(rule_config=self.config, anthropic_api_key="test_api_key")

        # Evaluate the rule
        result = engine._evaluate_rule_with_ai(self.rule1, self.email)

        # Verify that the result is False
        assert result is False

    def test_rule_result_init(self):
        """Test initializing a RuleResult."""
        # Create a rule result
        result = RuleResult(rule=self.rule1, matched=True, actions=self.rule1.actions)

        # Verify the attributes
        assert result.rule == self.rule1
        assert result.matched is True
        assert result.actions == self.rule1.actions

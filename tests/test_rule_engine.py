"""
Tests for the rule engine.
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from stoppls.config import RuleAction, NaturalLanguageRule, RuleConfig
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
                RuleAction(type="reply", parameters={"text": "Thank you for your email!"})
            ]
        )
        
        self.rule2 = NaturalLanguageRule(
            name="Archive Newsletters",
            description="Archive newsletter emails",
            prompt="The email is a newsletter or marketing email",
            enabled=True,
            actions=[
                RuleAction(type="archive", parameters={})
            ]
        )
        
        self.rule3 = NaturalLanguageRule(
            name="Label Important",
            description="Label important emails",
            prompt="The email contains urgent information or requires immediate action",
            enabled=True,
            actions=[
                RuleAction(type="label", parameters={"label": "Important"})
            ]
        )
        
        # Create a disabled rule
        self.disabled_rule = NaturalLanguageRule(
            name="Disabled Rule",
            description="This rule is disabled",
            prompt="This rule should not be evaluated",
            enabled=False,
            actions=[
                RuleAction(type="reply", parameters={"text": "This should not be sent"})
            ]
        )
        
        # Create rule config
        self.config = RuleConfig(rules=[
            self.rule1, 
            self.rule2, 
            self.rule3, 
            self.disabled_rule
        ])
        
        # Create test email
        self.email = EmailMessage(
            message_id="msg1",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Test Email",
            body_text="This is a test email.",
            date=datetime.now()
        )
        
        # Create rule engine
        self.engine = RuleEngine(self.config)
    
    @patch('stoppls.rule_engine.RuleEngine._evaluate_rule_with_ai')
    def test_evaluate_email(self, mock_evaluate_rule):
        """Test evaluating an email against rules."""
        # Mock the AI evaluation to return True for rule1, False for rule2, and True for rule3
        def mock_evaluate_side_effect(rule, email):
            if rule == self.rule1:
                return True
            elif rule == self.rule2:
                return False
            elif rule == self.rule3:
                return True
            else:
                return False
        
        mock_evaluate_rule.side_effect = mock_evaluate_side_effect
        
        # Evaluate the email
        results = self.engine.evaluate_email(self.email)
        
        # Verify the results
        assert len(results) == 2  # Only rule1 and rule3 should match
        
        # Check rule1 result
        rule1_result = next((r for r in results if r.rule == self.rule1), None)
        assert rule1_result is not None
        assert rule1_result.matched is True
        assert rule1_result.actions == self.rule1.actions
        
        # Check rule3 result
        rule3_result = next((r for r in results if r.rule == self.rule3), None)
        assert rule3_result is not None
        assert rule3_result.matched is True
        assert rule3_result.actions == self.rule3.actions
        
        # Verify the disabled rule was not evaluated
        mock_evaluate_rule.assert_any_call(self.rule1, self.email)
        mock_evaluate_rule.assert_any_call(self.rule2, self.email)
        mock_evaluate_rule.assert_any_call(self.rule3, self.email)
        assert mock_evaluate_rule.call_count == 3  # Disabled rule should not be evaluated
    
    @patch('stoppls.rule_engine.RuleEngine._evaluate_rule_with_ai')
    def test_evaluate_email_no_matches(self, mock_evaluate_rule):
        """Test evaluating an email with no matching rules."""
        # Mock the AI evaluation to return False for all rules
        mock_evaluate_rule.return_value = False
        
        # Evaluate the email
        results = self.engine.evaluate_email(self.email)
        
        # Verify the results
        assert len(results) == 0  # No rules should match
        
        # Verify the disabled rule was not evaluated
        mock_evaluate_rule.assert_any_call(self.rule1, self.email)
        mock_evaluate_rule.assert_any_call(self.rule2, self.email)
        mock_evaluate_rule.assert_any_call(self.rule3, self.email)
        assert mock_evaluate_rule.call_count == 3  # Disabled rule should not be evaluated
    
    @patch('anthropic.Anthropic')
    def test_evaluate_rule_with_ai(self, mock_anthropic_class):
        """Test evaluating a rule with AI."""
        # Mock the Anthropic client
        mock_anthropic = MagicMock()
        mock_anthropic_class.return_value = mock_anthropic
        
        # Mock the AI response for a matching rule
        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(text="Yes, this rule applies to the email.")
        ]
        mock_anthropic.messages.create.return_value = mock_message
        
        # Create a rule engine with an API key
        engine = RuleEngine(self.config, anthropic_api_key="test_api_key")
        
        # Evaluate the rule
        result = engine._evaluate_rule_with_ai(self.rule1, self.email)
        
        # Verify the result
        assert result is True
        
        # Verify the AI was called with the correct prompt
        mock_anthropic.messages.create.assert_called_once()
        args, kwargs = mock_anthropic.messages.create.call_args
        assert "example.com" in kwargs["system"]  # Rule prompt should be in system message
        assert "sender@example.com" in kwargs["messages"][0]["content"]  # Email details should be in user message
    
    @patch('anthropic.Anthropic')
    def test_evaluate_rule_with_ai_non_matching(self, mock_anthropic_class):
        """Test evaluating a non-matching rule with AI."""
        # Mock the Anthropic client
        mock_anthropic = MagicMock()
        mock_anthropic_class.return_value = mock_anthropic
        
        # Mock the AI response for a non-matching rule
        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(text="No, this rule does not apply to the email.")
        ]
        mock_anthropic.messages.create.return_value = mock_message
        
        # Create a rule engine with an API key
        engine = RuleEngine(self.config, anthropic_api_key="test_api_key")
        
        # Evaluate the rule
        result = engine._evaluate_rule_with_ai(self.rule2, self.email)
        
        # Verify the result
        assert result is False
    
    def test_rule_result_init(self):
        """Test RuleResult initialization."""
        result = RuleResult(
            rule=self.rule1,
            matched=True,
            actions=self.rule1.actions
        )
        
        assert result.rule == self.rule1
        assert result.matched is True
        assert result.actions == self.rule1.actions
"""
Tests for the rule configuration module.
"""
import os
import tempfile
from unittest.mock import patch

import pytest
import yaml

from stoppls.config import (
    RuleAction, Rule, NaturalLanguageRule, RuleConfig, 
    load_rules, save_rules
)


class TestRuleConfig:
    """Tests for the rule configuration classes."""
    
    def test_rule_action_init(self):
        """Test RuleAction initialization."""
        action = RuleAction(
            type="reply",
            parameters={"text": "Thank you for your email!"}
        )
        
        assert action.type == "reply"
        assert action.parameters == {"text": "Thank you for your email!"}
    
    def test_natural_language_rule_init(self):
        """Test NaturalLanguageRule initialization."""
        action = RuleAction(
            type="reply",
            parameters={"text": "Thank you for your email!"}
        )
        
        rule = NaturalLanguageRule(
            name="Example Rule",
            description="Reply to emails from example.com",
            prompt="The email is from example.com",
            enabled=True,
            actions=[action]
        )
        
        assert rule.name == "Example Rule"
        assert rule.description == "Reply to emails from example.com"
        assert rule.prompt == "The email is from example.com"
        assert rule.enabled is True
        assert rule.actions == [action]
    
    def test_natural_language_rule_get_prompt_section(self):
        """Test NaturalLanguageRule get_prompt_section method."""
        rule = NaturalLanguageRule(
            name="Example Rule",
            description="Reply to emails from example.com",
            prompt="The email is from example.com"
        )
        
        expected_prompt = (
            "Rule: Example Rule\n"
            "Description: Reply to emails from example.com\n"
            "Criteria: The email is from example.com"
        )
        
        assert rule.get_prompt_section() == expected_prompt
    
    def test_natural_language_rule_to_dict(self):
        """Test NaturalLanguageRule to_dict method."""
        rule = NaturalLanguageRule(
            name="Example Rule",
            description="Reply to emails from example.com",
            prompt="The email is from example.com",
            enabled=True,
            actions=[
                RuleAction(
                    type="reply",
                    parameters={"text": "Thank you for your email!"}
                )
            ]
        )
        
        expected_dict = {
            "name": "Example Rule",
            "description": "Reply to emails from example.com",
            "enabled": True,
            "type": "NaturalLanguageRule",
            "prompt": "The email is from example.com",
            "actions": [
                {
                    "type": "reply",
                    "parameters": {
                        "text": "Thank you for your email!"
                    }
                }
            ]
        }
        
        assert rule.to_dict() == expected_dict
    
    def test_rule_from_dict(self):
        """Test Rule.from_dict method."""
        rule_dict = {
            "name": "Example Rule",
            "description": "Reply to emails from example.com",
            "enabled": True,
            "type": "NaturalLanguageRule",
            "prompt": "The email is from example.com",
            "actions": [
                {
                    "type": "reply",
                    "parameters": {
                        "text": "Thank you for your email!"
                    }
                }
            ]
        }
        
        rule = Rule.from_dict(rule_dict)
        
        assert isinstance(rule, NaturalLanguageRule)
        assert rule.name == "Example Rule"
        assert rule.description == "Reply to emails from example.com"
        assert rule.prompt == "The email is from example.com"
        assert rule.enabled is True
        assert len(rule.actions) == 1
        assert rule.actions[0].type == "reply"
        assert rule.actions[0].parameters == {"text": "Thank you for your email!"}
    
    def test_rule_from_dict_unknown_type(self):
        """Test Rule.from_dict with unknown rule type."""
        rule_dict = {
            "name": "Example Rule",
            "description": "Reply to emails from example.com",
            "enabled": True,
            "type": "UnknownRuleType",
            "actions": []
        }
        
        with pytest.raises(ValueError, match="Unknown rule type: UnknownRuleType"):
            Rule.from_dict(rule_dict)
    
    def test_rule_config_init(self):
        """Test RuleConfig initialization."""
        rule1 = NaturalLanguageRule(
            name="Rule 1",
            description="Description 1",
            prompt="Prompt 1",
            enabled=True,
            actions=[
                RuleAction(type="reply", parameters={"text": "Reply text"})
            ]
        )
        
        rule2 = NaturalLanguageRule(
            name="Rule 2",
            description="Description 2",
            prompt="Prompt 2",
            enabled=False,
            actions=[
                RuleAction(type="archive", parameters={})
            ]
        )
        
        config = RuleConfig(rules=[rule1, rule2])
        
        assert len(config.rules) == 2
        assert config.rules[0] == rule1
        assert config.rules[1] == rule2
    
    def test_rule_config_to_dict(self):
        """Test RuleConfig to_dict method."""
        rule = NaturalLanguageRule(
            name="Example Rule",
            description="Reply to emails from example.com",
            prompt="The email is from example.com",
            enabled=True,
            actions=[
                RuleAction(type="reply", parameters={"text": "Thank you for your email!"})
            ]
        )
        
        config = RuleConfig(rules=[rule])
        
        expected_dict = {
            "rules": [
                {
                    "name": "Example Rule",
                    "description": "Reply to emails from example.com",
                    "enabled": True,
                    "type": "NaturalLanguageRule",
                    "prompt": "The email is from example.com",
                    "actions": [
                        {
                            "type": "reply",
                            "parameters": {
                                "text": "Thank you for your email!"
                            }
                        }
                    ]
                }
            ]
        }
        
        assert config.to_dict() == expected_dict
    
    def test_rule_config_from_dict(self):
        """Test RuleConfig from_dict method."""
        config_dict = {
            "rules": [
                {
                    "name": "Example Rule",
                    "description": "Reply to emails from example.com",
                    "enabled": True,
                    "type": "NaturalLanguageRule",
                    "prompt": "The email is from example.com",
                    "actions": [
                        {
                            "type": "reply",
                            "parameters": {
                                "text": "Thank you for your email!"
                            }
                        }
                    ]
                }
            ]
        }
        
        config = RuleConfig.from_dict(config_dict)
        
        assert len(config.rules) == 1
        rule = config.rules[0]
        assert isinstance(rule, NaturalLanguageRule)
        assert rule.name == "Example Rule"
        assert rule.description == "Reply to emails from example.com"
        assert rule.prompt == "The email is from example.com"
        assert rule.enabled is True
        assert len(rule.actions) == 1
        action = rule.actions[0]
        assert action.type == "reply"
        assert action.parameters == {"text": "Thank you for your email!"}
    
    def test_load_save_rules(self):
        """Test loading and saving rules."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Create a rule config
            rule = NaturalLanguageRule(
                name="Example Rule",
                description="Reply to emails from example.com",
                prompt="The email is from example.com",
                enabled=True,
                actions=[
                    RuleAction(type="reply", parameters={"text": "Thank you for your email!"})
                ]
            )
            
            config = RuleConfig(rules=[rule])
            
            # Save the config
            save_rules(config, temp_path)
            
            # Load the config
            loaded_config = load_rules(temp_path)
            
            # Verify the loaded config matches the original
            assert len(loaded_config.rules) == 1
            loaded_rule = loaded_config.rules[0]
            assert isinstance(loaded_rule, NaturalLanguageRule)
            assert loaded_rule.name == rule.name
            assert loaded_rule.description == rule.description
            assert loaded_rule.prompt == rule.prompt
            assert loaded_rule.enabled == rule.enabled
            assert len(loaded_rule.actions) == 1
            loaded_action = loaded_rule.actions[0]
            assert loaded_action.type == rule.actions[0].type
            assert loaded_action.parameters == rule.actions[0].parameters
            
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_load_rules_file_not_found(self):
        """Test loading rules when the file doesn't exist."""
        # Try to load a non-existent file
        non_existent_path = "/path/to/non/existent/file.yaml"
        
        # Verify that an empty config is returned
        config = load_rules(non_existent_path)
        assert isinstance(config, RuleConfig)
        assert len(config.rules) == 0
"""Configuration module for the stoppls application."""

import importlib.metadata
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

import yaml


def get_version():
    """Returns the current version of the application from package metadata."""
    try:
        return importlib.metadata.version("stoppls")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0-dev"  # Development version when not installed


@dataclass
class RuleAction:
    """Represents an action to take when a rule matches.

    Attributes:
        type: The type of action (reply, archive, label, etc.)
        parameters: Parameters for the action (e.g., reply text)
    """

    type: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rule(ABC):
    """Base class for email processing rules.

    Attributes:
        name: The name of the rule
        description: A description of what the rule does
        enabled: Whether the rule is enabled
        actions: Actions to take when the rule matches
    """

    name: str
    description: str
    enabled: bool = True
    actions: List[RuleAction] = field(default_factory=list)

    @abstractmethod
    def get_prompt_section(self) -> str:
        """Get the prompt section for this rule to be used in AI evaluation.

        Returns:
            str: The prompt section for this rule
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert the rule to a dictionary."""
        result = {
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "type": self.__class__.__name__,
            "actions": [
                {"type": action.type, "parameters": action.parameters}
                for action in self.actions
            ],
        }
        # Add subclass-specific fields
        result.update(self._to_dict_specific())
        return result

    @abstractmethod
    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert subclass-specific fields to a dictionary.

        Returns:
            Dict[str, Any]: Subclass-specific fields as a dictionary
        """
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        """Create a rule from a dictionary."""
        rule_type = data.get("type", "NaturalLanguageRule")

        if rule_type == "NaturalLanguageRule":
            return NaturalLanguageRule(
                name=data["name"],
                description=data["description"],
                prompt=data["prompt"],
                enabled=data.get("enabled", True),
                actions=[
                    RuleAction(
                        type=action["type"], parameters=action.get("parameters", {})
                    )
                    for action in data.get("actions", [])
                ],
            )
        else:
            raise ValueError(f"Unknown rule type: {rule_type}")


@dataclass
class NaturalLanguageRule(Rule):
    """A rule defined using natural language.

    Attributes:
        prompt: Natural language prompt describing when this rule should apply
    """

    prompt: str = ""

    def get_prompt_section(self) -> str:
        """Get the prompt section for this rule.

        Returns:
            str: The prompt section for this rule
        """
        return f"Rule: {self.name}\nDescription: {self.description}\nCriteria: {self.prompt}"

    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert subclass-specific fields to a dictionary.

        Returns:
            Dict[str, Any]: Subclass-specific fields as a dictionary
        """
        return {"prompt": self.prompt}


@dataclass
class RuleConfig:
    """Configuration for email processing rules.

    Attributes:
        rules: List of rules for processing emails
    """

    rules: List[Rule] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary."""
        return {"rules": [rule.to_dict() for rule in self.rules]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuleConfig":
        """Create a configuration from a dictionary."""
        return cls(
            rules=[Rule.from_dict(rule_data) for rule_data in data.get("rules", [])]
        )


def load_rules(config_path: str) -> RuleConfig:
    """Load rules from a YAML configuration file.

    Args:
        config_path: Path to the configuration file

    Returns:
        RuleConfig: The loaded configuration
    """
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
            return RuleConfig.from_dict(data or {})
    except FileNotFoundError:
        return RuleConfig()


def save_rules(config: RuleConfig, config_path: str) -> None:
    """Save rules to a YAML configuration file.

    Args:
        config: The configuration to save
        config_path: Path to the configuration file
    """
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)

    # Save the configuration
    with open(config_path, "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False)

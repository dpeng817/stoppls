"""Rule engine for evaluating emails against rules."""

import logging
import os
from dataclasses import dataclass
from typing import List, Optional

import anthropic

from stoppls.config import Rule, RuleAction, RuleConfig
from stoppls.email_providers.base import EmailMessage


@dataclass
class RuleResult:
    """Result of evaluating a rule against an email.

    Attributes:
        rule: The rule that was evaluated
        matched: Whether the rule matched the email
        actions: Actions to take if the rule matched
    """

    rule: Rule
    matched: bool
    actions: List[RuleAction]


class RuleEngine:
    """Engine for evaluating emails against rules.

    This class uses AI to determine if rules match emails and returns
    the actions to take for matching rules.
    """

    def __init__(
        self, rule_config: RuleConfig, anthropic_api_key: Optional[str] = None
    ):
        """Initialize the rule engine.

        Args:
            rule_config: Configuration containing rules to evaluate
            anthropic_api_key: API key for Anthropic Claude (defaults to ANTHROPIC_API_KEY env var)
        """
        self.rule_config = rule_config
        self.logger = logging.getLogger(__name__)

        # Get the Anthropic API key
        self.anthropic_api_key = anthropic_api_key or os.environ.get(
            "ANTHROPIC_API_KEY"
        )

        # Initialize the Anthropic client if we have an API key
        self.anthropic_client = None
        if self.anthropic_api_key:
            # Create the Anthropic client with only the required api_key parameter
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)

    def evaluate_email(self, email: EmailMessage) -> List[RuleResult]:
        """Evaluate an email against all enabled rules.

        Args:
            email: The email to evaluate

        Returns:
            List[RuleResult]: Results for rules that matched the email
        """
        self.logger.debug(f"Evaluating email: {email.subject} from {email.sender}")

        results = []

        # Evaluate each enabled rule
        for rule in self.rule_config.rules:
            if not rule.enabled:
                self.logger.debug(f"Skipping disabled rule: {rule.name}")
                continue

            self.logger.debug(f"Evaluating rule: {rule.name}")

            # Evaluate the rule
            matched = self._evaluate_rule_with_ai(rule, email)

            if matched:
                self.logger.info(f"Rule matched: {rule.name}")
                results.append(
                    RuleResult(rule=rule, matched=True, actions=rule.actions)
                )
            else:
                self.logger.debug(f"Rule did not match: {rule.name}")

        self.logger.info(f"Evaluation complete. {len(results)} rules matched.")
        return results

    def _evaluate_rule_with_ai(self, rule: Rule, email: EmailMessage) -> bool:
        """Evaluate a rule against an email using AI.

        Args:
            rule: The rule to evaluate
            email: The email to evaluate

        Returns:
            bool: True if the rule matches the email, False otherwise
        """
        if not self.anthropic_client:
            self.logger.error("No Anthropic API key provided. Cannot evaluate rules.")
            return False

        try:
            # Create the system prompt
            system_prompt = self._create_system_prompt(rule)

            # Create the user prompt with email details
            user_prompt = self._create_user_prompt(email)

            # Call the Anthropic API
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=100,
                temperature=0.0,
            )

            # Extract the response text
            response_text = response.content[0].text

            # Determine if the rule matches
            return self._parse_ai_response(response_text)

        except Exception as e:
            self.logger.error(f"Error evaluating rule with AI: {e}")
            return False

    def _create_system_prompt(self, rule: Rule) -> str:
        """Create the system prompt for the AI.

        Args:
            rule: The rule to evaluate

        Returns:
            str: The system prompt
        """
        return f"""
        You are an email processing assistant that determines if an email matches a specific rule.
        
        {rule.get_prompt_section()}
        
        Respond with a clear "Yes" or "No" at the beginning of your response, followed by a brief explanation.
        Only say "Yes" if the email clearly matches the criteria above.
        """

    def _create_user_prompt(self, email: EmailMessage) -> str:
        """Create the user prompt with email details.

        Args:
            email: The email to evaluate

        Returns:
            str: The user prompt
        """
        return f"""
        Please evaluate if the following email matches the rule:
        
        From: {email.sender}
        To: {', '.join(email.recipients)}
        Subject: {email.subject}
        Date: {email.date}
        
        Body:
        {email.body_text}
        
        Does this email match the rule criteria? Answer with Yes or No.
        """

    def _parse_ai_response(self, response_text: str) -> bool:
        """Parse the AI response to determine if the rule matches.

        Args:
            response_text: The AI response text

        Returns:
            bool: True if the rule matches, False otherwise
        """
        # Clean and lowercase the response
        clean_response = response_text.strip().lower()

        # Check if the response starts with "yes"
        return clean_response.startswith("yes")

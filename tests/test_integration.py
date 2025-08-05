"""Integration tests for the StopPls application."""

import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
import yaml

from stoppls.config import RuleConfig, load_rules
from stoppls.email_monitor import EmailMonitor
from stoppls.email_providers.base import EmailMessage
from stoppls.email_providers.memory import InMemoryEmailProvider
from stoppls.rule_engine import RuleEngine


class TestIntegration:
    """Integration tests for the StopPls application."""

    @pytest.fixture
    def memory_provider(self):
        """Create an in-memory email provider for testing."""
        provider = InMemoryEmailProvider()
        provider.connect()
        return provider

    @pytest.fixture
    def temp_rules_file(self):
        """Create a temporary rules file for testing."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp:
            # Write test rules to the file
            rules_yaml = """
            rules:
              - name: "Reply to Recruiters"
                description: "Automatically reply to recruiter emails"
                type: "NaturalLanguageRule"
                prompt: "The email is from a recruiter or about a job opportunity."
                enabled: true
                actions:
                  - type: "reply"
                    parameters:
                      text: "Thank you for reaching out about this opportunity. I'm currently not looking for new positions, but I appreciate your consideration."
                  - type: "label"
                    parameters:
                      label: "Recruiters"

              - name: "Archive Newsletters"
                description: "Automatically archive newsletter emails"
                type: "NaturalLanguageRule"
                prompt: "The email is a newsletter or marketing email."
                enabled: true
                actions:
                  - type: "archive"
                    parameters: {}
                  - type: "label"
                    parameters:
                      label: "Newsletters"
            """
            temp.write(rules_yaml)
            temp_path = temp.name

        # Return the path to the temporary file
        yield temp_path

        # Clean up the temporary file
        os.unlink(temp_path)

    def test_recruiter_email_detection(self, memory_provider, temp_rules_file):
        """Test that recruiter emails are correctly identified and processed."""
        # Skip test if no API key is available
        print("ENVIRONMENT VARIABLES:")
        print(os.environ)
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("No Anthropic API key available")

        # Create a test recruiter email
        now = datetime.now()
        recruiter_email = EmailMessage(
            message_id="rec1",
            thread_id="thread1",
            sender="recruiter@company.com",
            recipients=["me@example.com"],
            subject="Exciting Job Opportunity",
            body_text="""
            Hi there,

            I hope this email finds you well. I'm a recruiter at Company XYZ, and I came across your profile.
            We have an exciting job opportunity for a Senior Software Engineer that I think would be a great fit for your skills.

            Would you be interested in discussing this role further?

            Best regards,
            John Recruiter
            """,
            date=now - timedelta(hours=1),
        )

        # Add the email to the provider
        memory_provider.add_message(recruiter_email)

        # Create the email monitor with the in-memory provider
        monitor = EmailMonitor(
            email_provider=memory_provider,
            monitored_addresses=["recruiter@company.com"],
            rule_config_path=temp_rules_file,
            anthropic_api_key=api_key,
            read_only=False,  # We want to execute actions
        )

        # Set the last check time to ensure our test email is processed
        monitor.last_check_time = now - timedelta(hours=2)

        # Run a single iteration
        success = monitor.run_single_iteration()
        assert success, "Failed to run single iteration"

        # Verify that the recruiter email was replied to
        assert len(memory_provider.replied_messages) == 1, "Recruiter email was not replied to"
        assert memory_provider.replied_messages[0]["original_message"] == recruiter_email
        assert "not looking for new positions" in memory_provider.replied_messages[0]["reply_text"]

        # Verify that the recruiter email was labeled
        assert len(memory_provider.labeled_messages) == 1, "Recruiter email was not labeled"
        assert memory_provider.labeled_messages[0]["message"] == recruiter_email
        assert memory_provider.labeled_messages[0]["label"] == "Recruiters"

    def test_newsletter_email_detection(self, memory_provider, temp_rules_file):
        """Test that newsletter emails are correctly identified and processed."""
        # Skip test if no API key is available
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("No Anthropic API key available")

        # Create a test newsletter email
        now = datetime.now()
        newsletter_email = EmailMessage(
            message_id="news1",
            thread_id="thread2",
            sender="newsletter@company.com",
            recipients=["me@example.com"],
            subject="Weekly Newsletter: Latest Updates",
            body_text="""
            # Company XYZ Weekly Newsletter

            Hello subscribers,

            Here are this week's top stories:
            - New product launch
            - Company updates
            - Industry news

            Thank you for subscribing to our newsletter!
            
            To unsubscribe, click here.
            """,
            date=now - timedelta(hours=1),
        )

        # Add the email to the provider
        memory_provider.add_message(newsletter_email)

        # Create the email monitor with the in-memory provider
        monitor = EmailMonitor(
            email_provider=memory_provider,
            monitored_addresses=["newsletter@company.com"],
            rule_config_path=temp_rules_file,
            anthropic_api_key=api_key,
            read_only=False,  # We want to execute actions
        )

        # Set the last check time to ensure our test email is processed
        monitor.last_check_time = now - timedelta(hours=2)

        # Run a single iteration
        success = monitor.run_single_iteration()
        assert success, "Failed to run single iteration"

        # Verify that the newsletter email was archived
        assert len(memory_provider.archived_messages) == 1, "Newsletter email was not archived"
        assert memory_provider.archived_messages[0] == newsletter_email

        # Verify that the newsletter email was labeled
        assert len(memory_provider.labeled_messages) == 1, "Newsletter email was not labeled"
        assert memory_provider.labeled_messages[0]["message"] == newsletter_email
        assert memory_provider.labeled_messages[0]["label"] == "Newsletters"

    def test_regular_email_no_action(self, memory_provider, temp_rules_file):
        """Test that regular emails don't trigger any actions."""
        # Skip test if no API key is available
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("No Anthropic API key available")

        # Create a test regular email
        now = datetime.now()
        regular_email = EmailMessage(
            message_id="reg1",
            thread_id="thread3",
            sender="friend@example.com",
            recipients=["me@example.com"],
            subject="Catching up",
            body_text="""
            Hey,

            How have you been? It's been a while since we caught up.
            Would you like to grab coffee sometime next week?

            Cheers,
            Your Friend
            """,
            date=now - timedelta(hours=1),
        )

        # Add the email to the provider
        memory_provider.add_message(regular_email)

        # Create the email monitor with the in-memory provider
        monitor = EmailMonitor(
            email_provider=memory_provider,
            monitored_addresses=["friend@example.com"],
            rule_config_path=temp_rules_file,
            anthropic_api_key=api_key,
            read_only=False,  # We want to execute actions
        )

        # Set the last check time to ensure our test email is processed
        monitor.last_check_time = now - timedelta(hours=2)

        # Run a single iteration
        success = monitor.run_single_iteration()
        assert success, "Failed to run single iteration"

        # Verify that no actions were taken on the regular email
        assert len(memory_provider.replied_messages) == 0, "Regular email was replied to"
        assert len(memory_provider.archived_messages) == 0, "Regular email was archived"
        assert len(memory_provider.labeled_messages) == 0, "Regular email was labeled"

    def test_read_only_mode(self, memory_provider, temp_rules_file):
        """Test that read-only mode logs actions but doesn't execute them."""
        # Skip test if no API key is available
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("No Anthropic API key available")

        # Create a test recruiter email
        now = datetime.now()
        recruiter_email = EmailMessage(
            message_id="rec2",
            thread_id="thread4",
            sender="recruiter@company.com",
            recipients=["me@example.com"],
            subject="Exciting Job Opportunity",
            body_text="""
            Hi there,

            I hope this email finds you well. I'm a recruiter at Company XYZ, and I came across your profile.
            We have an exciting job opportunity for a Senior Software Engineer that I think would be a great fit for your skills.

            Would you be interested in discussing this role further?

            Best regards,
            John Recruiter
            """,
            date=now - timedelta(hours=1),
        )

        # Add the email to the provider
        memory_provider.add_message(recruiter_email)

        # Create the email monitor with the in-memory provider in read-only mode
        monitor = EmailMonitor(
            email_provider=memory_provider,
            monitored_addresses=["recruiter@company.com"],
            rule_config_path=temp_rules_file,
            anthropic_api_key=api_key,
            read_only=True,  # Enable read-only mode
        )

        # Set the last check time to ensure our test email is processed
        monitor.last_check_time = now - timedelta(hours=2)

        # Run a single iteration
        with patch("logging.Logger.info") as mock_logger_info:
            success = monitor.run_single_iteration()
            assert success, "Failed to run single iteration"

            # Verify that actions were logged but not executed
            mock_logger_info.assert_any_call("[READ-ONLY] Would execute actions for rule: Reply to Recruiters")
            mock_logger_info.assert_any_call("[READ-ONLY] Would reply to message: Exciting Job Opportunity")
            mock_logger_info.assert_any_call("[READ-ONLY] Would apply label 'Recruiters' to message: Exciting Job Opportunity")

        # Verify that no actual actions were taken
        assert len(memory_provider.replied_messages) == 0, "Email was replied to in read-only mode"
        assert len(memory_provider.archived_messages) == 0, "Email was archived in read-only mode"
        assert len(memory_provider.labeled_messages) == 0, "Email was labeled in read-only mode"
"""Email monitoring service for checking and processing new emails."""

import logging
import threading
import time
from datetime import datetime
from typing import List, Optional

from stoppls.config import load_rules
from stoppls.email_providers.base import EmailMessage, EmailProvider
from stoppls.rule_engine import RuleAction, RuleEngine, RuleResult


class EmailMonitor:
    """Service for monitoring and processing new emails.

    This class periodically checks for new emails from specified addresses
    and processes them according to configured rules.
    """

    def __init__(
        self,
        email_provider: EmailProvider,
        check_interval: int = 60,
        monitored_addresses: Optional[List[str]] = None,
        rule_config_path: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        read_only: bool = False,
        enable_reports: bool = True,
        report_time: Optional[time] = None,
    ):
        """Initialize the email monitor.

        Args:
            email_provider: The email provider to use for checking emails.
            check_interval: How often to check for new emails, in seconds.
            monitored_addresses: List of email addresses to monitor.
            rule_config_path: Path to the rule configuration file.
            anthropic_api_key: API key for Anthropic Claude.
            read_only: If True, actions will be logged but not executed.
            enable_reports: Whether to enable daily reports.
            report_time: Time of day to send daily reports.
        """
        self.email_provider = email_provider
        self.check_interval = check_interval
        self.monitored_addresses = monitored_addresses or []
        self.rule_config_path = rule_config_path
        self.anthropic_api_key = anthropic_api_key
        self.read_only = read_only
        self.enable_reports = enable_reports

        # Load rule configuration if provided
        self.rule_config = None
        self.rule_engine = None
        if rule_config_path:
            self.rule_config = load_rules(rule_config_path)
            self.rule_engine = RuleEngine(
                rule_config=self.rule_config, anthropic_api_key=anthropic_api_key
            )

        # Initialize action tracker if reports are enabled
        self.action_tracker = None
        if enable_reports:
            from stoppls.reporting.action_tracker import ActionTracker

            self.action_tracker = ActionTracker(report_time=report_time)

        self.last_check_time = None
        self.is_running = False
        self._thread = None
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start the email monitoring service.

        This method starts a background thread that periodically checks for new emails.
        """
        if self.is_running:
            self.logger.warning("Email monitor is already running")
            return

        self.logger.info("Starting email monitor")
        if self.read_only:
            self.logger.info(
                "Running in READ-ONLY mode - actions will be logged but not executed"
            )

        # Connect to the email provider
        if not self.email_provider.is_connected():
            success = self.email_provider.connect()
            if not success:
                self.logger.error("Failed to connect to email provider")
                return

        # Start the monitoring thread
        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop)
        self._thread.daemon = True  # Thread will exit when main program exits
        self._thread.start()

        self.logger.info("Email monitor started")

    def stop(self):
        """Stop the email monitoring service.

        This method stops the background thread and disconnects from the email provider.
        """
        if not self.is_running:
            self.logger.warning("Email monitor is not running")
            return

        self.logger.info("Stopping email monitor")

        # Stop the thread
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

        # Disconnect from the email provider
        if self.email_provider.is_connected():
            self.email_provider.disconnect()

        self.logger.info("Email monitor stopped")

    def check_for_new_messages(self):
        """Check for new messages and process them.

        This method fetches new messages from the email provider and processes each one.
        """
        self.logger.debug("Checking for new messages")

        # Get the current time
        now = datetime.now()

        # If this is the first run, just set the last check time and return
        if self.last_check_time is None:
            self.logger.info("First run, setting last check time")
            self.last_check_time = now
            return

        try:
            # Get new messages since the last check
            messages = self.email_provider.get_messages(
                from_addresses=self.monitored_addresses, since=self.last_check_time
            )

            self.logger.info(f"Found {len(messages)} new messages")

            # Process each message
            for message in messages:
                self.process_message(message)

        except Exception as e:
            self.logger.error(f"Error checking for new messages: {e}")

        # Update the last check time
        self.last_check_time = now

    def process_message(self, message: EmailMessage):
        """Process a single email message.

        This method applies rules to determine what actions to take on the message.

        Args:
            message: The email message to process.
        """
        self.logger.info(f"Processing message: {message.subject} from {message.sender}")

        # Log message details
        self.logger.debug(f"Message ID: {message.message_id}")
        self.logger.debug(f"Thread ID: {message.thread_id}")
        self.logger.debug(f"Date: {message.date}")
        self.logger.debug(f"Subject: {message.subject}")
        self.logger.debug(f"From: {message.sender}")
        self.logger.debug(f"To: {message.recipients}")

        # If we have a rule engine, evaluate the message against rules
        if self.rule_engine:
            self.logger.debug("Evaluating message against rules")
            rule_results = self.rule_engine.evaluate_email(message)

            # Execute actions for matching rules
            for result in rule_results:
                self.execute_actions(message, result)
        else:
            self.logger.debug("No rule engine configured, skipping rule evaluation")

    def execute_actions(self, message: EmailMessage, rule_result: RuleResult):
        """Execute actions for a matching rule.

        Args:
            message: The email message to act on.
            rule_result: The result of evaluating a rule against the message.
        """
        if self.read_only:
            self.logger.info(
                f"[READ-ONLY] Would execute actions for rule: {rule_result.rule.name}"
            )
            # Log each action that would be taken but don't execute them
            for action in rule_result.actions:
                if action.type == "reply":
                    reply_text = action.parameters.get("text", "")
                    self.logger.info(
                        f"[READ-ONLY] Would reply to message: {message.subject}"
                    )
                    self.logger.debug(f"[READ-ONLY] Reply text would be: {reply_text}")
                elif action.type == "archive":
                    self.logger.info(
                        f"[READ-ONLY] Would archive message: {message.subject}"
                    )
                elif action.type == "label":
                    label = action.parameters.get("label", "")
                    if label:
                        self.logger.info(
                            f"[READ-ONLY] Would apply label '{label}' to message: {message.subject}"
                        )
                    else:
                        self.logger.warning(
                            "[READ-ONLY] Would attempt to apply label, but no label specified"
                        )
                else:
                    self.logger.warning(
                        f"[READ-ONLY] Would attempt unknown action type: {action.type}"
                    )
            # Return early to avoid executing any actions
            return

        self.logger.info(f"Executing actions for rule: {rule_result.rule.name}")

        for action in rule_result.actions:
            self.logger.debug(f"Executing action: {action.type}")

            try:
                success = False

                if action.type == "reply":
                    success = self._execute_reply_action(message, action)
                elif action.type == "archive":
                    success = self._execute_archive_action(message, action)
                elif action.type == "label":
                    success = self._execute_label_action(message, action)
                else:
                    self.logger.warning(f"Unknown action type: {action.type}")
                    continue  # Skip recording unknown actions

                # Record the action if it was successful and action tracker is enabled
                if success and self.action_tracker:
                    self.action_tracker.record_action(
                        message=message, action=action, rule_name=rule_result.rule.name
                    )

            except Exception as e:
                self.logger.error(f"Error executing action {action.type}: {e}")

    def _execute_reply_action(self, message: EmailMessage, action: RuleAction):
        """Execute a reply action.

        Args:
            message: The email message to reply to.
            action: The reply action to execute.

        Returns:
            bool: True if the action was successful, False otherwise.
        """
        # No need to check read_only here since execute_actions already handles it
        reply_text = action.parameters.get("text", "")
        reply_html = action.parameters.get("html")

        self.logger.info(f"Replying to message: {message.subject}")
        self.logger.debug(f"Reply text: {reply_text}")

        success = self.email_provider.send_reply(
            original_message=message, reply_text=reply_text, reply_html=reply_html
        )

        if success:
            self.logger.info("Reply sent successfully")
        else:
            self.logger.error("Failed to send reply")

        return success

    def _execute_archive_action(self, message: EmailMessage, action: RuleAction):
        """Execute an archive action.

        Args:
            message: The email message to archive.
            action: The archive action to execute.

        Returns:
            bool: True if the action was successful, False otherwise.
        """
        # No need to check read_only here since execute_actions already handles it
        self.logger.info(f"Archiving message: {message.subject}")

        success = self.email_provider.archive_message(message)

        if success:
            self.logger.info("Message archived successfully")
        else:
            self.logger.error("Failed to archive message")

        return success

    def _execute_label_action(self, message: EmailMessage, action: RuleAction):
        """Execute a label action.

        Args:
            message: The email message to label.
            action: The label action to execute.

        Returns:
            bool: True if the action was successful, False otherwise.
        """
        # No need to check read_only here since execute_actions already handles it
        label = action.parameters.get("label", "")

        if not label:
            self.logger.warning("No label specified in label action")
            return False

        self.logger.info(f"Applying label '{label}' to message: {message.subject}")

        success = self.email_provider.apply_label(message, label)

        if success:
            self.logger.info("Label applied successfully")
        else:
            self.logger.error("Failed to apply label")

        return success

    def _run_loop(self):
        """Run the monitoring loop.

        This method runs in a background thread and periodically checks for new messages.
        """
        self.logger.debug("Starting monitoring loop")

        while self.is_running:
            try:
                # Check for new messages
                self.check_for_new_messages()

                # Check if it's time to send a daily report
                if self.action_tracker and self.monitored_addresses:
                    # Send report to the first monitored address
                    recipient = self.monitored_addresses[0]
                    self.action_tracker.check_and_send_daily_report(
                        email_provider=self.email_provider, recipient_email=recipient
                    )

                # Sleep for the check interval
                time.sleep(self.check_interval)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")

                # Sleep for a short time to avoid tight loop in case of persistent errors
                time.sleep(5)

        self.logger.debug("Monitoring loop stopped")

    def run_single_iteration(self):
        """Run a single iteration of the monitoring loop.

        This method is useful for testing and integration tests.
        It runs a single check for new messages without starting a background thread.

        Returns:
            bool: True if the iteration completed successfully, False otherwise.
        """
        self.logger.debug("Running single iteration of monitoring loop")

        if not self.email_provider.is_connected():
            success = self.email_provider.connect()
            if not success:
                self.logger.error("Failed to connect to email provider")
                return False

        try:
            # Check for new messages
            self.check_for_new_messages()
            return True
        except Exception as e:
            self.logger.error(f"Error in single iteration: {e}")
            return False
        finally:
            # Don't disconnect, as the provider might be reused
            pass

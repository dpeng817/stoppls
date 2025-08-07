"""Action tracking system for StopPls."""

import json
import logging
import os
import uuid
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional

from stoppls.config import RuleAction
from stoppls.email_providers.base import EmailMessage, EmailProvider


class ActionTracker:
    """Tracks actions taken by the email monitor and sends daily reports.

    This class records actions (reply, archive, label) taken on emails
    and provides methods to retrieve and analyze those actions.
    """

    def __init__(
        self, storage_path: Optional[str] = None, report_time: Optional[time] = None
    ):
        """Initialize the action tracker.

        Args:
            storage_path: Path to store action records. If None, uses a default location.
            report_time: Time of day to send the daily report (default: 9:00 AM)
        """
        self.logger = logging.getLogger(__name__)

        # Set default storage path if not provided
        if storage_path is None:
            config_dir = os.path.expanduser("~/.config/stoppls")
            os.makedirs(config_dir, exist_ok=True)
            self.storage_path = os.path.join(config_dir, "actions.json")
        else:
            self.storage_path = storage_path

        # Set default report time if not provided
        self.report_time = report_time or time(9, 0)  # Default to 9:00 AM

        # Create the storage file if it doesn't exist
        if not os.path.exists(self.storage_path):
            self._initialize_storage()

    def _initialize_storage(self):
        """Initialize the storage file with an empty actions list."""
        with open(self.storage_path, "w") as f:
            json.dump({"actions": [], "last_report_date": None}, f)

    def _load_actions(self) -> Dict:
        """Load actions from the storage file.

        Returns:
            Dict containing the actions data.
        """
        try:
            with open(self.storage_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.error(f"Error loading actions: {e}")
            return {"actions": [], "last_report_date": None}

    def _save_actions(self, data: Dict):
        """Save actions to the storage file.

        Args:
            data: Dict containing the actions data.
        """
        try:
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving actions: {e}")

    def record_action(self, message: EmailMessage, action: RuleAction, rule_name: str):
        """Record an action taken on an email message.

        Args:
            message: The email message the action was taken on
            action: The action that was taken
            rule_name: The name of the rule that triggered the action
        """
        # Create the action record
        action_record = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "action_type": action.type,
            "message_id": message.message_id,
            "message_subject": message.subject,
            "sender": message.sender,
            "rule_name": rule_name,
            "details": action.parameters,
        }

        # Load existing actions
        data = self._load_actions()

        # Add the new action
        data["actions"].append(action_record)

        # Save the updated actions
        self._save_actions(data)

        self.logger.debug(
            f"Recorded {action.type} action for message: {message.subject}"
        )

    def get_actions_for_day(self, day: Optional[date] = None) -> List[Dict]:
        """Get actions for a specific day.

        Args:
            day: The day to get actions for (defaults to today)

        Returns:
            List of action records for the specified day
        """
        # Set default day if not provided
        if day is None:
            day = datetime.now().date()

        # Calculate start and end times for the day
        start_time = datetime.combine(day, time(0, 0, 0))
        end_time = datetime.combine(day, time(23, 59, 59))

        # Load all actions
        data = self._load_actions()
        actions = data["actions"]

        # Filter actions for the specified day
        day_actions = []
        for action in actions:
            action_time = datetime.fromisoformat(action["timestamp"])
            if start_time <= action_time <= end_time:
                day_actions.append(action)

        return day_actions

    def clear_old_actions(self, days_to_keep: int = 30):
        """Remove actions older than the specified number of days.

        Args:
            days_to_keep: Number of days of actions to keep
        """
        # Calculate the cutoff date
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        # Load all actions
        data = self._load_actions()

        # Filter out old actions
        new_actions = []
        removed_count = 0

        for action in data["actions"]:
            action_time = datetime.fromisoformat(action["timestamp"])

            if action_time >= cutoff_date:
                new_actions.append(action)
            else:
                removed_count += 1

        # Save the filtered actions
        data["actions"] = new_actions
        self._save_actions(data)

        self.logger.info(f"Cleared {removed_count} old actions")

    def generate_daily_report(
        self, day: Optional[date] = None, format: str = "html"
    ) -> str:
        """Generate a daily report for the specified day.

        Args:
            day: The day to generate the report for (defaults to yesterday)
            format: Output format ("text", "html", "markdown")

        Returns:
            The report as a string in the specified format
        """
        # Set default day if not provided (yesterday)
        if day is None:
            day = (datetime.now() - timedelta(days=1)).date()

        # Get actions for the day
        actions = self.get_actions_for_day(day)

        # Count actions by type
        action_counts = {}
        for action in actions:
            action_type = action["action_type"]
            action_counts[action_type] = action_counts.get(action_type, 0) + 1

        # Generate the report based on the requested format
        if format == "html":
            return self._generate_html_report(day, actions, action_counts)
        elif format == "markdown":
            return self._generate_markdown_report(day, actions, action_counts)
        else:  # Default to text
            return self._generate_text_report(day, actions, action_counts)

    def _generate_text_report(
        self, day: date, actions: List[Dict], action_counts: Dict[str, int]
    ) -> str:
        """Generate a text report.

        Args:
            day: The day the report is for
            actions: List of actions for the day
            action_counts: Count of actions by type

        Returns:
            The report as a string in text format
        """
        # Format the date
        date_str = day.strftime("%B %d, %Y")

        # Start with the report header
        report = f"StopPls Daily Report for {date_str}\n\n"

        # Add summary information
        report += f"Total actions: {len(actions)}\n"

        # Add counts by action type
        for action_type, count in action_counts.items():
            report += f"{action_type.capitalize()}s: {count}\n"

        # If there are no actions, add a message
        if not actions:
            report += "\nNo actions were taken on this day.\n"
            return report

        # Add detailed action information
        report += "\nDetailed Actions:\n"

        for action in actions:
            report += (
                f"\n- {action['action_type'].upper()}: {action['message_subject']}\n"
            )
            report += f"  From: {action['sender']}\n"
            report += f"  Rule: {action['rule_name']}\n"

            # Add action-specific details
            if action["action_type"] == "reply" and "text" in action["details"]:
                report += f"  Reply: {action['details']['text'][:100]}...\n"
            elif action["action_type"] == "label" and "label" in action["details"]:
                report += f"  Label: {action['details']['label']}\n"

        return report

    def _generate_html_report(
        self, day: date, actions: List[Dict], action_counts: Dict[str, int]
    ) -> str:
        """Generate an HTML report.

        Args:
            day: The day the report is for
            actions: List of actions for the day
            action_counts: Count of actions by type

        Returns:
            The report as a string in HTML format
        """
        # Format the date
        date_str = day.strftime("%B %d, %Y")

        # Start with the HTML header
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333366; }}
                h2 {{ color: #666699; margin-top: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
                th, td {{ text-align: left; padding: 8px; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .summary {{ background-color: #eef; padding: 10px; border-radius: 5px; }}
                .no-actions {{ color: #666; font-style: italic; }}
            </style>
        </head>
        <body>
            <h1>StopPls Daily Report for {date_str}</h1>
            
            <div class="summary">
                <h2>Summary</h2>
                <p>Total actions: {len(actions)}</p>
        """

        # Add counts by action type
        for action_type, count in action_counts.items():
            # Fix the pluralization - use "Replies" instead of "Replys"
            action_type_plural = (
                "Replies" if action_type == "reply" else f"{action_type.capitalize()}s"
            )
            html += f"<p>{action_type_plural}: {count}</p>\n"

        html += "</div>\n"

        # If there are no actions, add a message
        if not actions:
            html += '<p class="no-actions">No actions were taken on this day.</p>\n'
            html += "</body></html>"
            return html

        # Add detailed action information
        html += "<h2>Detailed Actions</h2>\n"
        html += "<table>\n<tr><th>Action</th><th>Subject</th><th>From</th><th>Rule</th><th>Details</th></tr>\n"

        for action in actions:
            html += f"<tr>\n<td>{action['action_type']}</td>\n"
            html += f"<td>{action['message_subject']}</td>\n"
            html += f"<td>{action['sender']}</td>\n"
            html += f"<td>{action['rule_name']}</td>\n"

            # Add action-specific details
            details = ""
            if action["action_type"] == "reply" and "text" in action["details"]:
                reply_text = action["details"]["text"]
                if len(reply_text) > 100:
                    reply_text = reply_text[:100] + "..."
                details = f"Reply: {reply_text}"
            elif action["action_type"] == "label" and "label" in action["details"]:
                details = f"Label: {action['details']['label']}"

            html += f"<td>{details}</td>\n</tr>\n"

        html += "</table>\n</body>\n</html>"
        return html

    def _generate_markdown_report(
        self, day: date, actions: List[Dict], action_counts: Dict[str, int]
    ) -> str:
        """Generate a Markdown report.

        Args:
            day: The day the report is for
            actions: List of actions for the day
            action_counts: Count of actions by type

        Returns:
            The report as a string in Markdown format
        """
        # Format the date
        date_str = day.strftime("%B %d, %Y")

        # Start with the report header
        md = f"# StopPls Daily Report for {date_str}\n\n"

        # Add summary information
        md += "## Summary\n\n"
        md += f"Total actions: {len(actions)}\n\n"

        # Add counts by action type
        for action_type, count in action_counts.items():
            md += f"{action_type.capitalize()}s: {count}\n\n"

        # If there are no actions, add a message
        if not actions:
            md += "*No actions were taken on this day.*\n"
            return md

        # Add detailed action information
        md += "## Detailed Actions\n\n"
        md += "| Action | Subject | Sender | Rule |\n"
        md += "| --- | --- | --- | --- |\n"

        for action in actions:
            md += f"| {action['action_type']} | {action['message_subject']} | {action['sender']} | {action['rule_name']} |\n"

        # Add action-specific details in a separate section
        md += "\n## Action Details\n\n"

        for i, action in enumerate(actions):
            md += f"### {i + 1}. {action['action_type'].upper()}: {action['message_subject']}\n\n"

            # Add action-specific details
            if action["action_type"] == "reply" and "text" in action["details"]:
                md += f"**Reply text:**\n\n```\n{action['details']['text']}\n```\n\n"
            elif action["action_type"] == "label" and "label" in action["details"]:
                md += f"**Label:** {action['details']['label']}\n\n"

        return md

    def send_daily_report(
        self,
        email_provider: EmailProvider,
        recipient_email: str,
        day: Optional[date] = None,
    ) -> bool:
        """Send a daily report via email.

        Args:
            email_provider: The email provider to use for sending
            recipient_email: Email address to send the report to
            day: The day to generate the report for (defaults to yesterday)

        Returns:
            True if the report was sent successfully, False otherwise
        """
        # Set default day if not provided (yesterday)
        if day is None:
            day = (datetime.now() - timedelta(days=1)).date()

        # Format the date for the subject
        date_str = day.strftime("%B %d, %Y")

        # Generate the report in HTML format
        report_html = self.generate_daily_report(day=day, format="html")

        # Generate a plain text version as well
        report_text = self.generate_daily_report(day=day, format="text")

        # Check if the email provider is connected
        if not email_provider.is_connected():
            success = email_provider.connect()
            if not success:
                self.logger.error("Failed to connect to email provider")
                return False

        # Send the email
        subject = f"StopPls Daily Report: {date_str}"

        try:
            success = email_provider.send_email(
                to=recipient_email,
                subject=subject,
                body_text=report_text,
                body_html=report_html,
            )

            if success:
                self.logger.info(
                    f"Sent daily report for {date_str} to {recipient_email}"
                )

                # Update the last report date
                data = self._load_actions()
                data["last_report_date"] = datetime.now().date().isoformat()
                self._save_actions(data)

                return True
            else:
                self.logger.error(f"Failed to send daily report for {date_str}")
                return False

        except Exception as e:
            self.logger.error(f"Error sending daily report: {e}")
            return False

    def _get_last_report_date(self) -> Optional[date]:
        """Get the date when the last report was sent.

        Returns:
            The date when the last report was sent, or None if no report has been sent
        """
        data = self._load_actions()
        last_report_date_str = data.get("last_report_date")

        if last_report_date_str:
            return date.fromisoformat(last_report_date_str)
        else:
            return None

    def check_and_send_daily_report(
        self, email_provider: EmailProvider, recipient_email: str
    ) -> bool:
        """Check if it's time to send a daily report and send it if needed.

        This method should be called regularly from the main loop.
        It will only send a report if:
        1. It's past the configured report_time
        2. A report hasn't been sent today yet

        Args:
            email_provider: The email provider to use for sending
            recipient_email: Email address to send the report to

        Returns:
            True if a report was sent, False otherwise
        """
        # Get the current date and time
        now = datetime.now()
        today = now.date()
        current_time = now.time()

        # Get the date when the last report was sent
        last_report_date = self._get_last_report_date()

        # Check if it's time to send a report
        if current_time >= self.report_time and (
            last_report_date is None or last_report_date < today
        ):
            # Send a report for yesterday
            yesterday = today - timedelta(days=1)
            return self.send_daily_report(
                email_provider=email_provider,
                recipient_email=recipient_email,
                day=yesterday,
            )

        return False

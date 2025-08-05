"""Tests for the action tracking system."""

import json
import os
import tempfile
from datetime import datetime, date, time, timedelta
from unittest.mock import MagicMock, patch

import pytest

from stoppls.config import RuleAction
from stoppls.email_providers.base import EmailMessage, EmailProvider
from stoppls.reporting.action_tracker import ActionTracker


class TestActionTracker:
    """Tests for the ActionTracker class."""

    @pytest.fixture
    def temp_storage_file(self):
        """Create a temporary file for action storage."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp:
            temp_path = temp.name
        
        yield temp_path
        
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def mock_message(self):
        """Create a mock email message."""
        return EmailMessage(
            message_id="msg123",
            thread_id="thread1",
            sender="sender@example.com",
            recipients=["recipient@example.com"],
            subject="Test Subject",
            body_text="Test body",
            date=datetime.now()
        )

    @pytest.fixture
    def mock_reply_action(self):
        """Create a mock reply action."""
        return RuleAction(
            type="reply",
            parameters={"text": "Test reply"}
        )

    @pytest.fixture
    def mock_archive_action(self):
        """Create a mock archive action."""
        return RuleAction(
            type="archive",
            parameters={}
        )

    @pytest.fixture
    def mock_label_action(self):
        """Create a mock label action."""
        return RuleAction(
            type="label",
            parameters={"label": "Test Label"}
        )

    @pytest.fixture
    def mock_email_provider(self):
        """Create a mock email provider."""
        provider = MagicMock(spec=EmailProvider)
        provider.is_connected.return_value = True
        provider.send_email.return_value = True
        return provider

    def test_init_creates_storage_file(self, temp_storage_file):
        """Test that initializing creates the storage file if it doesn't exist."""
        # Remove the file if it exists
        if os.path.exists(temp_storage_file):
            os.unlink(temp_storage_file)
            
        # Initialize the tracker
        tracker = ActionTracker(storage_path=temp_storage_file)
        
        # Check that the file was created with the correct structure
        assert os.path.exists(temp_storage_file)
        with open(temp_storage_file, "r") as f:
            data = json.load(f)
            assert "actions" in data
            assert isinstance(data["actions"], list)
            assert len(data["actions"]) == 0

    def test_record_action(self, temp_storage_file, mock_message, mock_reply_action):
        """Test recording an action."""
        # Initialize the tracker
        tracker = ActionTracker(storage_path=temp_storage_file)
        
        # Record an action
        tracker.record_action(
            message=mock_message,
            action=mock_reply_action,
            rule_name="Test Rule"
        )
        
        # Check that the action was recorded
        with open(temp_storage_file, "r") as f:
            data = json.load(f)
            assert len(data["actions"]) == 1
            action = data["actions"][0]
            assert action["action_type"] == "reply"
            assert action["message_id"] == "msg123"
            assert action["message_subject"] == "Test Subject"
            assert action["sender"] == "sender@example.com"
            assert action["rule_name"] == "Test Rule"
            assert action["details"]["text"] == "Test reply"
            assert "timestamp" in action
            assert "id" in action

    def test_get_actions_for_day(self, temp_storage_file, mock_message):
        """Test getting actions for a specific day."""
        # Initialize the tracker
        tracker = ActionTracker(storage_path=temp_storage_file)
        
        # Create actions with specific timestamps
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # Create mock actions
        today_action = RuleAction(type="reply", parameters={"text": "Today reply"})
        yesterday_action = RuleAction(type="archive", parameters={})
        
        # Record actions with specific timestamps
        with patch("stoppls.reporting.action_tracker.datetime") as mock_datetime:
            # Mock today's action
            mock_datetime.now.return_value = datetime.combine(today, time(10, 0))
            tracker.record_action(mock_message, today_action, "Today Rule")
            
            # Mock yesterday's action
            mock_datetime.now.return_value = datetime.combine(yesterday, time(10, 0))
            tracker.record_action(mock_message, yesterday_action, "Yesterday Rule")
        
        # Get actions for today
        actions = tracker.get_actions_for_day(day=today)
        
        # Check that only today's action was returned
        assert len(actions) == 1
        assert actions[0]["action_type"] == "reply"
        assert actions[0]["details"]["text"] == "Today reply"
        
        # Get actions for yesterday
        actions = tracker.get_actions_for_day(day=yesterday)
        
        # Check that only yesterday's action was returned
        assert len(actions) == 1
        assert actions[0]["action_type"] == "archive"

    def test_clear_old_actions(self, temp_storage_file, mock_message, mock_reply_action):
        """Test clearing old actions."""
        # Initialize the tracker
        tracker = ActionTracker(storage_path=temp_storage_file)
        
        # Record actions with specific timestamps
        now = datetime.now()
        old_time = now - timedelta(days=31)
        
        # Record a recent action
        with patch("stoppls.reporting.action_tracker.datetime") as mock_datetime:
            mock_datetime.now.return_value = now
            tracker.record_action(mock_message, mock_reply_action, "Recent Rule")
        
        # Record an old action
        with patch("stoppls.reporting.action_tracker.datetime") as mock_datetime:
            mock_datetime.now.return_value = old_time
            tracker.record_action(mock_message, mock_reply_action, "Old Rule")
        
        # Clear actions older than 30 days
        tracker.clear_old_actions(days_to_keep=30)
        
        # Load all actions
        with open(temp_storage_file, "r") as f:
            data = json.load(f)
            actions = data["actions"]
        
        # Check that only the recent action remains
        assert len(actions) == 1
        assert actions[0]["rule_name"] == "Recent Rule"

    def test_generate_daily_report(self, temp_storage_file, mock_message):
        """Test generating a daily report."""
        # Initialize the tracker
        tracker = ActionTracker(storage_path=temp_storage_file)
        
        # Record actions for today
        today = datetime.now().date()
        
        # Create mock actions
        reply_action = RuleAction(type="reply", parameters={"text": "Test reply"})
        archive_action = RuleAction(type="archive", parameters={})
        label_action = RuleAction(type="label", parameters={"label": "Test Label"})
        
        # Record actions with today's timestamp
        with patch("stoppls.reporting.action_tracker.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.combine(today, time(10, 0))
            tracker.record_action(mock_message, reply_action, "Reply Rule")
            tracker.record_action(mock_message, archive_action, "Archive Rule")
            tracker.record_action(mock_message, label_action, "Label Rule")
        
        # Generate a report for today
        report = tracker.generate_daily_report(day=today)
        
        # Check that the report contains expected content
        assert "StopPls Daily Report" in report
        assert f"{today.strftime('%B %d, %Y')}" in report
        assert "Total actions: 3" in report
        assert "Replies: 1" in report
        assert "Archives: 1" in report
        assert "Labels: 1" in report
        assert "Test Subject" in report

    def test_send_daily_report(self, temp_storage_file, mock_message, mock_reply_action, mock_email_provider):
        """Test sending a daily report."""
        # Initialize the tracker
        tracker = ActionTracker(storage_path=temp_storage_file)
        
        # Record an action
        tracker.record_action(mock_message, mock_reply_action, "Test Rule")
        
        # Send a report
        success = tracker.send_daily_report(
            email_provider=mock_email_provider,
            recipient_email="recipient@example.com"
        )
        
        # Check that the email was sent
        mock_email_provider.send_email.assert_called_once()
        call_args = mock_email_provider.send_email.call_args[1]
        assert call_args["to"] == "recipient@example.com"
        assert "StopPls Daily Report" in call_args["subject"]
        assert call_args["body_html"] is not None
        
        assert success is True

    def test_check_and_send_daily_report_time_to_send(self, temp_storage_file, mock_email_provider):
        """Test checking and sending a daily report when it's time to send."""
        # Set a specific report time
        report_time = time(9, 0)  # 9:00 AM
        
        # Initialize the tracker with the report time
        tracker = ActionTracker(
            storage_path=temp_storage_file,
            report_time=report_time
        )
        
        # Mock the current time to be after the report time
        current_time = time(10, 0)  # 10:00 AM
        current_date = date(2025, 8, 5)
        
        # Mock that no report has been sent today
        tracker._get_last_report_date = MagicMock(return_value=date(2025, 8, 4))
        
        # Mock datetime.now to return our fixed time
        with patch("stoppls.reporting.action_tracker.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.combine(current_date, current_time)
            mock_datetime.combine = datetime.combine
            
            # Mock send_daily_report to return success
            tracker.send_daily_report = MagicMock(return_value=True)
            
            # Check and send the report
            result = tracker.check_and_send_daily_report(
                email_provider=mock_email_provider,
                recipient_email="recipient@example.com"
            )
            
            # Verify that send_daily_report was called
            tracker.send_daily_report.assert_called_once_with(
                email_provider=mock_email_provider,
                recipient_email="recipient@example.com",
                day=date(2025, 8, 4)  # Should send for yesterday
            )
            
            assert result is True

    def test_check_and_send_daily_report_not_time_yet(self, temp_storage_file, mock_email_provider):
        """Test checking and sending a daily report when it's not time to send yet."""
        # Set a specific report time
        report_time = time(9, 0)  # 9:00 AM
        
        # Initialize the tracker with the report time
        tracker = ActionTracker(
            storage_path=temp_storage_file,
            report_time=report_time
        )
        
        # Mock the current time to be before the report time
        current_time = time(8, 0)  # 8:00 AM
        current_date = date(2025, 8, 5)
        
        # Mock datetime.now to return our fixed time
        with patch("stoppls.reporting.action_tracker.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.combine(current_date, current_time)
            
            # Mock send_daily_report
            tracker.send_daily_report = MagicMock()
            
            # Check and send the report
            result = tracker.check_and_send_daily_report(
                email_provider=mock_email_provider,
                recipient_email="recipient@example.com"
            )
            
            # Verify that send_daily_report was not called
            tracker.send_daily_report.assert_not_called()
            
            assert result is False

    def test_check_and_send_daily_report_already_sent_today(self, temp_storage_file, mock_email_provider):
        """Test checking and sending a daily report when it's already been sent today."""
        # Set a specific report time
        report_time = time(9, 0)  # 9:00 AM
        
        # Initialize the tracker with the report time
        tracker = ActionTracker(
            storage_path=temp_storage_file,
            report_time=report_time
        )
        
        # Mock the current time to be after the report time
        current_time = time(10, 0)  # 10:00 AM
        current_date = date(2025, 8, 5)
        
        # Mock that a report has already been sent today
        tracker._get_last_report_date = MagicMock(return_value=date(2025, 8, 5))
        
        # Mock datetime.now to return our fixed time
        with patch("stoppls.reporting.action_tracker.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.combine(current_date, current_time)
            
            # Mock send_daily_report
            tracker.send_daily_report = MagicMock()
            
            # Check and send the report
            result = tracker.check_and_send_daily_report(
                email_provider=mock_email_provider,
                recipient_email="recipient@example.com"
            )
            
            # Verify that send_daily_report was not called
            tracker.send_daily_report.assert_not_called()
            
            assert result is False
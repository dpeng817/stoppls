"""Command-line interface for the stoppls application."""

import argparse
import logging
import os
import sys
import time
from datetime import time as datetime_time

from stoppls.config import load_rules
from stoppls.email_monitor import EmailMonitor
from stoppls.email_providers.gmail import GmailProvider
from stoppls.rule_engine import RuleEngine


def setup_logging(verbose=False):
    """Set up logging configuration.

    Args:
        verbose: Whether to enable verbose logging.
    """
    log_level = logging.DEBUG if verbose else logging.INFO

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def run_monitor(args):
    """Run the email monitor.

    Args:
        args: Command-line arguments.
    """
    # Set up logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Log the configuration
    logger.info("Starting stoppls email monitor")
    logger.info(f"Credentials path: {args.credentials}")
    logger.info(f"Token path: {args.token}")
    logger.info(f"Check interval: {args.interval} seconds")
    logger.info(f"Monitored addresses: {args.addresses}")
    if args.rules:
        logger.info(f"Rules configuration: {args.rules}")
    if args.anthropic_key:
        logger.info("Using provided Anthropic API key")
    elif os.environ.get("ANTHROPIC_API_KEY"):
        logger.info("Using Anthropic API key from environment")
    else:
        logger.warning(
            "No Anthropic API key provided. AI rule evaluation will be disabled."
        )
    if args.read_only:
        logger.info("Running in READ-ONLY mode - actions will be logged but not executed")
    if args.enable_reports:
        logger.info(f"Daily reports enabled - will be sent at {args.report_time}")
    else:
        logger.info("Daily reports disabled")

    # Create the email provider
    provider = GmailProvider(credentials_path=args.credentials, token_path=args.token)

    # Parse report time if provided
    report_time = None
    if args.report_time:
        try:
            hour, minute = map(int, args.report_time.split(':'))
            report_time = datetime_time(hour, minute)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid report time format: {e}")
            logger.info("Using default report time (9:00 AM)")

    # Create the email monitor
    monitor = EmailMonitor(
        email_provider=provider,
        check_interval=args.interval,
        monitored_addresses=args.addresses,
        rule_config_path=args.rules,
        anthropic_api_key=args.anthropic_key,
        read_only=args.read_only,
        enable_reports=args.enable_reports,
        report_time=report_time,
    )

    try:
        # Start the monitor
        monitor.start()

        # Keep the main thread alive
        logger.info("Monitor running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Stopping monitor...")

    finally:
        # Stop the monitor
        monitor.stop()
        logger.info("Monitor stopped.")


def dry_run(args):
    """Run rules against a single email in read-only mode.

    Args:
        args: Command-line arguments.
    """
    # Set up logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Log the configuration
    logger.info("Starting stoppls dry-run")
    logger.info(f"Email ID: {args.email_id}")
    logger.info(f"Credentials path: {args.credentials}")
    logger.info(f"Token path: {args.token}")
    if args.rules:
        logger.info(f"Rules configuration: {args.rules}")
    if args.anthropic_key:
        logger.info("Using provided Anthropic API key")
    elif os.environ.get("ANTHROPIC_API_KEY"):
        logger.info("Using Anthropic API key from environment")
    else:
        logger.warning(
            "No Anthropic API key provided. AI rule evaluation will be disabled."
        )
    logger.info("Running in READ-ONLY mode - actions will be logged but not executed")

    # Create the email provider
    provider = GmailProvider(credentials_path=args.credentials, token_path=args.token)

    try:
        # Connect to the email provider
        logger.info("Connecting to email provider...")
        if not provider.connect():
            logger.error("Failed to connect to email provider")
            return

        # Get the email
        logger.info(f"Retrieving email with ID: {args.email_id}")
        email = provider.get_message_by_id(args.email_id)
        
        if not email:
            logger.error(f"Email with ID {args.email_id} not found")
            return
            
        logger.info(f"Found email: {email.subject} from {email.sender}")
        
        # Load rules
        if args.rules:
            rule_config = load_rules(args.rules)
            if not rule_config.rules:
                logger.warning("No rules found in configuration")
                return
                
            logger.info(f"Loaded {len(rule_config.rules)} rules")
            
            # Create rule engine
            rule_engine = RuleEngine(
                rule_config=rule_config,
                anthropic_api_key=args.anthropic_key
            )
            
            # Evaluate email against rules
            logger.info("Evaluating email against rules...")
            rule_results = rule_engine.evaluate_email(email)
            
            if not rule_results:
                logger.info("No rules matched this email")
            else:
                logger.info(f"{len(rule_results)} rules matched this email")
                
                # Log the actions that would be taken
                for result in rule_results:
                    logger.info(f"Rule matched: {result.rule.name}")
                    
                    for action in result.actions:
                        if action.type == "reply":
                            reply_text = action.parameters.get("text", "")
                            logger.info(f"[READ-ONLY] Would reply to message: {email.subject}")
                            logger.info(f"[READ-ONLY] Reply text would be: {reply_text}")
                        elif action.type == "archive":
                            logger.info(f"[READ-ONLY] Would archive message: {email.subject}")
                        elif action.type == "label":
                            label = action.parameters.get("label", "")
                            if label:
                                logger.info(f"[READ-ONLY] Would apply label '{label}' to message: {email.subject}")
                            else:
                                logger.warning("[READ-ONLY] Would attempt to apply label, but no label specified")
                        else:
                            logger.warning(f"[READ-ONLY] Would attempt unknown action type: {action.type}")
        else:
            logger.error("No rules configuration provided")

    except Exception as e:
        logger.error(f"Error in dry-run: {e}")
        
    finally:
        # Disconnect from the email provider
        if provider.is_connected():
            provider.disconnect()
            logger.info("Disconnected from email provider")


def main():
    """Main entry point for the command-line interface."""
    # Create the argument parser
    parser = argparse.ArgumentParser(description="StopPls Email Monitor")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the email monitor")
    run_parser.add_argument(
        "--credentials",
        type=str,
        default=os.path.expanduser("~/.config/stoppls/credentials.json"),
        help="Path to the Gmail API credentials file",
    )
    run_parser.add_argument(
        "--token",
        type=str,
        default=os.path.expanduser("~/.config/stoppls/token.pickle"),
        help="Path to the Gmail API token file",
    )
    run_parser.add_argument(
        "--interval", type=int, default=60, help="Interval between checks in seconds"
    )
    run_parser.add_argument(
        "--addresses",
        type=str,
        nargs="+",
        default=[],
        help="Email addresses to monitor",
    )
    run_parser.add_argument(
        "--rules",
        type=str,
        default=os.path.expanduser("~/.config/stoppls/rules.yaml"),
        help="Path to the rules configuration file",
    )
    run_parser.add_argument(
        "--anthropic-key",
        type=str,
        help="Anthropic API key (defaults to ANTHROPIC_API_KEY environment variable)",
    )
    run_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging"
    )
    run_parser.add_argument(
        "--read-only", 
        action="store_true", 
        help="Run in read-only mode (log actions but don't execute them)"
    )
    run_parser.add_argument(
        "--enable-reports",
        action="store_true",
        help="Enable daily action reports",
    )
    run_parser.add_argument(
        "--report-time",
        type=str,
        default="09:00",
        help="Time of day to send daily reports (24-hour format, e.g., '09:00')",
    )
    run_parser.set_defaults(func=run_monitor)
    
    # Dry-run command
    dry_run_parser = subparsers.add_parser(
        "dry-run", 
        help="Run rules against a single email in read-only mode"
    )
    dry_run_parser.add_argument(
        "email_id",
        type=str,
        help="ID of the email to process",
    )
    dry_run_parser.add_argument(
        "--credentials",
        type=str,
        default=os.path.expanduser("~/.config/stoppls/credentials.json"),
        help="Path to the Gmail API credentials file",
    )
    dry_run_parser.add_argument(
        "--token",
        type=str,
        default=os.path.expanduser("~/.config/stoppls/token.pickle"),
        help="Path to the Gmail API token file",
    )
    dry_run_parser.add_argument(
        "--rules",
        type=str,
        default=os.path.expanduser("~/.config/stoppls/rules.yaml"),
        help="Path to the rules configuration file",
    )
    dry_run_parser.add_argument(
        "--anthropic-key",
        type=str,
        help="Anthropic API key (defaults to ANTHROPIC_API_KEY environment variable)",
    )
    dry_run_parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging"
    )
    dry_run_parser.set_defaults(func=dry_run)

    # Parse the arguments
    args = parser.parse_args()

    # Run the appropriate command
    if hasattr(args, "func"):
        # Create the config directory if it doesn't exist
        if hasattr(args, "credentials"):
            config_dir = os.path.dirname(args.credentials)
            os.makedirs(config_dir, exist_ok=True)

        # Run the command
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

"""
Command-line interface for the stoppls application.
"""
import argparse
import logging
import os
import sys
import time
from pathlib import Path

from stoppls.email_monitor import EmailMonitor
from stoppls.email_providers.gmail import GmailProvider


def setup_logging(verbose=False):
    """
    Set up logging configuration.
    
    Args:
        verbose: Whether to enable verbose logging.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def run_monitor(args):
    """
    Run the email monitor.
    
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
        logger.warning("No Anthropic API key provided. AI rule evaluation will be disabled.")
    
    # Create the email provider
    provider = GmailProvider(
        credentials_path=args.credentials,
        token_path=args.token
    )
    
    # Create the email monitor
    monitor = EmailMonitor(
        email_provider=provider,
        check_interval=args.interval,
        monitored_addresses=args.addresses,
        rule_config_path=args.rules,
        anthropic_api_key=args.anthropic_key
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


def main():
    """
    Main entry point for the command-line interface.
    """
    # Create the argument parser
    parser = argparse.ArgumentParser(description="StopPls Email Monitor")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run the email monitor")
    run_parser.add_argument(
        "--credentials",
        type=str,
        default=os.path.expanduser("~/.config/stoppls/credentials.json"),
        help="Path to the Gmail API credentials file"
    )
    run_parser.add_argument(
        "--token",
        type=str,
        default=os.path.expanduser("~/.config/stoppls/token.pickle"),
        help="Path to the Gmail API token file"
    )
    run_parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Interval between checks in seconds"
    )
    run_parser.add_argument(
        "--addresses",
        type=str,
        nargs="+",
        default=[],
        help="Email addresses to monitor"
    )
    run_parser.add_argument(
        "--rules",
        type=str,
        default=os.path.expanduser("~/.config/stoppls/rules.yaml"),
        help="Path to the rules configuration file"
    )
    run_parser.add_argument(
        "--anthropic-key",
        type=str,
        help="Anthropic API key (defaults to ANTHROPIC_API_KEY environment variable)"
    )
    run_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    run_parser.set_defaults(func=run_monitor)
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Run the appropriate command
    if hasattr(args, "func"):
        # Create the config directory if it doesn't exist
        config_dir = os.path.dirname(args.credentials)
        os.makedirs(config_dir, exist_ok=True)
        
        # Run the command
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
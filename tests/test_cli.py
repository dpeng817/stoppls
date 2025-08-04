"""
Tests for the command-line interface.
"""
import argparse
from unittest.mock import MagicMock, patch

import pytest

from stoppls.cli import main, run_monitor, setup_logging


class TestCLI:
    """Tests for the CLI module."""
    
    @patch('stoppls.cli.argparse.ArgumentParser.parse_args')
    @patch('os.makedirs')
    def test_main_run_command(self, mock_makedirs, mock_parse_args):
        """Test the main function with the run command."""
        # Mock the parsed arguments
        mock_func = MagicMock()
        
        args = argparse.Namespace()
        args.command = 'run'
        args.credentials = '/path/to/credentials.json'
        args.token = '/path/to/token.pickle'
        args.interval = 60
        args.addresses = ['test@example.com']
        args.verbose = False
        args.func = mock_func
        mock_parse_args.return_value = args
        
        # Call main
        main()
        
        # Verify makedirs was called
        mock_makedirs.assert_called_once_with('/path/to', exist_ok=True)
        
        # Verify the mock function was called with the args
        mock_func.assert_called_once_with(args)
    
    @patch('stoppls.cli.argparse.ArgumentParser.parse_args')
    @patch('stoppls.cli.argparse.ArgumentParser.print_help')
    def test_main_no_command(self, mock_print_help, mock_parse_args):
        """Test the main function with no command."""
        # Mock the parsed arguments
        args = argparse.Namespace()
        args.command = None
        mock_parse_args.return_value = args
        
        # Call main
        main()
        
        # Verify print_help was called
        mock_print_help.assert_called_once()
    
    @patch('stoppls.cli.logging.basicConfig')
    def test_setup_logging_verbose(self, mock_basicConfig):
        """Test setup_logging with verbose=True."""
        # Call setup_logging
        setup_logging(verbose=True)
        
        # Verify basicConfig was called with DEBUG level
        mock_basicConfig.assert_called_once()
        args, kwargs = mock_basicConfig.call_args
        assert kwargs['level'] == 10  # logging.DEBUG
    
    @patch('stoppls.cli.logging.basicConfig')
    def test_setup_logging_non_verbose(self, mock_basicConfig):
        """Test setup_logging with verbose=False."""
        # Call setup_logging
        setup_logging(verbose=False)
        
        # Verify basicConfig was called with INFO level
        mock_basicConfig.assert_called_once()
        args, kwargs = mock_basicConfig.call_args
        assert kwargs['level'] == 20  # logging.INFO
    
    @patch('stoppls.cli.GmailProvider')
    @patch('stoppls.cli.EmailMonitor')
    @patch('stoppls.cli.setup_logging')
    @patch('time.sleep', side_effect=KeyboardInterrupt)  # Simulate Ctrl+C
    def test_run_monitor(self, mock_sleep, mock_setup_logging, mock_EmailMonitor, mock_GmailProvider):
        """Test the run_monitor function."""
        # Mock the arguments
        args = argparse.Namespace()
        args.credentials = '/path/to/credentials.json'
        args.token = '/path/to/token.pickle'
        args.interval = 60
        args.addresses = ['test@example.com']
        args.verbose = False
        args.rules = '/path/to/rules.yaml'
        args.anthropic_key = 'test_api_key'
        
        # Mock the provider and monitor
        mock_provider = MagicMock()
        mock_GmailProvider.return_value = mock_provider
        
        mock_monitor = MagicMock()
        mock_EmailMonitor.return_value = mock_monitor
        
        # Call run_monitor
        run_monitor(args)
        
        # Verify setup_logging was called
        mock_setup_logging.assert_called_once_with(False)
        
        # Verify GmailProvider was created with the correct arguments
        mock_GmailProvider.assert_called_once_with(
            credentials_path='/path/to/credentials.json',
            token_path='/path/to/token.pickle'
        )
        
        # Verify EmailMonitor was created with the correct arguments
        mock_EmailMonitor.assert_called_once_with(
            email_provider=mock_provider,
            check_interval=60,
            monitored_addresses=['test@example.com'],
            rule_config_path='/path/to/rules.yaml',
            anthropic_api_key='test_api_key'
        )
        
        # Verify monitor was started and stopped
        mock_monitor.start.assert_called_once()
        mock_monitor.stop.assert_called_once()
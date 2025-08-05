# StopPls Project Context

## Project Overview
StopPls is a Python-based tool that runs as a background process on macOS to monitor incoming emails from specified addresses and uses AI to take automated actions on those emails.

## Key Features
- Email monitoring (Gmail initially, extensible to other providers)
- AI-powered email analysis (Claude initially, extensible to other AI providers)
- Automated actions: replying, archiving, and labeling emails
- Natural language configuration interface (users describe rules in plaintext)
- YAML-based configuration storage
- Read-only mode for testing and debugging (logs actions without executing them)

## Development Environment
- Python 3.12 with uv for virtual environment management
- **IMPORTANT**: All Python commands must be run within the uv virtual environment
- To activate the virtual environment:
  ```bash
  source .venv/bin/activate
  ```
- Always ensure the virtual environment is activated before running any Python commands
- Run tests with: `python -m pytest` (within the activated virtual environment)
- Run the application with: `python -m stoppls.cli` (within the activated virtual environment)

## Development Preferences
- Test-driven development (TDD) approach - never move on until tests pass
- Atomic task breakdown - complete one small feature at a time
- Python as primary language with pytest for testing
- uv for virtual environment management
- Ruff for linting and formatting
- Makefile for common development tasks
- Extensible architecture with clear interfaces

## Code Structure
- Email providers use a base interface with provider-specific implementations
- Rules system uses natural language prompts evaluated by AI
- Email monitor runs as a background process checking for new emails
- Command-line interface for configuration and control

## Project Organization
- src/stoppls/ - Main package code
  - email_providers/ - Email provider implementations
  - cli.py - Command-line interface
  - config.py - Configuration handling
  - email_monitor.py - Email monitoring service
  - rule_engine.py - Rule evaluation engine
- tests/ - Test files matching the structure of src/
- config/ - Configuration files including rules.yaml

## Coding Style
- Google docstring style
- Type hints for function parameters and return values
- Comprehensive error handling
- Thorough test coverage (aim for >85%)
- Clear separation of concerns
- Extensible interfaces for future additions

## Running the Application
- Basic usage: `python -m stoppls.cli run`
- Read-only mode: `python -m stoppls.cli run --read-only`
- For help and all available options: `python -m stoppls.cli run --help`
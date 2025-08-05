# StopPls

A Python-based tool that runs as a background process on macOS to monitor incoming emails from a list of addresses and uses AI to take automated actions on those emails.

## Features

- Email monitoring (Gmail initially, extensible to other providers)
- AI-powered email analysis (Claude initially, extensible to other AI providers)
- Automated actions: replying, archiving, and filtering emails
- Natural language configuration interface (users describe rules in plaintext)
- YAML-based configuration storage
- Read-only mode for testing and debugging (logs actions without executing them)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/stoppls.git
cd stoppls

# Create a virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Install the package in development mode
uv pip install -e .
```

## Usage

### Setting up Gmail API credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials.json file
6. Place the credentials.json file in `~/.config/stoppls/` or specify a custom path with the `--credentials` flag

### Setting up Anthropic API key

1. Sign up for an Anthropic API key at [Anthropic](https://www.anthropic.com/)
2. Set the API key as an environment variable:
   ```bash
   export ANTHROPIC_API_KEY=your_api_key_here
   ```
   Or provide it directly with the `--anthropic-key` flag

### Creating rules

Create a YAML file with your email processing rules. Here's an example:

```yaml
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
```

Save this file to `~/.config/stoppls/rules.yaml` or specify a custom path with the `--rules` flag.

### Running the email monitor

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Run the email monitor with default settings
python -m stoppls.cli run

# Run with custom settings
python -m stoppls.cli run --credentials /path/to/credentials.json --token /path/to/token.pickle --interval 120 --addresses important@example.com updates@example.com --rules /path/to/rules.yaml --anthropic-key your_api_key_here --verbose

# Run in read-only mode (logs actions but doesn't execute them)
python -m stoppls.cli run --read-only
```

### Running as a Background Process

StopPls is designed to run as a background process. For detailed instructions on how to:
- Run StopPls in the background
- Keep it running after terminal sessions close
- Set it up to start automatically
- Monitor and stop the background process

See the [Background Process documentation](docs/background_process.md).

### Command-line options

- `--credentials`: Path to the Gmail API credentials file (default: ~/.config/stoppls/credentials.json)
- `--token`: Path to store the Gmail API token (default: ~/.config/stoppls/token.pickle)
- `--interval`: Interval between checks in seconds (default: 60)
- `--addresses`: Email addresses to monitor (default: none)
- `--rules`: Path to the rules configuration file (default: ~/.config/stoppls/rules.yaml)
- `--anthropic-key`: Anthropic API key (defaults to ANTHROPIC_API_KEY environment variable)
- `--verbose`: Enable verbose logging
- `--read-only`: Run in read-only mode (log actions but don't execute them)

## Rule System

StopPls uses a flexible rule system powered by AI to determine what actions to take on incoming emails.

### Rule Types

Currently, the system supports:

- **NaturalLanguageRule**: Rules defined using natural language prompts that describe when the rule should apply

### Available Actions

- **reply**: Reply to the email with a specified text
- **archive**: Archive the email
- **label**: Apply a label to the email

### How Rules Work

1. When a new email arrives, each enabled rule is evaluated against the email
2. The AI (Claude) analyzes the email content based on the rule's prompt
3. If the AI determines the rule applies, the associated actions are executed
4. Multiple rules can match a single email, and all matching actions will be executed

### Read-Only Mode

StopPls includes a read-only mode that allows you to test your email rules and see what actions would be taken without actually executing them. This is useful for:

- Testing new rules before applying them to real emails
- Debugging rule configurations
- Auditing what actions would be taken on incoming emails

To use read-only mode, add the `--read-only` flag when running the application:

```bash
python -m stoppls.cli run --read-only
```

For more details, see the [Read-Only Mode documentation](docs/read_only_mode.md).

## Development

This project uses test-driven development with pytest.

### Running Tests

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Run all tests
python -m pytest

# Run tests with coverage report
python -m pytest --cov=src/stoppls

# Run specific test files
python -m pytest tests/test_gmail_provider.py
```

## Project Structure

```
stoppls/
├── src/
│   └── stoppls/
│       ├── __init__.py
│       ├── cli.py                # Command-line interface
│       ├── config.py             # Configuration handling
│       ├── email_monitor.py      # Email monitoring service
│       ├── rule_engine.py        # Rule evaluation engine
│       └── email_providers/      # Email provider implementations
│           ├── __init__.py
│           ├── base.py           # Base email provider interface
│           └── gmail.py          # Gmail provider implementation
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_email_monitor.py
│   ├── test_gmail_provider.py
│   ├── test_rule_config.py
│   └── test_rule_engine.py
├── config/
│   └── rules.yaml               # Example rules configuration
├── docs/
│   ├── read_only_mode.md        # Documentation for read-only mode
│   └── background_process.md    # Documentation for running as a background process
├── README.md
├── requirements.txt
├── setup.py
└── pytest.ini
```

## License

[MIT License](LICENSE)
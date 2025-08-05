# Read-Only Mode

## Overview

StopPls includes a read-only mode that allows you to test your email rules and see what actions would be taken without actually executing them. This is useful for:

- Testing new rules before applying them to real emails
- Debugging rule configurations
- Auditing what actions would be taken on incoming emails
- Safely exploring the behavior of the system

## Usage

To run StopPls in read-only mode, use the `--read-only` flag with the `run` command:

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Run in read-only mode
python -m stoppls.cli run --read-only
```

You can combine this with other flags:

```bash
python -m stoppls.cli run --read-only --verbose --interval 30 --addresses important@example.com
```

## How It Works

When running in read-only mode:

1. StopPls connects to your email provider and checks for new emails as usual
2. Rules are evaluated against incoming emails normally
3. Instead of executing actions (reply, archive, label), StopPls logs what actions would have been taken
4. All read-only logs are prefixed with `[READ-ONLY]` for clear identification

## Example Output

When running in read-only mode, you'll see log messages like:

```
2025-08-04 14:32:15 - stoppls.email_monitor - INFO - [READ-ONLY] Would execute actions for rule: Auto-Reply to Newsletters
2025-08-04 14:32:15 - stoppls.email_monitor - INFO - [READ-ONLY] Would reply to message: Weekly Newsletter
2025-08-04 14:32:15 - stoppls.email_monitor - INFO - [READ-ONLY] Would archive message: Weekly Newsletter
2025-08-04 14:32:15 - stoppls.email_monitor - INFO - [READ-ONLY] Would apply label 'Newsletters' to message: Weekly Newsletter
```

## Best Practices

1. **Test New Rules**: Always test new rules in read-only mode first before enabling them in production
2. **Use with Verbose Logging**: Combine with `--verbose` for more detailed information
3. **Regular Audits**: Periodically run in read-only mode to audit what actions would be taken
4. **Troubleshooting**: Use read-only mode to troubleshoot when rules aren't matching as expected

## Limitations

- Read-only mode still connects to your email provider and reads emails
- AI evaluation of rules still occurs, which may incur API costs
- The system still needs the same permissions and credentials as normal operation
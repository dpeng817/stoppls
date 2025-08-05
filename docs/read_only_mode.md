# Read-Only Mode

StopPls can run in read-only mode, which allows you to test your rules without actually performing any actions on your emails. This is useful for testing and debugging your rules before applying them to your actual emails.

## Running in Read-Only Mode

There are two ways to use read-only mode:

### 1. Using the `--read-only` flag with the `run` command

When running the email monitor, you can use the `--read-only` flag to run in read-only mode:

```bash
python -m stoppls.cli run --read-only
```

In this mode, the monitor will:
- Connect to your email provider
- Check for new emails
- Evaluate emails against your rules
- Log the actions that would be taken, but not actually perform them

This is useful for testing your rules against real incoming emails without making any changes.

### 2. Using the `dry-run` command for a single email

If you want to test your rules against a specific email, you can use the `dry-run` command:

```bash
python -m stoppls.cli dry-run <email-id>
```

This command:
- Automatically runs in read-only mode
- Retrieves the specified email by ID
- Evaluates it against your rules
- Logs the actions that would be taken, but doesn't perform them

This is useful for testing your rules against a specific email, especially when debugging or developing new rules.

## Finding Email IDs

To use the `dry-run` command, you need the ID of the email you want to process. In Gmail, you can find the email ID by:

1. Opening the email in Gmail
2. Looking at the URL in your browser
3. The ID is the long alphanumeric string after `/mail/u/0/#inbox/` in the URL

For example, in the URL `https://mail.google.com/mail/u/0/#inbox/FMfcgzGxSHKLMnoPQRST`, the email ID is `FMfcgzGxSHKLMnoPQRST`.

## Example Usage

```bash
# Run the dry-run command on a specific email
python -m stoppls.cli dry-run FMfcgzGxSHKLMnoPQRST

# Run with verbose logging for more details
python -m stoppls.cli dry-run FMfcgzGxSHKLMnoPQRST --verbose

# Specify a custom rules file
python -m stoppls.cli dry-run FMfcgzGxSHKLMnoPQRST --rules /path/to/rules.yaml
```

## Output

The `dry-run` command will output information about:
- The email that was processed (subject, sender, etc.)
- Which rules matched the email
- What actions would be taken for each matching rule

Example output:
```
INFO - Starting stoppls dry-run
INFO - Email ID: FMfcgzGxSHKLMnoPQRST
INFO - Found email: "Weekly Newsletter" from newsletter@example.com
INFO - Loaded 3 rules
INFO - Evaluating email against rules...
INFO - 1 rules matched this email
INFO - Rule matched: Newsletter Rule
INFO - [READ-ONLY] Would apply label 'Newsletters' to message: Weekly Newsletter
INFO - [READ-ONLY] Would archive message: Weekly Newsletter
```

This allows you to verify that your rules are working as expected before applying them to your actual emails.
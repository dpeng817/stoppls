# Running StopPls as a Background Process

This guide explains how to run StopPls as a background process on macOS and how to manage it from the terminal.

## Starting as a Background Process

There are several ways to run StopPls as a background process:

### Method 1: Using `nohup` (Recommended for Terminal Sessions)

The `nohup` command allows the process to continue running even if you close your terminal session:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Start StopPls in the background with nohup
nohup python -m stoppls.cli run > stoppls.log 2>&1 &

# Note the process ID for later use
echo $! > stoppls.pid
```

This will:
1. Start StopPls in the background
2. Redirect both standard output and errors to `stoppls.log`
3. Save the process ID to `stoppls.pid` for easy reference

### Method 2: Using `screen` or `tmux` (For Interactive Sessions)

If you need to occasionally check on the process or interact with it:

#### Using `screen`:

```bash
# Install screen if not already installed
brew install screen

# Start a new screen session
screen -S stoppls

# Inside the screen session, activate the virtual environment and run StopPls
source .venv/bin/activate
python -m stoppls.cli run

# Detach from the screen session (but leave it running) by pressing:
# Ctrl+A followed by D
```

To reattach to the screen session later:
```bash
screen -r stoppls
```

#### Using `tmux`:

```bash
# Install tmux if not already installed
brew install tmux

# Start a new tmux session
tmux new -s stoppls

# Inside the tmux session, activate the virtual environment and run StopPls
source .venv/bin/activate
python -m stoppls.cli run

# Detach from the tmux session (but leave it running) by pressing:
# Ctrl+B followed by D
```

To reattach to the tmux session later:
```bash
tmux attach -t stoppls
```

### Method 3: Using `launchd` (For Automatic Startup on macOS)

For a more permanent solution that starts automatically when you log in:

1. Create a launch agent plist file:

```bash
mkdir -p ~/Library/LaunchAgents
```

Create a file named `com.user.stoppls.plist` in `~/Library/LaunchAgents` with the following content:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.stoppls</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd /path/to/stoppls && source .venv/bin/activate && python -m stoppls.cli run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/path/to/stoppls/stoppls.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/stoppls/stoppls_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>ANTHROPIC_API_KEY</key>
        <string>your_api_key_here</string>
    </dict>
</dict>
</plist>
```

Replace `/path/to/stoppls` with the actual path to your StopPls installation and set your actual API key.

2. Load the launch agent:

```bash
launchctl load ~/Library/LaunchAgents/com.user.stoppls.plist
```

## Stopping the Background Process

### Method 1: Using the Process ID (For `nohup` Method)

If you started StopPls using `nohup` and saved the PID:

```bash
# Read the PID from the file
PID=$(cat stoppls.pid)

# Send a termination signal
kill $PID

# If the process doesn't terminate, force kill it
kill -9 $PID

# Remove the PID file
rm stoppls.pid
```

### Method 2: Finding and Killing the Process

If you don't have the PID saved:

```bash
# Find the StopPls process
ps aux | grep "[p]ython -m stoppls.cli"

# Kill the process using its PID (replace <PID> with the actual process ID)
kill <PID>

# If the process doesn't terminate, force kill it
kill -9 <PID>
```

### Method 3: Stopping a `screen` or `tmux` Session

#### For `screen`:

```bash
# Reattach to the screen session
screen -r stoppls

# Once reattached, stop the process with Ctrl+C
# Then exit the screen session
exit
```

Or kill the screen session directly:
```bash
screen -S stoppls -X quit
```

#### For `tmux`:

```bash
# Reattach to the tmux session
tmux attach -t stoppls

# Once reattached, stop the process with Ctrl+C
# Then exit the tmux session
exit
```

Or kill the tmux session directly:
```bash
tmux kill-session -t stoppls
```

### Method 4: Unloading a Launch Agent

If you used the `launchd` method:

```bash
# Unload the launch agent
launchctl unload ~/Library/LaunchAgents/com.user.stoppls.plist
```

## Checking if StopPls is Running

To check if StopPls is currently running:

```bash
ps aux | grep "[p]ython -m stoppls.cli"
```

If the process is running, you'll see output showing the process details.

## Viewing Logs

If you redirected output to a log file:

```bash
# View the entire log file
cat stoppls.log

# View the last 50 lines
tail -n 50 stoppls.log

# Follow the log in real-time (press Ctrl+C to exit)
tail -f stoppls.log
```

## Running in Read-Only Mode

Remember that you can run StopPls in read-only mode to test your configuration without actually taking actions on emails:

```bash
# Run in read-only mode as a background process
nohup python -m stoppls.cli run --read-only > stoppls_readonly.log 2>&1 &
```

This is useful for testing your rules and seeing what actions would be taken without actually executing them.
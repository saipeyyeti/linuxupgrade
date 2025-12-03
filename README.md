# Ubuntu VM Update Agent with LangChain & LLM

## Overview

An intelligent Python-based system update agent that leverages LangChain and Large Language Models (LLMs) to automate Ubuntu VM updates with smart health checks and automatic rollback capabilities.

## Features

### 🛡️ Safe Update Process
- **Pre-Update Snapshots**: Automatically creates system snapshots using Timeshift before any updates
- **Fallback Protection**: If Timeshift is unavailable, creates package list backups
- **Atomic Operations**: All-or-nothing update approach with automatic rollback on failure

### 🤖 AI-Powered Health Analysis
- **Intelligent Monitoring**: Uses Claude AI to analyze system health post-update
- **Comprehensive Checks**: Monitors services, packages, network, disk usage, and memory
- **Smart Decision Making**: LLM evaluates whether the system is truly healthy beyond simple pass/fail checks

### 🔄 Automatic Rollback
- **Failure Detection**: Automatically detects update failures and system issues
- **Instant Recovery**: Rolls back to pre-update state using Timeshift snapshots
- **Multiple Strategies**: Falls back to package restoration if Timeshift unavailable

### 📊 Complete Logging
- **Detailed Audit Trail**: Logs every action to both console and log file (`/var/log/llm_update_agent.log`)
- **Timestamped Entries**: All operations tracked with precise timestamps
- **Debugging Support**: Full update history available for troubleshooting

## System Requirements

### Operating System
- Ubuntu 18.04 LTS or later
- Debian-based distributions

### Software Dependencies
- Python 3.8 or higher
- Root/sudo access
- Internet connectivity

### Python Packages
```bash
pip install langchain langchain-anthropic
```

### Recommended Tools
```bash
sudo apt install timeshift
```

## Installation

### Step 1: Install System Dependencies

```bash
# Update package lists
sudo apt update

# Install Timeshift (highly recommended)
sudo apt install timeshift -y

# Install Python pip if not available
sudo apt install python3-pip -y
```

### Step 2: Install Python Dependencies

```bash
# Install required Python packages
pip install langchain langchain-anthropic
```

### Step 3: Download the Script

Save the script as `ubuntu_update_agent.py` and make it executable:

```bash
chmod +x ubuntu_update_agent.py
```

### Step 4: Configure API Key

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY='your-anthropic-api-key-here'

# Or add to your .bashrc for persistence
echo 'export ANTHROPIC_API_KEY="your-anthropic-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

## Usage

### Basic Usage

```bash
# Run the update agent with sudo
sudo -E python3 ubuntu_update_agent.py
```

**Note**: The `-E` flag preserves environment variables (including your API key) when running with sudo.

### Running as a Cron Job

To schedule automatic updates:

```bash
# Edit root's crontab
sudo crontab -e

# Add weekly updates (Sunday at 2 AM)
0 2 * * 0 ANTHROPIC_API_KEY='your-key' /usr/bin/python3 /path/to/ubuntu_update_agent.py

# Or monthly updates (1st day of month at 3 AM)
0 3 1 * * ANTHROPIC_API_KEY='your-key' /usr/bin/python3 /path/to/ubuntu_update_agent.py
```

### Configuration Options

Edit these variables in the script to customize behavior:

```python
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
SNAPSHOT_NAME = f"pre_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
LOG_FILE = "/var/log/llm_update_agent.log"
```

## How It Works

### Workflow

1. **Initialization**
   - Verifies root access and API key
   - Initializes LangChain with Claude Sonnet 4

2. **Create Snapshot**
   - Attempts to create Timeshift snapshot
   - Falls back to package list backup if Timeshift unavailable
   - Logs snapshot creation status

3. **Collect Pre-Update State**
   - Gathers system information (OS version, kernel, disk usage, memory)
   - Records running and failed services
   - Checks for broken packages
   - Tests network connectivity

4. **Perform Updates**
   - Updates package lists (`apt update`)
   - Upgrades packages (`apt upgrade -y`)
   - Performs full upgrade (`apt full-upgrade -y`)
   - Cleans up unused packages (`apt autoremove`, `apt autoclean`)

5. **System Stabilization**
   - Waits 30 seconds for services to restart
   - Allows system to reach steady state

6. **AI Health Analysis**
   - Collects post-update system information
   - Sends data to Claude AI for intelligent analysis
   - LLM evaluates overall system health
   - Provides detailed recommendations

7. **Decision & Action**
   - **If Healthy**: Completes successfully, logs success
   - **If Unhealthy**: Initiates automatic rollback, restores previous state

## Health Check Criteria

The system evaluates multiple indicators:

### Service Health
- ✅ All critical services running
- ❌ Any failed services trigger investigation

### Package Integrity
- ✅ No broken packages
- ❌ Broken dependencies trigger rollback

### Network Connectivity
- ✅ Can reach external networks
- ❌ Network failures indicate problems

### Resource Usage
- ✅ Adequate disk space and memory
- ❌ Resource exhaustion warnings

### LLM Analysis
- Uses Claude to identify subtle issues
- Detects patterns that simple scripts might miss
- Provides context-aware recommendations

## Rollback Process

### Timeshift Rollback (Preferred)

```bash
# Automatically restores complete system state
sudo timeshift --restore --snapshot-device /dev/sda1 --scripted
```

### Fallback Package Restoration

If Timeshift is unavailable:
```bash
# Reinstalls packages from pre-update list
sudo apt install --reinstall $(cat /tmp/package_list_*.txt | awk '{print $1}')
```

## Logs and Monitoring

### Log File Location
```bash
/var/log/llm_update_agent.log
```

### View Logs
```bash
# View entire log
sudo cat /var/log/llm_update_agent.log

# View last 50 lines
sudo tail -n 50 /var/log/llm_update_agent.log

# Follow log in real-time
sudo tail -f /var/log/llm_update_agent.log
```

### Log Format
```
[2024-12-03 14:30:15] Creating system snapshot...
[2024-12-03 14:30:20] Snapshot created successfully
[2024-12-03 14:30:21] Starting system update process...
```

## Troubleshooting

### Common Issues

#### API Key Not Found
```
Error: Please set ANTHROPIC_API_KEY environment variable
```
**Solution**: Export your API key before running
```bash
export ANTHROPIC_API_KEY='your-key'
sudo -E python3 ubuntu_update_agent.py
```

#### Permission Denied
```
Error: This script must be run as root or with sudo
```
**Solution**: Run with sudo
```bash
sudo -E python3 ubuntu_update_agent.py
```

#### Timeshift Not Available
```
Warning: Timeshift not available, creating package list backup
```
**Solution**: Install Timeshift for better snapshots
```bash
sudo apt install timeshift
```

#### Network Timeout
```
Command timed out after 600 seconds
```
**Solution**: Check internet connection, may need to increase timeout in script

## Best Practices

### Before Running

1. **Test in Non-Production First**: Always test on development/staging VMs
2. **Backup Important Data**: Create manual backups of critical data
3. **Check Disk Space**: Ensure adequate space (at least 5GB free)
4. **Review Logs**: Check previous update logs for patterns

### Scheduling Updates

1. **Choose Low-Traffic Times**: Schedule during maintenance windows
2. **Avoid Business Hours**: Run updates during off-peak hours
3. **Monitor First Run**: Watch the first scheduled run carefully
4. **Set Up Alerts**: Configure monitoring for update failures

### Post-Update

1. **Verify Applications**: Test critical applications after updates
2. **Check Logs**: Review update logs for warnings
3. **Monitor Performance**: Watch system metrics for anomalies
4. **Document Issues**: Keep notes on any problems encountered

## Security Considerations

- **API Key Protection**: Never commit API keys to version control
- **Log Sensitive Data**: Review logs before sharing (may contain system info)
- **Snapshot Storage**: Ensure snapshots are stored securely
- **Network Security**: Agent requires internet access for LLM API calls

## Exit Codes

- `0`: Update completed successfully
- `1`: Update failed or rolled back

## Support and Contributing

For issues, improvements, or questions:
- Review the log file for detailed error messages
- Check system resources and connectivity
- Verify API key is valid and has sufficient credits
- Test individual components (snapshot, update, health check) separately

## License

This script is provided as-is for educational and operational purposes.

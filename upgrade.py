#!/usr/bin/env python3
"""
Ubuntu VM Update Agent with LangChain and LLM
Performs system updates with intelligent health checks and automatic rollback
"""

import os
import subprocess
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")
SNAPSHOT_NAME = f"pre_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
LOG_FILE = "/var/log/llm_update_agent.log"

class SystemUpdateAgent:
    def __init__(self):
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=ANTHROPIC_API_KEY,
            temperature=0
        )
        self.snapshot_created = False
        self.update_log = []
        
    def log(self, message: str):
        """Log messages to both console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.update_log.append(log_entry)
        try:
            with open(LOG_FILE, "a") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")

    def run_command(self, command: str, check: bool = True) -> Tuple[int, str, str]:
        """Execute shell command and return exit code, stdout, stderr"""
        self.log(f"Executing: {command}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            self.log("Command timed out after 600 seconds")
            return -1, "", "Command timeout"
        except Exception as e:
            self.log(f"Command execution error: {e}")
            return -1, "", str(e)

    def create_snapshot(self) -> bool:
        """Create system snapshot using timeshift or similar"""
        self.log("Creating system snapshot...")
        
        # Check if timeshift is available
        code, _, _ = self.run_command("which timeshift")
        if code == 0:
            code, out, err = self.run_command(
                f"sudo timeshift --create --comments '{SNAPSHOT_NAME}' --scripted"
            )
            if code == 0:
                self.snapshot_created = True
                self.log("Snapshot created successfully")
                return True
            else:
                self.log(f"Timeshift snapshot failed: {err}")
        
        # Fallback: Create package list backup
        self.log("Timeshift not available, creating package list backup")
        code, out, err = self.run_command(
            f"dpkg --get-selections > /tmp/package_list_{SNAPSHOT_NAME}.txt"
        )
        if code == 0:
            self.snapshot_created = True
            self.log("Package list backup created")
            return True
        
        self.log("WARNING: Could not create snapshot or backup")
        return False

    def update_system(self) -> bool:
        """Perform system updates"""
        self.log("Starting system update process...")
        
        # Update package lists
        self.log("Updating package lists...")
        code, out, err = self.run_command("sudo apt update")
        if code != 0:
            self.log(f"Failed to update package lists: {err}")
            return False
        
        # Upgrade packages
        self.log("Upgrading packages...")
        code, out, err = self.run_command(
            "sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y"
        )
        if code != 0:
            self.log(f"Package upgrade failed: {err}")
            return False
        
        # Full upgrade (handles dependencies)
        self.log("Performing full upgrade...")
        code, out, err = self.run_command(
            "sudo DEBIAN_FRONTEND=noninteractive apt full-upgrade -y"
        )
        if code != 0:
            self.log(f"Full upgrade failed: {err}")
            return False
        
        # Clean up
        self.log("Cleaning up...")
        self.run_command("sudo apt autoremove -y")
        self.run_command("sudo apt autoclean")
        
        self.log("System update completed")
        return True

    def collect_system_info(self) -> Dict:
        """Collect system health information"""
        info = {}
        
        # OS version
        code, out, _ = self.run_command("lsb_release -d")
        info['os_version'] = out.strip()
        
        # Kernel version
        code, out, _ = self.run_command("uname -r")
        info['kernel'] = out.strip()
        
        # Disk usage
        code, out, _ = self.run_command("df -h / | tail -1")
        info['disk_usage'] = out.strip()
        
        # Memory usage
        code, out, _ = self.run_command("free -h | grep Mem")
        info['memory'] = out.strip()
        
        # Running services
        code, out, _ = self.run_command("systemctl list-units --type=service --state=running --no-pager")
        info['running_services'] = len(out.strip().split('\n')) - 2
        
        # Failed services
        code, out, _ = self.run_command("systemctl list-units --type=service --state=failed --no-pager")
        failed = out.strip().split('\n')
        info['failed_services'] = [line.split()[0] for line in failed if line.strip() and not line.startswith('●')]
        
        # Check for broken packages
        code, out, _ = self.run_command("dpkg -l | grep -E '^.[^i]'")
        info['broken_packages'] = out.strip() if out.strip() else "None"
        
        # Network connectivity
        code, _, _ = self.run_command("ping -c 2 8.8.8.8")
        info['network'] = "OK" if code == 0 else "FAILED"
        
        return info

    def perform_health_checks(self) -> Tuple[bool, str]:
        """Run health checks and use LLM to analyze results"""
        self.log("Performing system health checks...")
        
        system_info = self.collect_system_info()
        
        # Create prompt for LLM analysis
        analysis_prompt = f"""
Analyze the following Ubuntu system health information after a system update.
Determine if the system is healthy and functioning properly.

System Information:
{json.dumps(system_info, indent=2)}

Update Log:
{chr(10).join(self.update_log[-20:])}

Provide your analysis in the following format:
1. HEALTH_STATUS: HEALTHY or UNHEALTHY
2. ISSUES: List any critical issues found (or "None" if healthy)
3. RECOMMENDATION: What action should be taken

Be strict in your assessment. Any failed services, broken packages, or network issues should be flagged.
"""
        
        try:
            response = self.llm.invoke(analysis_prompt)
            analysis = response.content
            self.log(f"LLM Health Analysis:\n{analysis}")
            
            # Parse LLM response
            is_healthy = "HEALTH_STATUS: HEALTHY" in analysis.upper()
            
            return is_healthy, analysis
            
        except Exception as e:
            self.log(f"Error during LLM analysis: {e}")
            # Fallback to basic checks
            is_healthy = (
                len(system_info.get('failed_services', [])) == 0 and
                system_info.get('network') == "OK" and
                "None" in system_info.get('broken_packages', '')
            )
            return is_healthy, "Basic health check completed (LLM unavailable)"

    def rollback_system(self) -> bool:
        """Rollback system to previous state"""
        self.log("INITIATING ROLLBACK...")
        
        if not self.snapshot_created:
            self.log("ERROR: No snapshot available for rollback")
            return False
        
        # Try timeshift restore
        code, _, _ = self.run_command("which timeshift")
        if code == 0:
            self.log("Restoring from timeshift snapshot...")
            code, out, err = self.run_command(
                "sudo timeshift --restore --snapshot-device /dev/sda1 --scripted"
            )
            if code == 0:
                self.log("Timeshift rollback successful")
                return True
            else:
                self.log(f"Timeshift rollback failed: {err}")
        
        # Fallback: Downgrade packages (basic)
        self.log("Attempting package downgrade...")
        code, out, err = self.run_command(
            "sudo apt install --reinstall $(cat /tmp/package_list_*.txt | awk '{print $1}')"
        )
        
        self.log("Rollback process completed")
        return code == 0

    def run_update_workflow(self) -> bool:
        """Main workflow for system update"""
        self.log("=" * 60)
        self.log("Ubuntu VM Update Agent Starting")
        self.log("=" * 60)
        
        # Step 1: Create snapshot
        if not self.create_snapshot():
            self.log("WARNING: Proceeding without snapshot (risky)")
        
        # Step 2: Collect pre-update system state
        self.log("Collecting pre-update system state...")
        pre_update_info = self.collect_system_info()
        self.log(f"Pre-update info: {json.dumps(pre_update_info, indent=2)}")
        
        # Step 3: Perform updates
        update_success = self.update_system()
        
        if not update_success:
            self.log("ERROR: Update process failed")
            if self.snapshot_created:
                self.rollback_system()
            return False
        
        # Step 4: Wait for system to stabilize
        self.log("Waiting 30 seconds for system to stabilize...")
        time.sleep(30)
        
        # Step 5: Health checks
        is_healthy, analysis = self.perform_health_checks()
        
        if not is_healthy:
            self.log("ERROR: System health checks failed")
            self.log("Analysis indicates problems, initiating rollback...")
            self.rollback_system()
            return False
        
        # Step 6: Success
        self.log("=" * 60)
        self.log("UPDATE SUCCESSFUL - System is healthy")
        self.log("=" * 60)
        return True


def main():
    """Main entry point"""
    # Check for root/sudo
    if os.geteuid() != 0:
        print("This script must be run as root or with sudo")
        print("Usage: sudo python3 ubuntu_update_agent.py")
        return
    
    # Check for API key
    if ANTHROPIC_API_KEY == "your-api-key-here":
        print("Please set ANTHROPIC_API_KEY environment variable")
        print("export ANTHROPIC_API_KEY='your-key-here'")
        return
    
    agent = SystemUpdateAgent()
    
    try:
        success = agent.run_update_workflow()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        agent.log("\nUpdate process interrupted by user")
        exit(1)
    except Exception as e:
        agent.log(f"Unexpected error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
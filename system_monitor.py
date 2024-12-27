#!/usr/bin/env python3
"""
System Monitoring Script with Flexible Output Options by Li, Dec 2024
"""

import psutil
import time
import logging
from logging.handlers import RotatingFileHandler
import smtplib
import yaml
import os
import argparse
from email.mime.text import MIMEText
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler
from rich import print as rprint

@dataclass
class ResourceUsage:
    """Data class to store resource usage information"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    timestamp: datetime

class SystemMonitor:
    """Enhanced system monitoring with flexible output options"""
    
    def __init__(self, config_path: str = 'config.yaml', log_to_file: bool = False):
        """Initialize the SystemMonitor"""
        self.config = self._load_config(config_path)
        self.thresholds = self.config['thresholds']
        self.email_config = self.config['email']
        self.interval = self.config.get('interval', 300)
        self.alert_cooldown = self.config.get('alert_cooldown', 3600)
        self.last_alert_time = {
            'cpu': datetime.min,
            'memory': datetime.min,
            'disk': datetime.min
        }
        
        # Initialize console output
        self.console = Console()
        
        # Setup logging
        self._setup_logging(log_to_file)

    def _setup_logging(self, log_to_file: bool):
        """Configure logging with both console and file handlers"""
        # Clear any existing handlers
        logging.getLogger().handlers = []
        
        # Create console handler with rich formatting
        console_handler = RichHandler(
            console=self.console,
            show_path=False,
            enable_link_path=False
        )
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        console_handler.setLevel(logging.INFO)
        
        handlers = [console_handler]
        
        # Add file handler if requested
        if log_to_file:
            file_handler = RotatingFileHandler(
                'system_monitor.log',
                maxBytes=10485760,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            ))
            file_handler.setLevel(logging.INFO)
            handlers.append(file_handler)
        
        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            handlers=handlers
        )

    def format_usage_report(self, usage: ResourceUsage) -> str:
        """Format resource usage as a string report"""
        return f"""
System Resource Usage Report - {usage.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
{'='* 60}
CPU Usage    : {usage.cpu_percent:>5.1f}% (Threshold: {self.thresholds['cpu']}%) - {'[red]ALERT[/red]' if usage.cpu_percent > self.thresholds['cpu'] else '[green]OK[/green]'}
Memory Usage : {usage.memory_percent:>5.1f}% (Threshold: {self.thresholds['memory']}%) - {'[red]ALERT[/red]' if usage.memory_percent > self.thresholds['memory'] else '[green]OK[/green]'}
Disk Usage   : {usage.disk_percent:>5.1f}% (Threshold: {self.thresholds['disk']}%) - {'[red]ALERT[/red]' if usage.disk_percent > self.thresholds['disk'] else '[green]OK[/green]'}
{'='* 60}"""

    def get_resource_usage(self) -> ResourceUsage:
        """Get current resource usage"""
        try:
            return ResourceUsage(
                cpu_percent=psutil.cpu_percent(interval=1),
                memory_percent=psutil.virtual_memory().percent,
                disk_percent=psutil.disk_usage('/').percent,
                timestamp=datetime.now()
            )
        except Exception as e:
            logging.error(f"Failed to get resource usage: {e}")
            raise

    def check_resources(self) -> None:
        """Check system resources and display/log results"""
        try:
            usage = self.get_resource_usage()
            
            # Format and display the usage report
            report = self.format_usage_report(usage)
            self.console.print(report)
            
            # Check thresholds and send alerts
            current_time = datetime.now()
            
            if usage.cpu_percent > self.thresholds['cpu']:
                if (current_time - self.last_alert_time['cpu']).total_seconds() > self.alert_cooldown:
                    self.send_alert("High CPU Usage Alert", 
                                  f"CPU usage is {usage.cpu_percent:.1f}%")
                    self.last_alert_time['cpu'] = current_time
            
            if usage.memory_percent > self.thresholds['memory']:
                if (current_time - self.last_alert_time['memory']).total_seconds() > self.alert_cooldown:
                    self.send_alert("High Memory Usage Alert", 
                                  f"Memory usage is {usage.memory_percent:.1f}%")
                    self.last_alert_time['memory'] = current_time
            
            if usage.disk_percent > self.thresholds['disk']:
                if (current_time - self.last_alert_time['disk']).total_seconds() > self.alert_cooldown:
                    self.send_alert("High Disk Usage Alert", 
                                  f"Disk usage is {usage.disk_percent:.1f}%")
                    self.last_alert_time['disk'] = current_time
                    
        except Exception as e:
            logging.error(f"Error in check_resources: {e}")
            
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            return {
                'thresholds': {'cpu': 80, 'memory': 80, 'disk': 80},
                'email': {
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'sender': 'your-email@gmail.com',
                    'password': 'your-app-password',
                    'recipient': 'admin@example.com'
                }
            }

    def send_alert(self, subject: str, message: str) -> None:
        """Send email alert"""
        try:
            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = self.email_config['sender']
            msg['To'] = self.email_config['recipient']

            with smtplib.SMTP(self.email_config['smtp_server'], 
                            self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['sender'], 
                           self.email_config['password'])
                server.send_message(msg)
                
            logging.info(f"Alert sent: {subject}")
        except Exception as e:
            logging.error(f"Failed to send alert: {e}")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='System Resource Monitor')
    parser.add_argument('--config', type=str, default='config.yaml',
                      help='Path to configuration file')
    parser.add_argument('--interval', type=int,
                      help='Monitoring interval in seconds (overrides config file)')
    parser.add_argument('--log-file', action='store_true',
                      help='Enable logging to file')
    parser.add_argument('--output', type=str,
                      help='Redirect output to specified file')
    return parser.parse_args()

def main():
    """Main function to run the monitoring system"""
    args = parse_args()
    
    try:
        # Initialize monitor with logging preferences
        monitor = SystemMonitor(args.config, args.log_file)
        
        # Override interval if specified
        if args.interval:
            monitor.interval = args.interval
            
        logging.info(f"Starting system monitoring (interval: {monitor.interval}s)")
        
        # Redirect output if specified
        if args.output:
            original_stdout = monitor.console.file
            output_file = open(args.output, 'a')
            monitor.console.file = output_file
        
        try:
            while True:
                monitor.check_resources()
                time.sleep(monitor.interval)
        finally:
            # Restore original stdout and close file if needed
            if args.output:
                monitor.console.file = original_stdout
                output_file.close()
                
    except KeyboardInterrupt:
        logging.info("Monitoring stopped by user")
    except Exception as e:
        logging.error(f"Monitoring stopped due to error: {e}")

if __name__ == "__main__":
    main()

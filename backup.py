#!/usr/bin/env python3

import os
import sys
import getpass
import json
import zipfile
import datetime
from pathlib import Path
import subprocess
import shutil
import paramiko
import schedule
import time
from datetime import datetime as dt


class VPSBackupTool:
    def __init__(self):
        self.config_file = "env.py"
        self.config = {}

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    content = f.read()
                    config_dict = {}
                    for line in content.split('\n'):
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"\'')
                            config_dict[key] = value
                    self.config = config_dict
                    return True
            except Exception as e:
                print(f"Error loading config: {e}")
        return False

    def save_config(self):
        with open(self.config_file, 'w') as f:
            f.write("# VPS Backup Configuration\n")
            for key, value in self.config.items():
                f.write(f'{key} = "{value}"\n')

    def setup_configuration(self):
        print("Setting up VPS backup configuration...")

        ip_address = self.get_user_input("Enter VPS IP address: ")
        username = self.get_user_input("Enter VPS username: ")
        password = self.get_user_input("Enter VPS password: ", hide_input=True)

        while True:
            try:
                backup_frequency = int(self.get_user_input("Backup every how many days? "))
                if backup_frequency > 0:
                    break
                else:
                    print("Please enter a positive number.")
            except ValueError:
                print("Please enter a valid number.")

        while True:
            try:
                retention_count = int(self.get_user_input("How many backup files to keep? "))
                if retention_count > 0:
                    break
                else:
                    print("Please enter a positive number.")
            except ValueError:
                print("Please enter a valid number.")

        self.config = {
            'IP_ADDRESS': ip_address,
            'USERNAME': username,
            'PASSWORD': password,
            'BACKUP_FREQUENCY_DAYS': str(backup_frequency),
            'RETENTION_COUNT': str(retention_count)
        }

        self.save_config()
        print("Configuration saved successfully!")

    def get_user_input(self, prompt, hide_input=False):
        if hide_input:
            return getpass.getpass(prompt)
        else:
            return input(prompt)

    def display_existing_config(self):
        print("\nExisting configuration:")
        print(f"VPS IP Address: {self.config.get('IP_ADDRESS', 'Not set')}")
        print(f"Username: {self.config.get('USERNAME', 'Not set')}")
        print(f"Backup Frequency: {self.config.get('BACKUP_FREQUENCY_DAYS', 'Not set')} day(s)")
        print(f"Retention Count: {self.config.get('RETENTION_COUNT', 'Not set')} file(s)")

    def get_backup_filename(self):
        now = datetime.datetime.now()
        timestamp = now.strftime("%d/%m/%Y").replace("/", "_")
        return f"{self.config['USERNAME']}_{timestamp}.zip"

    def create_remote_backup(self):
        print("Creating backup of remote VPS...")

        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh_client.connect(
                hostname=self.config['IP_ADDRESS'],
                username=self.config['USERNAME'],
                password=self.config['PASSWORD']
            )

            script_content = """#!/bin/bash
cd /
zip -r /tmp/vps_backup_temp.zip . -x "dev/*" "proc/*" "sys/*" "tmp/*" "run/*" "mnt/*" "media/*" "lost+found/*" "boot/*" "var/log/*" ".cache/*" "home/*" "root/*" "etc/ssh/*" "etc/shadow*" "etc/passwd*"
"""

            stdin, stdout, stderr = ssh_client.exec_command(f'bash -c "{script_content}"')

            exit_status = stdout.channel.recv_exit_status()

            if exit_status != 0:
                error_output = stderr.read().decode()
                print(f"Error creating remote backup: {error_output}")
                ssh_client.close()
                return False

            ssh_client.close()
            return True

        except Exception as e:
            print(f"Exception during remote backup creation: {e}")
            return False

    def transfer_backup(self):
        print("Transferring backup file...")

        remote_file = "/tmp/vps_backup_temp.zip"
        local_file = self.get_backup_filename()

        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh_client.connect(
                hostname=self.config['IP_ADDRESS'],
                username=self.config['USERNAME'],
                password=self.config['PASSWORD']
            )

            sftp_client = ssh_client.open_sftp()

            sftp_client.get(remote_file, local_file)

            sftp_client.close()
            ssh_client.close()

            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(
                hostname=self.config['IP_ADDRESS'],
                username=self.config['USERNAME'],
                password=self.config['PASSWORD']
            )

            stdin, stdout, stderr = ssh_client.exec_command('rm /tmp/vps_backup_temp.zip')
            ssh_client.close()

            print(f"Backup transferred successfully: {local_file}")
            return True

        except Exception as e:
            print(f"Exception during backup transfer: {e}")
            return False

    def cleanup_old_backups(self):
        print("Cleaning up old backups...")

        retention_count = int(self.config.get('RETENTION_COUNT', 5))

        backup_pattern = f"{self.config['USERNAME']}_*.zip"
        backup_files = []

        for file in os.listdir('.'):
            if file.startswith(f"{self.config['USERNAME']}_") and file.endswith('.zip'):
                backup_files.append(file)

        backup_files.sort(key=lambda x: os.path.getctime(x))

        files_to_remove = len(backup_files) - retention_count
        if files_to_remove > 0:
            for i in range(files_to_remove):
                file_to_remove = backup_files[i]
                print(f"Removing old backup: {file_to_remove}")
                os.remove(file_to_remove)
        else:
            print(f"Number of backups ({len(backup_files)}) is within retention limit ({retention_count})")

    def run_backup(self):
        print("Starting VPS backup process...")

        if not self.create_remote_backup():
            print("Failed to create remote backup. Exiting.")
            return False

        if not self.transfer_backup():
            print("Failed to transfer backup. Exiting.")
            return False

        self.cleanup_old_backups()
        print("Backup process completed successfully!")
        return True

    def schedule_backups(self):
        frequency_days = int(self.config.get('BACKUP_FREQUENCY_DAYS', 1))

        print(f"Scheduling backups every {frequency_days} day(s)...")

        schedule.every(frequency_days).days.do(self.run_backup)

        print("Backup scheduler started. Press Ctrl+C to stop.")

        try:
            while True:
                schedule.run_pending()
                time.sleep(3600)
        except KeyboardInterrupt:
            print("\nScheduler stopped by user.")

    def run(self):
        print("VPS Backup Tool")
        print("===============")

        if self.load_config():
            print("\nConfiguration already exists:")
            self.display_existing_config()

            while True:
                choice = input("\nChoose an option:\n1. Use existing configuration\n2. Enter new configuration\n3. Run scheduled backups\nEnter choice (1, 2, or 3): ")

                if choice == '1':
                    print("Using existing configuration...")
                    break
                elif choice == '2':
                    self.setup_configuration()
                    break
                elif choice == '3':
                    print("Starting scheduled backups...")
                    self.schedule_backups()
                    return
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
        else:
            self.setup_configuration()

        while True:
            run_choice = input("\nRun backup now? (y/n): ").lower()
            if run_choice in ['y', 'yes']:
                self.run_backup()
                break
            elif run_choice in ['n', 'no']:
                schedule_choice = input("Schedule automatic backups? (y/n): ").lower()
                if schedule_choice in ['y', 'yes']:
                    self.schedule_backups()
                break
            else:
                print("Please enter 'y' or 'n'")


def main():
    tool = VPSBackupTool()
    tool.run()


if __name__ == "__main__":
    main()
# VPS Backup Tool

This tool automates the backup process of a remote VPS to your local machine. It connects to the remote VPS via SSH, creates a zip archive of its contents, transfers the archive to your local machine, and manages backup retention.

## Features

- Secure SSH connection using username and password
- Automatic creation of zip archives of remote VPS contents
- Transfer of backup files to local machine
- Configurable backup frequency (every X days)
- Automatic cleanup of old backup files based on retention policy
- Scheduling of automatic backups
- Secure storage of credentials in env.py file

## Requirements

- Python 3.6+
- paramiko library
- schedule library

## Installation

1. Clone or download this repository
2. Install required dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

## Usage

Run the backup tool:
```bash
python3 vps_backup_tool.py
```

On first run, you'll be prompted to enter:
1. VPS IP address
2. Username
3. Password (input will be hidden)
4. Backup frequency (every X days)
5. Number of backup files to keep

On subsequent runs, you can choose to use existing configuration or enter new configuration.

## Backup File Naming

Backup files are named in the format: `{username}_{day}_{month}_{year}.zip`
Example: `phims_20_2_2026.zip`

## Security

- Passwords are stored in plain text in the env.py file for convenience
- Use appropriate file permissions to protect the env.py file
- Consider using SSH keys instead of passwords for production environments

## Scheduling

The tool supports automatic scheduling of backups based on the configured frequency. When you choose to schedule backups, the tool will run in the background and perform backups according to your specified schedule.

## Important Notes

- The backup process excludes system directories like /dev, /proc, /sys, etc.
- The tool connects to the remote VPS as root to backup all files. Make sure you have appropriate permissions.
- Ensure sufficient disk space on the local machine to store backups.
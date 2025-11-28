#!/usr/bin/env python3
import sys
import os
sys.path.append('.')

from windsurf_account_manager.config_path_manager import ConfigPathManager
from windsurf_account_manager.config_snapshot import ConfigSnapshot
from windsurf_account_manager.auto_backup import AutoBackupManager
from windsurf_account_manager.storage import load_accounts

# 加载账号
accounts = load_accounts()
if not accounts:
    print("No accounts found")
    sys.exit(1)

# 初始化管理器
manager = ConfigPathManager()
snapshot = ConfigSnapshot()
backup_manager = AutoBackupManager(manager, snapshot)

# 获取第一个账号
account = accounts[0]
print(f"Testing with account: {account.email}")

# 列出备份
backups = backup_manager.list_backups(account.id)
print(f"Found {len(backups)} backups for this account")

if not backups:
    print("No backups found")
    sys.exit(1)

# 获取最新备份
latest_backup = backups[0]
backup_name = latest_backup.get("backup_name")
print(f"Latest backup: {backup_name}")

# 显示备份中的文件
print("Files in backup:")
for file_name in latest_backup.get("files", []):
    print(f"  - {file_name}")

# 测试恢复功能
print("\nTesting restore functionality...")
result = backup_manager.restore_backup(account.id, backup_name)
print(f"Restore result: {result}")
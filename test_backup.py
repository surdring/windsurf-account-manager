#!/usr/bin/env python3
import sys
sys.path.append('.')

from windsurf_account_manager.config_path_manager import ConfigPathManager
from windsurf_account_manager.config_snapshot import ConfigSnapshot
from windsurf_account_manager.auto_backup import AutoBackupManager
from windsurf_account_manager.storage import load_accounts

# 加载账号
accounts = load_accounts()
print(f"Found accounts: {len(accounts)}")

# 初始化管理器
manager = ConfigPathManager()
snapshot = ConfigSnapshot()
backup_manager = AutoBackupManager(manager, snapshot)

# 显示配置信息
print(f"Config files: {snapshot.config_files}")
print(f"Active path: {manager.get_active_path()}")

if accounts:
    print(f"First account: {accounts[0].email}")
    
    # 尝试创建备份
    result = backup_manager.create_backup(accounts[0].id, accounts[0].email)
    print(f"Backup result: {result}")
    
    # 列出备份
    backups = backup_manager.list_backups(accounts[0].id)
    print(f"Backups for {accounts[0].email}: {len(backups)}")
    if backups:
        print(f"Latest backup: {backups[0].get('backup_name', 'N/A')}")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append('.')

from windsurf_account_manager.config_path_manager import ConfigPathManager
from windsurf_account_manager.config_snapshot import ConfigSnapshot
from windsurf_account_manager.auto_backup import AutoBackupManager
from windsurf_account_manager.storage import AccountStorage

def main():
    # 创建管理器
    config_path_manager = ConfigPathManager()
    snapshot_manager = ConfigSnapshot()
    backup_manager = AutoBackupManager(config_path_manager, snapshot_manager)
    
    # 检查活动路径
    active_path = config_path_manager.get_active_path()
    print(f"当前活动路径: {active_path}")
    
    # 加载账号
    storage = AccountStorage()
    accounts = storage.load_accounts()
    print(f"找到 {len(accounts)} 个账号")
    
    if accounts:
        # 为第一个账号创建备份
        account = accounts[0]
        print(f"为账号 {account.email} 创建备份...")
        success = backup_manager.create_backup(account.id, account.email)
        print(f"备份结果: {success}")
        
        # 列出备份
        backups = backup_manager.list_backups(account.id)
        print(f"账号 {account.email} 有 {len(backups)} 个备份")
        for backup in backups:
            print(f"  - {backup.get('created_at', '')}: {backup.get('path', '')}")
    
    # 检查自动备份配置
    print(f"自动备份启用: {backup_manager.enabled}")
    print(f"备份间隔: {backup_manager.backup_interval_hours} 小时")
    print(f"最大备份数: {backup_manager.max_backups}")
    print(f"上次备份时间: {backup_manager.last_backup_time}")

if __name__ == "__main__":
    main()
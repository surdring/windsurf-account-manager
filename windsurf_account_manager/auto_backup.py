"""
自动备份和恢复功能模块
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from .config_path_manager import ConfigPathManager
from .config_snapshot import ConfigSnapshot
from .storage import load_accounts, save_accounts
from .models import Account


class AutoBackupManager:
    """自动备份管理器"""
    
    def __init__(
        self,
        config_path_manager: ConfigPathManager,
        snapshot_manager: ConfigSnapshot,
        backup_dir: Optional[Path] = None,
        enabled: bool = True,
        backup_interval_hours: int = 24,
        max_backups: int = 7
    ) -> None:
        """
        初始化自动备份管理器
        
        Args:
            config_path_manager: 配置路径管理器
            snapshot_manager: 快照管理器
            backup_dir: 备份目录
            enabled: 是否启用自动备份
            backup_interval_hours: 备份间隔（小时）
            max_backups: 最大备份数量
        """
        self.config_path_manager = config_path_manager
        self.snapshot_manager = snapshot_manager
        self.enabled = enabled
        self.backup_interval_hours = backup_interval_hours
        self.max_backups = max_backups
        
        # 设置备份目录
        if backup_dir is None:
            backup_dir = Path(__file__).resolve().parent.parent / "data" / "auto_backups"
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置文件路径
        self.config_file = self.backup_dir / "auto_backup_config.json"
        
        # 后台线程
        self.backup_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # 加载配置
        self.load_config()
        
        # 如果启用，启动自动备份
        if self.enabled:
            self.start_auto_backup()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        if self.config_file.exists():
            try:
                with self.config_file.open("r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.enabled = config.get("enabled", True)
                    self.backup_interval_hours = config.get("backup_interval_hours", 24)
                    self.max_backups = config.get("max_backups", 7)
                    self.last_backup_time = config.get("last_backup_time")
                    return config
            except Exception as e:
                print(f"加载自动备份配置失败: {e}")
                self.last_backup_time = None
                return {}
        else:
            self.last_backup_time = None
            self.save_config()
            return {}
    
    def save_config(self) -> None:
        """保存配置"""
        try:
            config = {
                "enabled": self.enabled,
                "backup_interval_hours": self.backup_interval_hours,
                "max_backups": self.max_backups,
                "last_backup_time": self.last_backup_time
            }
            with self.config_file.open("w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存自动备份配置失败: {e}")
    
    def is_time_to_backup(self) -> bool:
        """检查是否到了备份时间"""
        if not self.last_backup_time:
            return True
        
        try:
            last_backup = datetime.fromisoformat(self.last_backup_time)
            now = datetime.now()
            return now - last_backup >= timedelta(hours=self.backup_interval_hours)
        except Exception:
            return True
    
    def create_backup(self, account_id: str, account_email: str) -> bool:
        """为指定账号创建备份"""
        try:
            # 获取活动配置路径
            active_path = self.config_path_manager.get_active_path()
            if not active_path:
                print("没有活动配置路径，无法创建备份")
                return False
            
            # 确保active_path是Path对象
            if not isinstance(active_path, Path):
                active_path = Path(active_path)
            
            # 创建备份目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{account_email}_{timestamp}"
            backup_path = self.backup_dir / account_id / backup_name
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # 复制配置文件
            for config_file in self.snapshot_manager.config_files:
                src_file = active_path / config_file
                if src_file.exists():
                    # 对于嵌套路径，需要确保目标目录存在
                    dst_file = backup_path / config_file
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
            
            # 创建备份元数据
            metadata = {
                "account_id": account_id,
                "account_email": account_email,
                "created_at": datetime.now().isoformat(),
                "config_path": str(active_path),
                "os_type": self.snapshot_manager.get_os_type(),
                "files": [f for f in self.snapshot_manager.config_files if (active_path / f).exists()]
            }
            
            metadata_file = backup_path / "metadata.json"
            with metadata_file.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # 清理旧备份
            self.cleanup_old_backups(account_id)
            
            # 更新最后备份时间
            self.last_backup_time = datetime.now().isoformat()
            self.save_config()
            
            print(f"已为账号 {account_email} 创建自动备份: {backup_name}")
            return True
        except Exception as e:
            print(f"创建自动备份失败: {e}")
            return False
    
    def restore_backup(self, account_id: str, backup_name: str) -> bool:
        """恢复指定账号的备份"""
        try:
            # 获取活动配置路径
            active_path = self.config_path_manager.get_active_path()
            if not active_path:
                print("没有活动配置路径，无法恢复备份")
                return False
            
            # 确保active_path是Path对象
            if not isinstance(active_path, Path):
                active_path = Path(active_path)
            
            # 备份路径
            backup_path = self.backup_dir / account_id / backup_name
            if not backup_path.exists():
                print(f"备份不存在: {backup_name}")
                return False
            
            # 先备份当前配置
            current_backup_dir = active_path.parent / f"Windsurf_auto_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if active_path.exists():
                shutil.copytree(active_path, current_backup_dir)
                print(f"当前配置已备份到: {current_backup_dir}")
            
            # 确保目标目录存在
            active_path.mkdir(parents=True, exist_ok=True)
            
            # 恢复配置文件
            for config_file in self.snapshot_manager.config_files:
                src_file = backup_path / config_file
                if src_file.exists():
                    dst_file = active_path / config_file
                    # 对于嵌套路径，需要确保目标目录存在
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
            
            print(f"已恢复账号 {account_id} 的备份: {backup_name}")
            return True
        except Exception as e:
            print(f"恢复备份失败: {e}")
            return False
    
    def list_backups(self, account_id: str) -> List[Dict[str, Any]]:
        """列出指定账号的所有备份"""
        backups = []
        account_backup_dir = self.backup_dir / account_id
        
        if not account_backup_dir.exists():
            return backups
        
        for backup_dir in account_backup_dir.iterdir():
            if not backup_dir.is_dir():
                continue
                
            metadata_file = backup_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with metadata_file.open("r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    # 添加备份名称和路径
                    metadata["backup_name"] = backup_dir.name
                    metadata["path"] = str(backup_dir)
                    metadata["id"] = f"{account_id}_{backup_dir.name}"  # 用于UI中的唯一标识
                    backups.append(metadata)
                except Exception as e:
                    print(f"读取备份元数据失败: {e}")
        
        # 按创建时间排序（最新的在前）
        backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return backups
    
    def list_all_backups(self) -> List[Dict[str, Any]]:
        """列出所有账号的所有备份"""
        all_backups = []
        
        # 获取所有账号
        try:
            accounts = load_accounts()
            account_ids = [account.id for account in accounts]
        except Exception as e:
            print(f"获取账号列表失败: {e}")
            return all_backups
        
        # 获取每个账号的备份
        for account_id in account_ids:
            backups = self.list_backups(account_id)
            all_backups.extend(backups)
        
        # 按创建时间排序（最新的在前）
        all_backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return all_backups
    
    def cleanup_old_backups(self, account_id: str) -> None:
        """清理旧备份，保留最新的max_backups个"""
        backups = self.list_backups(account_id)
        
        if len(backups) <= self.max_backups:
            return
        
        # 删除多余的备份
        for backup in backups[self.max_backups:]:
            backup_name = backup.get("backup_name")
            if backup_name:
                backup_path = self.backup_dir / account_id / backup_name
                try:
                    shutil.rmtree(backup_path)
                    print(f"已删除旧备份: {backup_name}")
                except Exception as e:
                    print(f"删除旧备份失败: {e}")
    
    def backup_all_accounts(self) -> None:
        """为所有有快照的账号创建备份"""
        try:
            accounts = load_accounts()
            for account in accounts:
                if account.has_snapshot:
                    self.create_backup(account.id, account.email)
        except Exception as e:
            print(f"为所有账号创建备份失败: {e}")
    
    def backup_worker(self) -> None:
        """后台备份工作线程"""
        while not self.stop_event.is_set():
            try:
                if self.enabled and self.is_time_to_backup():
                    self.backup_all_accounts()
                
                # 每小时检查一次
                for _ in range(60):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"自动备份工作线程错误: {e}")
    
    def start_auto_backup(self) -> None:
        """启动自动备份"""
        if self.backup_thread and self.backup_thread.is_alive():
            return
        
        self.stop_event.clear()
        self.backup_thread = threading.Thread(target=self.backup_worker, daemon=True)
        self.backup_thread.start()
        print("自动备份已启动")
    
    def stop_auto_backup(self) -> None:
        """停止自动备份"""
        if not self.backup_thread or not self.backup_thread.is_alive():
            return
        
        self.stop_event.set()
        self.backup_thread.join(timeout=5)
        print("自动备份已停止")
    
    def set_enabled(self, enabled: bool) -> None:
        """设置是否启用自动备份"""
        self.enabled = enabled
        self.save_config()
        
        if enabled:
            self.start_auto_backup()
        else:
            self.stop_auto_backup()
    
    def set_backup_interval(self, hours: int) -> None:
        """设置备份间隔（小时）"""
        self.backup_interval_hours = max(1, hours)  # 最小1小时
        self.save_config()
    
    def set_max_backups(self, max_backups: int) -> None:
        """设置最大备份数量"""
        self.max_backups = max(1, max_backups)  # 最少1个备份
        self.save_config()
    
    def delete_backup(self, account_id: str, backup_name: str) -> bool:
        """删除指定备份"""
        backup_path = self.backup_dir / account_id / backup_name
        if not backup_path.exists():
            return True
        
        try:
            shutil.rmtree(backup_path)
            print(f"已删除备份: {backup_name}")
            return True
        except Exception as e:
            print(f"删除备份失败: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {
            "enabled": self.enabled,
            "backup_interval_hours": self.backup_interval_hours,
            "max_backups": self.max_backups,
            "last_backup_time": self.last_backup_time
        }
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .models import Account, AppSettings


class ConfigSnapshot:
    """配置快照管理类"""
    
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent.parent / "data"
        
        self.base_dir = base_dir
        self.snapshots_dir = self.base_dir / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        # 默认的Windsurf配置路径（需要根据实际情况调整）
        self.default_windsurf_paths = {
            "windows": [
                Path(os.path.expandvars("%APPDATA%")) / "Windsurf",
                Path(os.path.expandvars("%APPDATA%")) / "Codeium",
                Path(os.path.expandvars("%APPDATA%")) / "Cursor"
            ],
            "linux": [
                Path.home() / ".config" / "Windsurf",
                Path.home() / ".config" / "codeium",
                Path.home() / ".config" / "Cursor"
            ],
            "macos": [
                Path.home() / "Library" / "Application Support" / "Windsurf",
                Path.home() / "Library" / "Application Support" / "codeium",
                Path.home() / "Library" / "Application Support" / "Cursor"
            ]
        }
        
        # 需要备份的配置文件
        self.config_files = [
            "settings.json",
            "mcp_config.json",
            "rules.json",
            "keybindings.json",
            "extensions.json",
            "Preferences",
            "User/globalStorage/storage.json",
            "User/globalStorage/state.vscdb"
        ]
    
    def get_os_type(self) -> str:
        """获取操作系统类型"""
        import platform
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        elif system == "windows":
            return "windows"
        else:
            return "linux"  # 默认使用Linux路径
    
    def detect_windsurf_config_path(self) -> Optional[Path]:
        """检测Windsurf配置路径"""
        os_type = self.get_os_type()
        possible_paths = self.default_windsurf_paths.get(os_type, [])
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                # 检查是否包含Windsurf相关的配置文件
                for config_file in self.config_files:
                    if (path / config_file).exists():
                        return path
        
        return None
    
    def validate_path(self, path: Path) -> Dict[str, Any]:
        """验证路径是否为有效的Windsurf配置目录"""
        result = {
            "exists": path.exists(),
            "valid": False,
            "has_settings": False,
            "has_extensions": False,
            "has_keybindings": False,
            "missing_files": []
        }
        
        if not result["exists"]:
            return result
        
        # 检查配置文件
        for file_name in self.config_files:
            file_path = path / file_name
            if file_path.exists():
                result["valid"] = True
                if file_name == "settings.json":
                    result["has_settings"] = True
                elif file_name == "extensions.json":
                    result["has_extensions"] = True
                elif file_name == "keybindings.json":
                    result["has_keybindings"] = True
            else:
                result["missing_files"].append(file_name)
        
        # 如果至少有一个配置文件存在，认为是有效路径
        return result
    
    def get_default_config_path(self) -> Optional[Path]:
        """获取默认的Windsurf配置路径"""
        return self.detect_windsurf_config_path()
    
    def get_account_snapshot_dir(self, account_id: str) -> Path:
        """获取账号快照目录"""
        return self.snapshots_dir / account_id
    
    def create_snapshot(self, account_id: str, config_path: Optional[Path] = None, snapshot_name: Optional[str] = None) -> bool:
        """为指定账号创建配置快照"""
        try:
            # 如果没有提供配置路径，使用默认路径
            if config_path is None:
                config_path = self.detect_windsurf_config_path()
                if not config_path:
                    return False
            
            # 验证路径
            if not config_path.exists():
                print(f"Windsurf配置路径不存在: {config_path}")
                return False
            
            snapshot_dir = self.get_account_snapshot_dir(account_id)
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            
            # 备份配置文件
            for config_file in self.config_files:
                src_file = config_path / config_file
                if src_file.exists():
                    dst_file = snapshot_dir / config_file
                    shutil.copy2(src_file, dst_file)
            
            # 创建快照元数据
            metadata = {
                "account_id": account_id,
                "created_at": datetime.now().isoformat(),
                "config_path": str(config_path),
                "os_type": self.get_os_type(),
                "files": [f for f in self.config_files if (config_path / f).exists()],
                "custom_path": config_path is not None
            }
            
            # 如果提供了快照名称，添加到元数据
            if snapshot_name:
                metadata["name"] = snapshot_name
            
            metadata_file = snapshot_dir / "metadata.json"
            with metadata_file.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"创建快照失败: {e}")
            return False
    
    def restore_snapshot(self, account_id: str, config_path: Optional[Path] = None) -> bool:
        """恢复指定账号的配置快照"""
        try:
            # 如果没有提供配置路径，使用默认路径
            if config_path is None:
                config_path = self.detect_windsurf_config_path()
                if not config_path:
                    print("无法确定Windsurf配置路径")
                    return False
            
            # 验证路径
            if not config_path.exists():
                # 如果路径不存在，尝试创建
                config_path.mkdir(parents=True, exist_ok=True)
            
            snapshot_dir = self.get_account_snapshot_dir(account_id)
            if not snapshot_dir.exists():
                print(f"账号 {account_id} 的快照不存在")
                return False
            
            # 先备份当前配置
            backup_dir = config_path.parent / f"Windsurf_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if config_path.exists():
                shutil.copytree(config_path, backup_dir)
                print(f"当前配置已备份到: {backup_dir}")
            
            # 确保目标目录存在
            config_path.mkdir(parents=True, exist_ok=True)
            
            # 恢复配置文件
            for config_file in self.config_files:
                src_file = snapshot_dir / config_file
                if src_file.exists():
                    dst_file = config_path / config_file
                    shutil.copy2(src_file, dst_file)
            
            return True
        except Exception as e:
            print(f"恢复快照失败: {e}")
            return False
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """列出所有快照"""
        snapshots = []
        
        if not self.snapshots_dir.exists():
            return snapshots
        
        for account_dir in self.snapshots_dir.iterdir():
            if not account_dir.is_dir():
                continue
                
            metadata_file = account_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with metadata_file.open("r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    snapshots.append(metadata)
                except Exception as e:
                    print(f"读取快照元数据失败: {e}")
        
        return snapshots
    
    def delete_snapshot(self, account_id: str) -> bool:
        """删除指定账号的快照"""
        snapshot_dir = self.get_account_snapshot_dir(account_id)
        if not snapshot_dir.exists():
            return True
        
        try:
            shutil.rmtree(snapshot_dir)
            return True
        except Exception as e:
            print(f"删除快照失败: {e}")
            return False
    
    def get_snapshot(self, account_id: str) -> Optional[Dict[str, Any]]:
        """获取账号的快照信息"""
        snapshot_dir = self.get_account_snapshot_dir(account_id)
        if not snapshot_dir.exists():
            return None
        
        metadata_file = snapshot_dir / "metadata.json"
        if not metadata_file.exists():
            return None
        
        try:
            with metadata_file.open("r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # 添加快照名称（如果有）
            if "name" not in metadata:
                metadata["name"] = f"快照_{metadata.get('created_at', '')[:10]}"
            
            return metadata
        except Exception as e:
            print(f"读取快照信息失败: {e}")
            return None
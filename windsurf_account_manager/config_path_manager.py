"""
配置路径管理模块
用于管理Windsurf的配置路径，支持多路径配置和自动检测
"""
from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from .models import AppSettings


class ConfigPathManager:
    """配置路径管理类"""
    
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent.parent / "data"
        
        self.base_dir = base_dir
        self.config_file = self.base_dir / "config_paths.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 默认的Windsurf配置路径
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
        
        # 加载配置
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_file.exists():
            return {
                "paths": [],
                "active_path": None,
                "auto_detect": True
            }
        
        try:
            with self.config_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置路径失败: {e}")
            return {
                "paths": [],
                "active_path": None,
                "auto_detect": True
            }
    
    def _save_config(self) -> bool:
        """保存配置文件"""
        try:
            with self.config_file.open("w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置路径失败: {e}")
            return False
    
    def get_os_type(self) -> str:
        """获取操作系统类型"""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        elif system == "windows":
            return "windows"
        else:
            return "linux"  # 默认使用Linux路径
    
    def detect_windsurf_paths(self) -> List[Path]:
        """检测所有可能的Windsurf配置路径"""
        os_type = self.get_os_type()
        possible_paths = self.default_windsurf_paths.get(os_type, [])
        detected_paths = []
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                # 检查是否包含Windsurf相关的配置文件
                has_config = False
                for config_file in self.config_files:
                    if (path / config_file).exists():
                        has_config = True
                        break
                
                if has_config:
                    detected_paths.append(path)
        
        return detected_paths
    
    def get_paths(self) -> List[Dict[str, Any]]:
        """获取所有配置路径"""
        return self.config.get("paths", [])
    
    def add_path(self, path: Path, name: Optional[str] = None) -> bool:
        """添加配置路径"""
        if not path.exists() or not path.is_dir():
            return False
        
        path_str = str(path.resolve())
        
        # 检查路径是否已存在
        for existing in self.config.get("paths", []):
            if existing.get("path") == path_str:
                return False
        
        # 如果没有提供名称，使用路径的最后一部分
        if name is None:
            name = path.name
        
        # 检查路径是否包含Windsurf配置文件
        has_config = False
        for config_file in self.config_files:
            if (path / config_file).exists():
                has_config = True
                break
        
        path_info = {
            "id": len(self.config.get("paths", [])) + 1,
            "name": name,
            "path": path_str,
            "has_config": has_config,
            "os_type": self.get_os_type()
        }
        
        self.config.setdefault("paths", []).append(path_info)
        return self._save_config()
    
    def remove_path(self, path_id: int) -> bool:
        """删除配置路径"""
        paths = self.config.get("paths", [])
        for i, path_info in enumerate(paths):
            if path_info.get("id") == path_id:
                paths.pop(i)
                # 如果删除的是当前活动路径，清除活动路径
                if self.config.get("active_path") == path_id:
                    self.config["active_path"] = None
                return self._save_config()
        return False
    
    def set_active_path(self, path_or_id: Union[str, Path, int]) -> bool:
        """设置活动配置路径
        
        Args:
            path_or_id: 路径字符串、Path对象或路径ID
            
        Returns:
            是否设置成功
        """
        # 如果是Path对象，转换为字符串
        if isinstance(path_or_id, Path):
            path_str = str(path_or_id)
            # 查找匹配的路径ID
            for path_info in self.get_paths():
                if path_info.get("path", "") == path_str:
                    self.config["active_path"] = path_info.get("id")
                    return self._save_config()
            return False
        elif isinstance(path_or_id, str):
            # 假设是路径字符串
            path_str = path_or_id
            for path_info in self.get_paths():
                if path_info.get("path", "") == path_str:
                    self.config["active_path"] = path_info.get("id")
                    return self._save_config()
            return False
        else:
            # 假设是路径ID
            path_id = path_or_id
            paths = self.config.get("paths", [])
            for path_info in paths:
                if path_info.get("id") == path_id:
                    self.config["active_path"] = path_id
                    return self._save_config()
            return False
    
    def get_active_path(self) -> Optional[Path]:
        """获取当前活动配置路径"""
        active_path_id = self.config.get("active_path")
        if active_path_id is None:
            return None
        
        for path_info in self.get_paths():
            if path_info.get("id") == active_path_id:
                return Path(path_info.get("path", ""))
        
        return None
    
    def get_active_path_obj(self) -> Optional[Path]:
        """获取当前活动配置路径的Path对象"""
        active_path = self.get_active_path()
        if active_path is None:
            return None
        return Path(active_path.get("path", ""))
    
    def auto_detect_and_add(self) -> int:
        """自动检测并添加配置路径"""
        detected_paths = self.detect_windsurf_paths()
        added_count = 0
        
        for path in detected_paths:
            if self.add_path(path):
                added_count += 1
        
        # 如果没有活动路径，设置第一个为活动路径
        if self.config.get("active_path") is None and self.config.get("paths"):
            self.config["active_path"] = self.config["paths"][0]["id"]
            self._save_config()
        
        return added_count
    
    def get_config_files(self, path: Path) -> List[Dict[str, Any]]:
        """获取指定路径下的配置文件列表"""
        if not path.exists() or not path.is_dir():
            return []
        
        files = []
        for config_file in self.config_files:
            file_path = path / config_file
            if file_path.exists():
                stat = file_path.stat()
                files.append({
                    "name": config_file,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                })
        
        return files
    
    def validate_path(self, path: Union[str, Path]) -> Dict[str, Any]:
        """验证路径是否为有效的Windsurf配置目录
        
        Args:
            path: 要验证的路径
            
        Returns:
            包含验证结果的字典，包含以下键:
            - valid: 是否为有效路径
            - path: 路径字符串
            - errors: 错误信息列表
            - warnings: 警告信息列表
            - settings_exists: settings.json是否存在
            - extensions_exists: extensions.json是否存在
            - keybindings_exists: keybindings.json是否存在
        """
        result = {
            "valid": False,
            "path": str(path),
            "errors": [],
            "warnings": [],
            "settings_exists": False,
            "extensions_exists": False,
            "keybindings_exists": False
        }
        
        # 转换为Path对象
        if not isinstance(path, Path):
            path = Path(path)
        
        # 检查路径是否存在
        if not path.exists():
            result["errors"].append(f"路径不存在: {path}")
            return result
        
        # 检查是否为目录
        if not path.is_dir():
            result["errors"].append(f"路径不是目录: {path}")
            return result
        
        # 检查关键配置文件
        settings_file = path / "settings.json"
        extensions_file = path / "extensions.json"
        keybindings_file = path / "keybindings.json"
        
        result["settings_exists"] = settings_file.exists()
        result["extensions_exists"] = extensions_file.exists()
        result["keybindings_exists"] = keybindings_file.exists()
        
        # 检查settings.json是否存在
        if not settings_file.exists():
            result["errors"].append(f"未找到settings.json文件: {settings_file}")
        else:
            # 尝试解析settings.json
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                result["errors"].append(f"settings.json格式错误: {e}")
            except Exception as e:
                result["errors"].append(f"读取settings.json失败: {e}")
        
        # 检查extensions.json是否存在
        if not extensions_file.exists():
            result["warnings"].append(f"未找到extensions.json文件: {extensions_file}")
        else:
            # 尝试解析extensions.json
            try:
                with open(extensions_file, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                result["warnings"].append(f"extensions.json格式错误: {e}")
            except Exception as e:
                result["warnings"].append(f"读取extensions.json失败: {e}")
        
        # 检查keybindings.json是否存在
        if not keybindings_file.exists():
            result["warnings"].append(f"未找到keybindings.json文件: {keybindings_file}")
        else:
            # 尝试解析keybindings.json
            try:
                with open(keybindings_file, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                result["warnings"].append(f"keybindings.json格式错误: {e}")
            except Exception as e:
                result["warnings"].append(f"读取keybindings.json失败: {e}")
        
        # 如果没有错误，则认为路径有效
        result["valid"] = len(result["errors"]) == 0
        
        return result
    
    def get_default_path(self) -> Optional[Path]:
        """获取默认的Windsurf配置路径"""
        os_type = self.get_os_type()
        possible_paths = self.default_windsurf_paths.get(os_type, [])
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                return path
        
        return None
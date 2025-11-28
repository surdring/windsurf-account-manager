#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append('.')

from windsurf_account_manager.config_path_manager import ConfigPathManager

def main():
    # 创建配置路径管理器
    config_path_manager = ConfigPathManager()
    
    # 检测并添加配置路径
    print("检测Windsurf配置路径...")
    detected_paths = config_path_manager.detect_windsurf_paths()
    print(f"检测到 {len(detected_paths)} 个路径:")
    for path in detected_paths:
        print(f"  - {path}")
    
    # 添加检测到的路径
    added_count = config_path_manager.auto_detect_and_add()
    print(f"自动添加了 {added_count} 个配置路径")
    
    # 获取所有路径
    paths = config_path_manager.get_paths()
    print(f"共有 {len(paths)} 个配置路径:")
    for path_info in paths:
        print(f"  - ID: {path_info.get('id')}, 名称: {path_info.get('name')}, 路径: {path_info.get('path')}, 有配置: {path_info.get('has_config')}")
    
    # 获取活动路径
    active_path = config_path_manager.get_active_path()
    print(f"当前活动路径: {active_path}")
    
    # 如果没有活动路径，尝试手动添加一个默认路径
    if not active_path:
        print("没有活动路径，尝试添加默认路径...")
        default_path_str = os.path.expandvars("%APPDATA%") + "\\Windsurf"
        if os.path.exists(default_path_str):
            from pathlib import Path
            default_path = Path(default_path_str)
            success = config_path_manager.add_path(default_path, "默认Windsurf配置")
            if success:
                print(f"成功添加默认路径: {default_path}")
                # 设置为活动路径
                paths = config_path_manager.get_paths()
                if paths:
                    config_path_manager.set_active_path(paths[0]["id"])
                    active_path = config_path_manager.get_active_path()
                    print(f"设置活动路径为: {active_path}")
            else:
                print(f"添加默认路径失败: {default_path}")
        else:
            print(f"默认路径不存在: {default_path_str}")

if __name__ == "__main__":
    main()
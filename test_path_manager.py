#!/usr/bin/env python3
"""
测试脚本，用于验证配置路径管理器功能
"""
import sys
import os
from pathlib import Path

# 添加项目路径到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from windsurf_account_manager.config_path_manager import ConfigPathManager
from windsurf_account_manager.storage import load_accounts

def test_path_manager():
    """测试配置路径管理器"""
    print("测试配置路径管理器...")
    
    # 创建路径管理器
    path_manager = ConfigPathManager()
    
    # 测试添加路径
    test_paths = [
        Path("C:/Users/test/AppData/Roaming/Code/User"),
        Path("C:/Users/test2/AppData/Roaming/Code/User"),
        Path("D:/config/windsurf")
    ]
    
    for path in test_paths:
        result = path_manager.add_path(path)
        print(f"添加路径 {path}: {'成功' if result else '失败'}")
    
    # 测试获取所有路径
    all_paths = path_manager.get_paths()
    print(f"\n所有路径: {all_paths}")
    
    # 测试设置活动路径
    if all_paths:
        active_path = path_manager.set_active_path(all_paths[0])
        print(f"\n设置活动路径: {active_path}")
        
        # 测试获取活动路径
        current_active = path_manager.get_active_path()
        print(f"当前活动路径: {current_active}")
    
    # 测试路径验证
    if all_paths:
        validation_result = path_manager.validate_path(all_paths[0])
        print(f"\n路径验证结果: {validation_result}")
    
    print("\n配置路径管理器测试完成!")

def test_accounts():
    """测试账号数据"""
    print("\n测试账号数据...")
    
    try:
        accounts = load_accounts()
        print(f"加载了 {len(accounts)} 个账号")
        
        for account in accounts:
            print(f"账号: {account.email}, 有快照: {account.has_snapshot}")
    except Exception as e:
        print(f"加载账号失败: {e}")
    
    print("账号数据测试完成!")

if __name__ == "__main__":
    test_path_manager()
    test_accounts()
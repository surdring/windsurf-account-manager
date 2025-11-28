#!/usr/bin/env python3
"""
简单测试脚本，用于验证UI应用程序是否可以正常启动
"""
import sys
import os
from pathlib import Path

# 添加项目路径到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试所有模块是否可以正常导入"""
    print("测试模块导入...")
    
    try:
        from windsurf_account_manager import config_path_manager
        print("✓ config_path_manager 模块导入成功")
    except Exception as e:
        print(f"✗ config_path_manager 模块导入失败: {e}")
        return False
    
    try:
        from windsurf_account_manager import ui_main
        print("✓ ui_main 模块导入成功")
    except Exception as e:
        print(f"✗ ui_main 模块导入失败: {e}")
        return False
    
    try:
        from windsurf_account_manager import config_snapshot
        print("✓ config_snapshot 模块导入成功")
    except Exception as e:
        print(f"✗ config_snapshot 模块导入失败: {e}")
        return False
    
    try:
        from windsurf_account_manager import storage
        print("✓ storage 模块导入成功")
    except Exception as e:
        print(f"✗ storage 模块导入失败: {e}")
        return False
    
    try:
        from windsurf_account_manager import models
        print("✓ models 模块导入成功")
    except Exception as e:
        print(f"✗ models 模块导入失败: {e}")
        return False
    
    try:
        from windsurf_account_manager import api_client
        print("✓ api_client 模块导入成功")
    except Exception as e:
        print(f"✗ api_client 模块导入失败: {e}")
        return False
    
    try:
        from windsurf_account_manager import mcp_rules
        print("✓ mcp_rules 模块导入成功")
    except Exception as e:
        print(f"✗ mcp_rules 模块导入失败: {e}")
        return False
    
    return True

def test_path_manager():
    """测试配置路径管理器"""
    print("\n测试配置路径管理器...")
    
    try:
        from windsurf_account_manager.config_path_manager import ConfigPathManager
        
        # 创建配置路径管理器
        path_manager = ConfigPathManager()
        print("✓ 配置路径管理器创建成功")
        
        # 测试获取默认路径
        default_path = path_manager.get_default_path()
        print(f"✓ 默认路径: {default_path}")
        
        # 测试获取活动路径
        active_path = path_manager.get_active_path()
        print(f"✓ 活动路径: {active_path}")
        
        # 测试获取所有路径
        paths = path_manager.get_paths()
        print(f"✓ 配置路径数量: {len(paths)}")
        
        return True
    except Exception as e:
        print(f"✗ 配置路径管理器测试失败: {e}")
        return False

def test_snapshot_manager():
    """测试配置快照管理器"""
    print("\n测试配置快照管理器...")
    
    try:
        from windsurf_account_manager.config_snapshot import ConfigSnapshot
        
        # 创建配置快照管理器
        snapshot_manager = ConfigSnapshot()
        print("✓ 配置快照管理器创建成功")
        
        return True
    except Exception as e:
        print(f"✗ 配置快照管理器测试失败: {e}")
        return False

def test_storage():
    """测试存储模块"""
    print("\n测试存储模块...")
    
    try:
        from windsurf_account_manager.storage import load_accounts
        
        # 加载账号
        accounts = load_accounts()
        print(f"✓ 加载了 {len(accounts)} 个账号")
        
        return True
    except Exception as e:
        print(f"✗ 存储模块测试失败: {e}")
        return False

if __name__ == "__main__":
    print("开始测试Windsurf Account Manager...\n")
    
    success = True
    
    # 测试模块导入
    if not test_imports():
        success = False
    
    # 测试配置路径管理器
    if not test_path_manager():
        success = False
    
    # 测试配置快照管理器
    if not test_snapshot_manager():
        success = False
    
    # 测试存储模块
    if not test_storage():
        success = False
    
    if success:
        print("\n✓ 所有测试通过！应用程序应该可以正常运行。")
    else:
        print("\n✗ 部分测试失败，请检查错误信息。")
        sys.exit(1)
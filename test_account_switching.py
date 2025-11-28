#!/usr/bin/env python3
"""
测试切号功能的完整流程
"""
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from windsurf_account_manager.config_path_manager import ConfigPathManager
from windsurf_account_manager.snapshot_manager import SnapshotManager
from windsurf_account_manager.storage import load_accounts, save_accounts
from windsurf_account_manager.models import Account


def test_account_switching():
    """测试账号切换的完整流程"""
    print("=== 测试账号切换功能 ===\n")
    
    # 创建临时目录用于测试
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 1. 创建配置路径管理器
        print("1. 初始化配置路径管理器...")
        config_file = temp_path / "config.json"
        path_manager = ConfigPathManager(config_file)
        
        # 创建模拟的Windsurf配置路径
        test_config_path1 = temp_path / "windsurf_config1"
        test_config_path2 = temp_path / "windsurf_config2"
        test_config_path1.mkdir(parents=True, exist_ok=True)
        test_config_path2.mkdir(parents=True, exist_ok=True)
        
        # 创建模拟的配置文件
        (test_config_path1 / "settings.json").write_text(json.dumps({"theme": "dark"}))
        (test_config_path2 / "settings.json").write_text(json.dumps({"theme": "light"}))
        
        # 添加配置路径
        path_manager.add_path(str(test_config_path1), "测试配置1")
        path_manager.add_path(str(test_config_path2), "测试配置2")
        
        # 设置第一个路径为活动路径
        path_manager.set_active_path(str(test_config_path1))
        print(f"   活动路径设置为: {path_manager.get_active_path()}")
        
        # 2. 创建快照管理器
        print("\n2. 初始化快照管理器...")
        snapshot_dir = temp_path / "snapshots"
        snapshot_manager = SnapshotManager(snapshot_dir)
        
        # 3. 创建测试账号
        print("\n3. 创建测试账号...")
        accounts_file = temp_path / "accounts.json"
        
        account1 = Account(
            id="test-account-1",
            email="test1@example.com",
            password="password1",
            plan_name="Pro",
            plan_end="2024-12-31",
            used_prompt_credits=100,
            used_flow_credits=50
        )
        
        account2 = Account(
            id="test-account-2",
            email="test2@example.com",
            password="password2",
            plan_name="Free",
            plan_end="2024-10-31",
            used_prompt_credits=50,
            used_flow_credits=25
        )
        
        accounts = [account1, account2]
        save_accounts(accounts, accounts_file)
        
        # 4. 为账号1创建快照
        print("\n4. 为账号1创建快照...")
        snapshot_name1 = "account1-snapshot"
        success = snapshot_manager.create_snapshot(account1.id, test_config_path1, snapshot_name1)
        print(f"   创建快照结果: {'成功' if success else '失败'}")
        
        if success:
            account1.has_snapshot = True
            account1.snapshot_created_at = "2023-09-15T10:00:00"
            save_accounts(accounts, accounts_file)
            print(f"   快照信息: {snapshot_manager.get_snapshot(account1.id)}")
        
        # 5. 切换到账号2的配置
        print("\n5. 切换到账号2的配置...")
        path_manager.set_active_path(str(test_config_path2))
        print(f"   活动路径已切换到: {path_manager.get_active_path()}")
        
        # 6. 为账号2创建快照
        print("\n6. 为账号2创建快照...")
        snapshot_name2 = "account2-snapshot"
        success = snapshot_manager.create_snapshot(account2.id, test_config_path2, snapshot_name2)
        print(f"   创建快照结果: {'成功' if success else '失败'}")
        
        if success:
            account2.has_snapshot = True
            account2.snapshot_created_at = "2023-09-15T11:00:00"
            save_accounts(accounts, accounts_file)
            print(f"   快照信息: {snapshot_manager.get_snapshot(account2.id)}")
        
        # 7. 模拟切换回账号1
        print("\n7. 模拟切换回账号1...")
        path_manager.set_active_path(str(test_config_path1))
        print(f"   活动路径已切换到: {path_manager.get_active_path()}")
        
        # 8. 恢复账号1的快照
        print("\n8. 恢复账号1的快照...")
        success = snapshot_manager.restore_snapshot(account1.id, test_config_path1)
        print(f"   恢复快照结果: {'成功' if success else '失败'}")
        
        # 9. 检查配置文件内容
        print("\n9. 检查配置文件内容...")
        settings_content = (test_config_path1 / "settings.json").read_text()
        settings = json.loads(settings_content)
        print(f"   当前配置主题: {settings.get('theme')}")
        
        # 10. 删除账号2的快照
        print("\n10. 删除账号2的快照...")
        success = snapshot_manager.delete_snapshot(account2.id)
        print(f"    删除快照结果: {'成功' if success else '失败'}")
        
        if success:
            account2.has_snapshot = False
            account2.snapshot_created_at = None
            save_accounts(accounts, accounts_file)
            print(f"    账号2快照状态: {account2.has_snapshot}")
        
        print("\n=== 账号切换功能测试完成 ===")
        return True


def test_path_manager_integration():
    """测试路径管理器集成"""
    print("\n=== 测试路径管理器集成 ===\n")
    
    # 创建临时目录用于测试
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 1. 创建配置路径管理器
        print("1. 初始化配置路径管理器...")
        config_file = temp_path / "config.json"
        path_manager = ConfigPathManager(config_file)
        
        # 2. 测试路径添加和获取
        print("\n2. 测试路径添加和获取...")
        test_paths = [
            (temp_path / "path1", "路径1"),
            (temp_path / "path2", "路径2"),
            (temp_path / "path3", "路径3")
        ]
        
        for path, name in test_paths:
            path.mkdir(parents=True, exist_ok=True)
            path_manager.add_path(str(path), name)
        
        paths = path_manager.get_paths()
        print(f"   已添加 {len(paths)} 个路径")
        
        # 3. 测试设置活动路径
        print("\n3. 测试设置活动路径...")
        path_manager.set_active_path(str(test_paths[0][0]))
        active_path = path_manager.get_active_path()
        print(f"   活动路径: {active_path}")
        
        # 4. 测试路径验证
        print("\n4. 测试路径验证...")
        valid_path = temp_path / "valid_path"
        valid_path.mkdir(parents=True, exist_ok=True)
        (valid_path / "settings.json").write_text("{}")
        
        invalid_path = temp_path / "invalid_path"
        invalid_path.mkdir(parents=True, exist_ok=True)
        # 不创建settings.json文件
        
        print(f"   有效路径验证结果: {path_manager.validate_path(str(valid_path))}")
        print(f"   无效路径验证结果: {path_manager.validate_path(str(invalid_path))}")
        
        # 5. 测试路径删除
        print("\n5. 测试路径删除...")
        path_manager.remove_path(str(test_paths[2][0]))
        paths_after_removal = path_manager.get_paths()
        print(f"   删除后剩余路径数: {len(paths_after_removal)}")
        
        print("\n=== 路径管理器集成测试完成 ===")
        return True


if __name__ == "__main__":
    print("开始测试切号功能...\n")
    
    try:
        # 测试账号切换功能
        test1_result = test_account_switching()
        
        # 测试路径管理器集成
        test2_result = test_path_manager_integration()
        
        if test1_result and test2_result:
            print("\n✅ 所有测试通过！")
            sys.exit(0)
        else:
            print("\n❌ 部分测试失败！")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
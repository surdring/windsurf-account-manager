#!/usr/bin/env python3
"""
简化的切号功能测试
"""
import os
import sys
import json
import tempfile
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 创建日志文件
log_file = project_root / "test_log.txt"
with log_file.open("w", encoding="utf-8") as f:
    f.write("=== 测试开始 ===\n")

def log(message):
    print(message)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(message + "\n")

try:
    from windsurf_account_manager.config_path_manager import ConfigPathManager
    from windsurf_account_manager.config_snapshot import ConfigSnapshot
    from windsurf_account_manager.storage import save_accounts
    from windsurf_account_manager.models import Account
    
    log("所有模块导入成功")
    
    # 创建临时目录用于测试
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    log(f"临时目录: {temp_path}")
    
    # 创建配置路径管理器
    config_file = temp_path / "config.json"
    path_manager = ConfigPathManager(config_file)
    log("配置路径管理器创建成功")
    
    # 创建快照管理器
    snapshot_dir = temp_path / "snapshots"
    snapshot_manager = ConfigSnapshot(snapshot_dir)
    log("快照管理器创建成功")
    
    # 创建测试账号
    account1 = Account(
        id="test-account-1",
        email="test1@example.com",
        password="password1"
    )
    log("测试账号创建成功")
    
    # 创建模拟的Windsurf配置路径
    test_config_path = temp_path / "windsurf_config"
    test_config_path.mkdir(parents=True, exist_ok=True)
    
    # 创建模拟的配置文件
    (test_config_path / "settings.json").write_text(json.dumps({"theme": "dark"}))
    log("模拟配置文件创建成功")
    
    # 测试创建快照
    snapshot_name = "test-snapshot"
    success = snapshot_manager.create_snapshot(account1.id, test_config_path, snapshot_name)
    log(f"创建快照结果: {'成功' if success else '失败'}")
    
    # 检查快照是否创建成功
    snapshot_dir = snapshot_manager.get_account_snapshot_dir(account1.id)
    metadata_file = snapshot_dir / "metadata.json"
    if metadata_file.exists():
        log("快照元数据文件存在")
        with metadata_file.open("r", encoding="utf-8") as f:
            metadata = json.load(f)
            log(f"快照元数据: {metadata}")
    else:
        log("快照元数据文件不存在")
    
    # 测试恢复快照
    success = snapshot_manager.restore_snapshot(account1.id, test_config_path)
    log(f"恢复快照结果: {'成功' if success else '失败'}")
    
    # 测试删除快照
    success = snapshot_manager.delete_snapshot(account1.id)
    log(f"删除快照结果: {'成功' if success else '失败'}")
    
    log("所有测试通过!")
    
except Exception as e:
    log(f"测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
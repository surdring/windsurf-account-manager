from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class Account:
    id: str
    email: str
    password: str = ""
    note: str = ""
    plan_name: Optional[str] = None
    plan_tier: Optional[str] = None
    plan_end: Optional[str] = None
    used_prompt_credits: Optional[int] = None
    used_flow_credits: Optional[int] = None
    api_key: Optional[str] = None
    last_sync_time: Optional[str] = None
    # 新增字段，用于跟踪配置快照
    has_snapshot: bool = False
    snapshot_created_at: Optional[str] = None


@dataclass
class McpServerConfig:
    id: str
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class RuleConfig:
    id: str
    prompt: str


@dataclass
class AppSettings:
    mcp_config_path: Optional[str] = None
    rules_config_path: Optional[str] = None
    windsurf_config_path: Optional[str] = None
    restart_command: Optional[str] = None
    # 新增字段，用于配置快照功能
    auto_backup_before_switch: bool = True
    auto_create_snapshot: bool = False
    external_login_script: Optional[str] = None

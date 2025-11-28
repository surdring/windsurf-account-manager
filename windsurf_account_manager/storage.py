from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Any

from .models import Account


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ACCOUNTS_PATH = DATA_DIR / "accounts.json"


def load_accounts() -> List[Account]:
    if not ACCOUNTS_PATH.exists():
        return []
    with ACCOUNTS_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    accounts: List[Account] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            # 处理旧版本数据，确保新字段有默认值
            account_data = {
                "id": item["id"],
                "email": item["email"],
                "password": item.get("password", ""),
                "note": item.get("note", ""),
                "plan_name": item.get("plan_name"),
                "plan_tier": item.get("plan_tier"),
                "plan_end": item.get("plan_end"),
                "used_prompt_credits": item.get("used_prompt_credits"),
                "used_flow_credits": item.get("used_flow_credits"),
                "api_key": item.get("api_key"),
                "last_sync_time": item.get("last_sync_time"),
                # 新增字段
                "has_snapshot": item.get("has_snapshot", False),
                "snapshot_created_at": item.get("snapshot_created_at")
            }
            accounts.append(Account(**account_data))
        except (TypeError, KeyError):
            continue
    return accounts


def save_accounts(accounts: List[Account]) -> None:
    data = [_account_to_dict(a) for a in accounts]
    with ACCOUNTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _account_to_dict(account: Account) -> Dict[str, Any]:
    """将Account对象转换为字典"""
    return {
        "id": account.id,
        "email": account.email,
        "password": account.password,
        "note": account.note,
        "plan_name": account.plan_name,
        "plan_tier": account.plan_tier,
        "plan_end": account.plan_end,
        "used_prompt_credits": account.used_prompt_credits,
        "used_flow_credits": account.used_flow_credits,
        "api_key": account.api_key,
        "last_sync_time": account.last_sync_time,
        # 新增字段
        "has_snapshot": account.has_snapshot,
        "snapshot_created_at": account.snapshot_created_at
    }


def import_from_windsurf_json(path: Path, existing: List[Account]) -> List[Account]:
    if not path.exists():
        return existing
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    by_email = {a.email: a for a in existing}
    from uuid import uuid4
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            email = item.get("email")
            if not email or email in by_email:
                continue
            password = item.get("password", "")
            acc = Account(id=str(uuid4()), email=email, password=password)
            by_email[email] = acc
    return list(by_email.values())


def export_accounts(path: Path, accounts: List[Account]) -> None:
    data = [asdict(a) for a in accounts]
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
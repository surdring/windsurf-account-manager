from __future__ import annotations

import json
import requests
from typing import Any, Dict, Optional
from dataclasses import asdict

from .models import Account


class ApiClient:
    def __init__(self) -> None:
        # Firebase API配置 - 需要根据实际情况调整
        self.firebase_api_key = "AIzaSyDxV52Wp8XiJhZGWWl2zTbqf1sYg9jK8sE"  # 这是一个示例，需要从Windsurf获取真实的API key
        self.base_url = "https://api2.cursor.sh"
        
    def get_firebase_id_token(self, email: str, password: str) -> Optional[str]:
        """使用邮箱密码获取Firebase ID Token"""
        try:
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.firebase_api_key}"
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get("idToken")
            else:
                print(f"Firebase登录失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"获取Firebase ID Token时出错: {e}")
            return None
    
    def get_auth_token(self, firebase_id_token: str) -> Optional[str]:
        """使用Firebase ID Token获取Windsurf Auth Token"""
        try:
            # 这里需要使用protobuf，但为了简化，我们先尝试使用JSON
            url = f"{self.base_url}/exa.seat_management.v1.SeatManagementService/GetOneTimeAuthToken"
            
            # 实际实现应该使用protobuf序列化，这里使用JSON作为示例
            payload = {
                "firebase_id_token": firebase_id_token
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("auth_token")
            else:
                print(f"获取Auth Token失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"获取Auth Token时出错: {e}")
            return None
    
    def get_current_user(self, auth_token: str) -> Optional[Dict[str, Any]]:
        """使用Auth Token获取用户信息"""
        try:
            url = f"{self.base_url}/exa.seat_management.v1.SeatManagementService/GetCurrentUser"
            
            payload = {
                "auth_token": auth_token,
                "generateProfilePictureUrl": True,
                "createIfNotExist": True,
                "includeSubscription": True
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-Auth-Token": auth_token
            }
            
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"获取用户信息失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"获取用户信息时出错: {e}")
            return None
    
    def get_current_period_usage(self, bearer_token: str) -> Optional[Dict[str, Any]]:
        """使用Bearer Token获取使用量信息"""
        try:
            url = f"{self.base_url}/aiserver.v1.DashboardService/GetCurrentPeriodUsage"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {bearer_token}"
            }
            
            response = requests.post(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"获取使用量信息失败: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"获取使用量信息时出错: {e}")
            return None
    
    def login_and_update_account(self, account: Account) -> bool:
        """完整的登录流程并更新账号信息"""
        # 获取Firebase ID Token
        firebase_id_token = self.get_firebase_id_token(account.email, account.password)
        if not firebase_id_token:
            return False
        
        # 获取Auth Token
        auth_token = self.get_auth_token(firebase_id_token)
        if not auth_token:
            return False
        
        # 获取用户信息
        user_data = self.get_current_user(auth_token)
        if not user_data:
            return False
        
        # 更新账号信息
        try:
            if "user" in user_data:
                user = user_data["user"]
                account.api_key = user.get("api_key")
                
            if "plan_info" in user_data:
                plan_info = user_data["plan_info"]
                account.plan_name = plan_info.get("plan_name")
                
            if "plan_status" in user_data:
                plan_status = user_data["plan_status"]
                account.plan_end = plan_status.get("plan_end")
                account.used_prompt_credits = plan_status.get("used_prompt_credits")
                account.used_flow_credits = plan_status.get("used_flow_credits")
                
            # 更新同步时间
            from datetime import datetime
            account.last_sync_time = datetime.now().isoformat()
            
            return True
        except Exception as e:
            print(f"更新账号信息时出错: {e}")
            return False

import time
from typing import List, Dict, Any, Optional

class AuthService:
    def __init__(self):
        self.users = {
            "admin@oceanguard.ai": {
                "id": "USR-001",
                "email": "admin@oceanguard.ai",
                "name": "Commander Sarah Vance",
                "role": "Administrator",
                "department": "Maritime Security Operations Center (MSOC)",
                "token": "token-admin-oceanguard-99213"
            },
            "analyst@oceanguard.ai": {
                "id": "USR-002",
                "email": "analyst@oceanguard.ai",
                "name": "Dr. Alex Rivera",
                "role": "GIS & Satellite Analyst",
                "department": "Submarine Cable Intelligence Unit",
                "token": "token-analyst-oceanguard-44102"
            }
        }
        
        self.audit_logs: List[Dict[str, Any]] = [
            {
                "id": "LOG-1001",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600)),
                "user": "Commander Sarah Vance",
                "role": "Administrator",
                "action": "SYSTEM_INITIALIZATION",
                "details": "OceanGuard AI Backend GIS and AI Risk Engine initialized."
            },
            {
                "id": "LOG-1002",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 1800)),
                "user": "Dr. Alex Rivera",
                "role": "GIS & Satellite Analyst",
                "action": "SENTINEL_SAR_SCAN",
                "details": "Triggered Sentinel-1 SAR orbital sweep over MAREA Cable Corridor."
            }
        ]

    def authenticate_token(self, token: str) -> Optional[Dict[str, Any]]:
        for user in self.users.values():
            if user["token"] == token:
                return user
        # Default mock fallback for dev
        return self.users["admin@oceanguard.ai"]

    def log_action(self, user_name: str, role: str, action: str, details: str):
        log_entry = {
            "id": f"LOG-{int(time.time() * 1000) % 100000}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "user": user_name,
            "role": role,
            "action": action,
            "details": details
        }
        self.audit_logs.insert(0, log_entry)
        if len(self.audit_logs) > 50:
            self.audit_logs.pop()

    def get_audit_logs(self) -> List[Dict[str, Any]]:
        return self.audit_logs

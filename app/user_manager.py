import json
import os
import re
import uuid
import hashlib
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Tuple

DATA_DIR = "data"

def _hash_password(password: str) -> str:
    
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def _normalize_username(username: str) -> str:
    
    normalized = username.lower().strip()
    normalized = normalized.replace("@", "_at_")
    normalized = re.sub(r'[^a-z0-9._-]', '_', normalized)
    return normalized

@dataclass
class User:
    username: str
    password_hash: str
    display_name: str
    avatar_path: Optional[str] = None
    user_id: Optional[str] = None

    def get_folder_name(self) -> str:
        
        return _normalize_username(self.username)

    def to_dict(self) -> Dict:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "User":
        user_fields = {
            'username': data.get('username', ''),
            'password_hash': data.get('password_hash', ''),
            'display_name': data.get('display_name', ''),
            'avatar_path': data.get('avatar_path'),
            'user_id': data.get('user_id'),
        }
        return cls(**user_fields)

class UserManager:

    email_pattern = re.compile(r"^[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def __init__(self):
        self.users: Dict[str, User] = {}
        self._load_users()

    def _load_users(self):
        
        if not os.path.isdir(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
            return

        for entry in os.listdir(DATA_DIR):
            folder = os.path.join(DATA_DIR, entry)
            if not os.path.isdir(folder):
                continue
            profile_path = os.path.join(folder, "profile.json")
            if not os.path.exists(profile_path):
                continue
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                user = User.from_dict(data)
                if user.username:
                    lookup_key = user.username.lower()
                    self.users[lookup_key] = user
            except Exception as e:
                print(f"[UserManager] Failed to load {profile_path}: {e}")

    def _save_user(self, user: User, folder_name: Optional[str] = None):
        
        if folder_name is None:
            folder_name = user.get_folder_name()
        folder = os.path.join(DATA_DIR, folder_name)
        os.makedirs(folder, exist_ok=True)
        profile_path = os.path.join(folder, "profile.json")
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(user.to_dict(), f, ensure_ascii=False, indent=2)

    def register(
        self,
        username: str,
        password: str,
        display_name: str,
        avatar_path: Optional[str] = None,
    ) -> Tuple[bool, str]:
        
        if not username:
            return False, "Username/email is required"
        if not display_name:
            return False, "Display name is required"
        if not password:
            return False, "Password is required"
        if not self.email_pattern.match(username):
            return False, "Please enter a valid email address"

        username_key = username.lower()
        if username_key in self.users:
            return False, "Email already exists"

        for user in self.users.values():
            if user.display_name.lower() == display_name.lower():
                return False, "Display name already exists"

        folder_name = _normalize_username(username)
        
        user = User(
            username=username,
            password_hash=_hash_password(password),
            display_name=display_name,
            avatar_path=avatar_path,
            user_id=str(uuid.uuid4())[:8],
        )
        self.users[username_key] = user
        self._save_user(user, folder_name)
        return True, "Registration successful"

    def login(self, username: str, password: str) -> Tuple[bool, Optional[User], str]:
        
        if not username or not password:
            return False, None, "Missing username or password"

        username_key = username.lower()
        user = self.users.get(username_key)
        if not user:
            return False, None, "User not found"

        if user.password_hash != _hash_password(password):
            return False, None, "Incorrect password"

        return True, user, "Login successful"

    def get_user(self, username: str) -> Optional[User]:
        return self.users.get(username.lower())


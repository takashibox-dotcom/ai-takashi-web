"""
ユーザー管理システム
アカウント作成、認証、プロフィール管理を担当
"""
import json
import hashlib
import secrets
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class User:
    """ユーザー情報"""
    user_id: str
    username: str
    email: str
    password_hash: str
    salt: str
    created_at: str
    password: Optional[str] = None
    updated_at: Optional[str] = None
    last_login: Optional[str] = None
    is_active: bool = True
    profile: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        data = asdict(self)
        # 開発・テスト用に平文パスワードも保存する
        if hasattr(self, 'password') and self.password is not None:
            data['password'] = self.password
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        """辞書からユーザーオブジェクトを作成"""
        return cls(**data)

class UserManager:
    """ユーザー管理クラス"""
    
    def __init__(self, users_file: str = "users.json"):
        self.users_file = users_file
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, str] = {}  # session_id -> user_id
        self.load_users()
    
    def load_users(self):
        """ユーザーデータを読み込み"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_data in data.get('users', []):
                        user = User.from_dict(user_data)
                        self.users[user.user_id] = user
                    self.sessions = data.get('sessions', {})
                logger.info(f"{len(self.users)} ユーザーを読み込みました")
            else:
                logger.info("ユーザーファイルが存在しません。新規作成します。")
        except Exception as e:
            logger.error(f"ユーザーデータ読み込みエラー: {e}")
    
    def save_users(self):
        """ユーザーデータを保存"""
        try:
            data = {
                'users': [user.to_dict() for user in self.users.values()],
                'sessions': self.sessions,
                'last_updated': datetime.now().isoformat()
            }
            
            # デバッグ: 保存するデータを確認
            for user_data in data['users']:
                if user_data.get('username') == 'ｔｋｔｋｔｋ':
                    logger.info(f"保存するパスワード: {user_data.get('password')}")
                    logger.info(f"保存するハッシュ: {user_data.get('password_hash')}")
                    logger.info(f"保存するソルト: {user_data.get('salt')}")
                    break
            
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("ユーザーデータを保存しました")
        except Exception as e:
            logger.error(f"ユーザーデータ保存エラー: {e}")
            import traceback
            logger.error(f"保存エラーのスタックトレース: {traceback.format_exc()}")
    
    def _hash_password(self, password: str, salt: str) -> str:
        """パスワードをハッシュ化"""
        return hashlib.pbkdf2_hmac('sha256', 
                                  password.encode('utf-8'), 
                                  salt.encode('utf-8'), 
                                  100000).hex()
    
    def _generate_salt(self) -> str:
        """ソルトを生成"""
        return secrets.token_hex(16)
    
    def _generate_user_id(self) -> str:
        """ユーザーIDを生成"""
        return f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
    
    def create_user(self, username: str, email: str, password: str) -> Tuple[bool, str]:
        """新規ユーザー作成"""
        try:
            # 重複チェック
            for user in self.users.values():
                if user.username == username:
                    return False, "ユーザー名が既に使用されています"
                if user.email == email:
                    return False, "メールアドレスが既に使用されています"
            
            # バリデーション
            if len(username) < 3:
                return False, "ユーザー名は3文字以上で入力してください"
            if len(password) < 6:
                return False, "パスワードは6文字以上で入力してください"
            if '@' not in email:
                return False, "有効なメールアドレスを入力してください"
            
            # ユーザー作成
            salt = self._generate_salt()
            password_hash = self._hash_password(password, salt)
            user_id = self._generate_user_id()
            
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                salt=salt,
                created_at=datetime.now().isoformat(),
                profile={
                    'display_name': username,
                    'bio': '',
                    'avatar': '',
                    'preferences': {
                        'theme': 'light',
                        'language': 'ja',
                        'notifications': True
                    }
                }
            )
            
            self.users[user_id] = user
            self.save_users()
            
            logger.info(f"新規ユーザー作成: {username} ({user_id})")
            return True, f"アカウント「{username}」を作成しました"
            
        except Exception as e:
            logger.error(f"ユーザー作成エラー: {e}")
            return False, f"アカウント作成に失敗しました: {str(e)}"
    
    def authenticate_user(self, username_or_email: str, password: str) -> Tuple[bool, Optional[str], Optional[User]]:
        """ユーザー認証"""
        try:
            # ユーザー検索（ユーザー名またはメールアドレス）
            user = None
            for u in self.users.values():
                if u.username == username_or_email or u.email == username_or_email:
                    user = u
                    break
            
            if not user:
                return False, "ユーザー名またはパスワードが間違っています", None
            
            if not user.is_active:
                return False, "アカウントが無効化されています", None
            
            # パスワード検証
            password_hash = self._hash_password(password, user.salt)
            if password_hash != user.password_hash:
                return False, "ユーザー名またはパスワードが間違っています", None
            
            # 最終ログイン時刻を更新
            user.last_login = datetime.now().isoformat()
            self.save_users()
            
            logger.info(f"ログイン成功: {user.username} ({user.user_id})")
            return True, "ログインしました", user
            
        except Exception as e:
            logger.error(f"認証エラー: {e}")
            return False, f"ログインに失敗しました: {str(e)}", None
    
    def create_session(self, user_id: str) -> str:
        """セッション作成"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(8)}"
        self.sessions[session_id] = user_id
        self.save_users()
        return session_id
    
    def get_user_by_session(self, session_id: str) -> Optional[User]:
        """セッションからユーザー取得"""
        user_id = self.sessions.get(session_id)
        if user_id:
            return self.users.get(user_id)
        return None
    
    def logout(self, session_id: str) -> bool:
        """ログアウト"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.save_users()
            return True
        return False
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """ユーザーIDでユーザー取得"""
        return self.users.get(user_id)
    
    def update_profile(self, user_id: str, profile_data: Dict) -> Tuple[bool, str]:
        """プロフィール更新"""
        try:
            user = self.users.get(user_id)
            if not user:
                return False, "ユーザーが見つかりません"
            
            if user.profile is None:
                user.profile = {}
            
            # プロフィール更新
            user.profile.update(profile_data)
            self.save_users()
            
            return True, "プロフィールを更新しました"
            
        except Exception as e:
            logger.error(f"プロフィール更新エラー: {e}")
            return False, f"プロフィール更新に失敗しました: {str(e)}"
    
    def change_password(self, user_id: str, current_password: str, new_password: str) -> Tuple[bool, str]:
        """パスワード変更"""
        try:
            user = self.users.get(user_id)
            if not user:
                return False, "ユーザーが見つかりません"
            
            # 現在のパスワード確認
            current_hash = self._hash_password(current_password, user.salt)
            if current_hash != user.password_hash:
                return False, "現在のパスワードが間違っています"
            
            # 新しいパスワード設定
            new_salt = self._generate_salt()
            new_hash = self._hash_password(new_password, new_salt)
            
            user.password_hash = new_hash
            user.salt = new_salt
            self.save_users()
            
            logger.info(f"パスワード変更: {user.username} ({user_id})")
            return True, "パスワードを変更しました"
            
        except Exception as e:
            logger.error(f"パスワード変更エラー: {e}")
            return False, f"パスワード変更に失敗しました: {str(e)}"
    
    def deactivate_user(self, user_id: str) -> Tuple[bool, str]:
        """アカウント無効化"""
        try:
            user = self.users.get(user_id)
            if not user:
                return False, "ユーザーが見つかりません"
            
            user.is_active = False
            # セッションを削除
            sessions_to_remove = [sid for sid, uid in self.sessions.items() if uid == user_id]
            for sid in sessions_to_remove:
                del self.sessions[sid]
            
            self.save_users()
            logger.info(f"アカウント無効化: {user.username} ({user_id})")
            return True, "アカウントを無効化しました"
            
        except Exception as e:
            logger.error(f"アカウント無効化エラー: {e}")
            return False, f"アカウント無効化に失敗しました: {str(e)}"
    
    def cleanup_expired_sessions(self):
        """期限切れセッションのクリーンアップ"""
        # 簡易版：24時間以上古いセッションを削除
        cutoff_time = datetime.now() - timedelta(hours=24)
        sessions_to_remove = []
        
        for session_id, user_id in self.sessions.items():
            # セッションIDから作成時刻を推定（簡易版）
            try:
                timestamp_str = session_id.split('_')[1]
                session_time = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                if session_time < cutoff_time:
                    sessions_to_remove.append(session_id)
            except:
                # パースできないセッションは削除
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.sessions[session_id]
        
        if sessions_to_remove:
            self.save_users()
            logger.info(f"{len(sessions_to_remove)} の期限切れセッションを削除しました")

    def get_user_by_email(self, email: str) -> Optional[User]:
        """メールアドレスでユーザーを検索"""
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    def reset_password(self, user_id: str, new_password: str) -> tuple[bool, str]:
        """パスワードリセット"""
        try:
            logger.info(f"パスワードリセット開始: user_id={user_id}")
            
            # ユーザーを検索
            if user_id not in self.users:
                logger.error(f"ユーザーが見つかりません: user_id={user_id}")
                return False, "ユーザーが見つかりません"
            
            user = self.users[user_id]
            logger.info(f"ユーザー発見: {user.username}")
            
            # 新しいソルトを生成
            new_salt = secrets.token_hex(16)
            logger.info(f"新しいソルト生成: {new_salt}")
            
            # 新しいパスワードハッシュを生成
            new_password_hash = self._hash_password(new_password, new_salt)
            logger.info(f"新しいハッシュ生成: {new_password_hash}")
            
            # ユーザーデータを更新（開発・テスト用に平文パスワードも保存）
            user.password = new_password
            user.password_hash = new_password_hash
            user.salt = new_salt
            user.updated_at = datetime.now().isoformat()
            
            logger.info(f"ユーザーデータ更新完了: {user.username}")
            
            # ファイルを保存
            self.save_users()
            logger.info(f"ファイル保存完了")
            
            # デバッグ: メモリ内のデータを確認
            logger.info(f"メモリ内のパスワード: {user.password}")
            logger.info(f"メモリ内のハッシュ: {user.password_hash}")
            logger.info(f"メモリ内のソルト: {user.salt}")
            
            logger.info(f"ユーザー {user.username} のパスワードをリセットしました")
            return True, "パスワードがリセットされました"
            
        except Exception as e:
            logger.error(f"パスワードリセットエラー: {e}")
            import traceback
            logger.error(f"スタックトレース: {traceback.format_exc()}")
            return False, f"パスワードリセットに失敗しました: {str(e)}"

# グローバルインスタンス
user_manager = UserManager()


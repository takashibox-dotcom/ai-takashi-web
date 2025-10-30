import os
import json
import base64
import hashlib
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging
from pathlib import Path

class SecurityManager:
    """セキュリティ管理クラス"""
    
    def __init__(self):
        # ユーザーのホームディレクトリに設定ファイルを作成
        home_dir = Path.home()
        ai_config_dir = home_dir / ".ai_takashi_config"
        ai_config_dir.mkdir(exist_ok=True)
        
        self.key_file = str(ai_config_dir / "security.key")
        self.encrypted_config_file = str(ai_config_dir / "config.encrypted")
        self.salt_file = ai_config_dir / "security.salt"
        
        # saltをロードまたは生成
        self.salt = self._load_or_generate_salt()
        self._encryption_key = None
    
    def _load_or_generate_salt(self) -> bytes:
        """saltをロードまたは生成"""
        try:
            # saltファイルが存在する場合は読み込み
            if self.salt_file.exists():
                with open(self.salt_file, 'rb') as f:
                    salt = f.read()
                logging.info("既存のsaltを読み込みました")
                return salt
            else:
                # 新しいsaltを生成
                salt = secrets.token_bytes(32)  # 32バイトのランダムなsalt
                
                # saltファイルに保存
                with open(self.salt_file, 'wb') as f:
                    f.write(salt)
                
                # ファイルの権限を設定（読み取り専用）
                try:
                    os.chmod(self.salt_file, 0o600)
                except (OSError, PermissionError) as e:
                    logging.warning(f"saltファイルの権限設定に失敗しました: {e}")
                
                logging.info("新しいsaltを生成して保存しました")
                return salt
        except PermissionError as e:
            logging.warning(f"権限エラーでsaltファイルを操作できません: {e}")
            # フォールバック: メモリ上でのみ使用する一時的なsalt
            return secrets.token_bytes(32)
        except Exception as e:
            logging.error(f"salt生成エラー: {e}")
            # フォールバック: メモリ上でのみ使用する一時的なsalt
            return secrets.token_bytes(32)
    
    def generate_key(self, password: str = None) -> bytes:
        """暗号化キーを生成"""
        if password is None:
            password = os.environ.get('AI_TAKASHI_PASSWORD', 'default_password')
        
        password_bytes = password.encode('utf-8')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        return key
    
    def get_encryption_key(self) -> bytes:
        """暗号化キーを取得"""
        if self._encryption_key is None:
            self._encryption_key = self.generate_key()
        return self._encryption_key
    
    def encrypt_data(self, data: str) -> str:
        """データを暗号化"""
        try:
            key = self.get_encryption_key()
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logging.error(f"暗号化エラー: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """データを復号化"""
        try:
            key = self.get_encryption_key()
            fernet = Fernet(key)
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logging.error(f"復号化エラー: {e}")
            raise
    
    def save_encrypted_config(self, config_data: dict):
        """設定データを暗号化して保存"""
        try:
            json_data = json.dumps(config_data, ensure_ascii=False)
            encrypted_data = self.encrypt_data(json_data)
            
            with open(self.encrypted_config_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
            
            # ファイルの権限を設定（読み取り専用）
            try:
                os.chmod(self.encrypted_config_file, 0o600)
            except (OSError, PermissionError):
                pass  # 権限設定に失敗しても継続
            
            logging.info("設定データを暗号化して保存しました")
        except PermissionError as e:
            logging.warning(f"権限エラーで暗号化設定を保存できません: {e}")
        except Exception as e:
            logging.error(f"設定データ保存エラー: {e}")
            raise
    
    def load_encrypted_config(self) -> dict:
        """暗号化された設定データを読み込み"""
        try:
            if not os.path.exists(self.encrypted_config_file):
                return {}
            
            with open(self.encrypted_config_file, 'r', encoding='utf-8') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.decrypt_data(encrypted_data)
            config_data = json.loads(decrypted_data)
            logging.info("暗号化された設定データを読み込みました")
            return config_data
        except PermissionError as e:
            logging.warning(f"権限エラーで暗号化設定を読み込めません: {e}")
            return {}
        except Exception as e:
            logging.error(f"設定データ読み込みエラー: {e}")
            return {}
    
    def encrypt_api_key(self, api_key: str) -> str:
        """APIキーを暗号化"""
        return self.encrypt_data(api_key)
    
    def decrypt_api_key(self, encrypted_api_key: str) -> str:
        """APIキーを復号化"""
        return self.decrypt_data(encrypted_api_key)
    
    def hash_data(self, data: str) -> str:
        """データのハッシュ値を計算"""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    def verify_file_integrity(self, file_path: str, expected_hash: str) -> bool:
        """ファイルの整合性を確認"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            actual_hash = self.hash_data(content)
            return actual_hash == expected_hash
        except Exception as e:
            logging.error(f"ファイル整合性確認エラー: {e}")
            return False
    
    def secure_delete_file(self, file_path: str):
        """ファイルを安全に削除"""
        try:
            if os.path.exists(file_path):
                # ファイルを0で上書きしてから削除
                with open(file_path, 'r+b') as f:
                    length = f.seek(0, 2)
                    f.seek(0)
                    f.write(b'\0' * length)
                    f.flush()
                    os.fsync(f.fileno())
                os.remove(file_path)
                logging.info(f"ファイルを安全に削除しました: {file_path}")
        except Exception as e:
            logging.error(f"ファイル削除エラー: {e}")
    
    def create_backup_with_encryption(self, source_file: str, backup_file: str):
        """暗号化バックアップを作成"""
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            encrypted_content = self.encrypt_data(content)
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_content)
            
            os.chmod(backup_file, 0o600)
            logging.info(f"暗号化バックアップを作成しました: {backup_file}")
        except Exception as e:
            logging.error(f"バックアップ作成エラー: {e}")
            raise

# セキュリティマネージャーのインスタンス
security_manager = SecurityManager()

def get_secure_api_key():
    """セキュアなAPIキー取得"""
    try:
        # 暗号化された設定から取得を試行
        config = security_manager.load_encrypted_config()
        if 'encrypted_api_key' in config:
            return security_manager.decrypt_api_key(config['encrypted_api_key'])
        
        # 環境変数から取得
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            # 初回時は暗号化して保存
            try:
                encrypted_key = security_manager.encrypt_api_key(api_key)
                config['encrypted_api_key'] = encrypted_key
                security_manager.save_encrypted_config(config)
            except PermissionError:
                logging.warning("権限エラーでAPIキーを暗号化保存できませんが、環境変数から取得します")
            return api_key
        
        return None
    except Exception as e:
        logging.error(f"セキュアAPIキー取得エラー: {e}")
        return os.getenv("GOOGLE_API_KEY")  # フォールバック 
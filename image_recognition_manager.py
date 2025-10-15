import os
import json
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
import uuid

class ImageRecognitionManager:
    """画像認識機能の管理クラス"""
    
    def __init__(self):
        """初期化"""
        # ユーザーのホームディレクトリに設定ディレクトリを作成
        self.home_dir = Path.home()
        self.config_dir = self.home_dir / ".ai_takashi_config"
        self.temp_images_dir = self.config_dir / "temp_images"
        self.history_file = self.config_dir / "image_recognition_history.json"
        
        # ディレクトリの作成
        self.config_dir.mkdir(exist_ok=True)
        self.temp_images_dir.mkdir(exist_ok=True)
        
        # 履歴データの初期化
        self.history = self.load_history()
        
        # 古い画像ファイルの自動削除
        self.cleanup_old_images()
    
    def load_history(self):
        """履歴データを読み込む"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"image_recognition_history": []}
        except Exception as e:
            logging.error(f"履歴読み込みエラー: {e}")
            return {"image_recognition_history": []}
    
    def save_history(self):
        """履歴データを保存する"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"履歴保存エラー: {e}")
            return False
    
    def save_temp_image(self, image_path):
        """
        画像を一時保存ディレクトリにコピーする
        
        Args:
            image_path (str): 元の画像ファイルのパス
        
        Returns:
            str: 保存された画像のパス（失敗時はNone）
        """
        try:
            # ユニークなファイル名を生成
            unique_id = str(uuid.uuid4())
            file_extension = Path(image_path).suffix
            temp_filename = f"{unique_id}{file_extension}"
            temp_path = self.temp_images_dir / temp_filename
            
            # ファイルをコピー
            shutil.copy2(image_path, temp_path)
            
            logging.info(f"画像を一時保存しました: {temp_path}")
            return str(temp_path)
            
        except Exception as e:
            logging.error(f"画像一時保存エラー: {e}")
            return None
    
    def add_recognition_result(self, image_path, question, result, character_name="AI_takashi"):
        """
        画像認識結果を履歴に追加する
        
        Args:
            image_path (str): 画像ファイルのパス
            question (str): ユーザーの質問
            result (str): 認識結果
            character_name (str): 使用したキャラクター名
        
        Returns:
            str: 追加された履歴項目のID
        """
        try:
            # 画像を一時保存
            temp_image_path = self.save_temp_image(image_path)
            
            # 履歴項目を作成
            history_item = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "original_image_path": image_path,
                "temp_image_path": temp_image_path,
                "question": question,
                "recognition_result": result,
                "character_used": character_name,
                "image_info": self._get_image_info(image_path)
            }
            
            # 履歴に追加
            self.history["image_recognition_history"].append(history_item)
            
            # 履歴の制限（最大1000件）
            if len(self.history["image_recognition_history"]) > 1000:
                # 古い履歴を削除
                old_item = self.history["image_recognition_history"].pop(0)
                self._remove_temp_image(old_item.get("temp_image_path"))
            
            # 履歴を保存
            self.save_history()
            
            logging.info(f"画像認識結果を履歴に追加しました: {history_item['id']}")
            return history_item["id"]
            
        except Exception as e:
            logging.error(f"認識結果追加エラー: {e}")
            return None
    
    def _get_image_info(self, image_path):
        """画像の情報を取得する"""
        try:
            from PIL import Image
            
            with Image.open(image_path) as img:
                return {
                    "format": img.format,
                    "size": img.size,
                    "mode": img.mode,
                    "file_size": os.path.getsize(image_path)
                }
        except Exception as e:
            logging.error(f"画像情報取得エラー: {e}")
            return {}
    
    def _remove_temp_image(self, temp_image_path):
        """一時画像ファイルを削除する"""
        try:
            if temp_image_path and os.path.exists(temp_image_path):
                os.remove(temp_image_path)
                logging.info(f"一時画像を削除しました: {temp_image_path}")
        except Exception as e:
            logging.error(f"一時画像削除エラー: {e}")
    
    def cleanup_old_images(self):
        """古い画像ファイルを削除する（7日間以上経過）"""
        try:
            cutoff_date = datetime.now() - timedelta(days=7)
            removed_count = 0
            
            # 履歴から古い項目を削除
            updated_history = []
            for item in self.history["image_recognition_history"]:
                try:
                    item_date = datetime.fromisoformat(item["timestamp"])
                    if item_date < cutoff_date:
                        # 古い項目なので削除
                        self._remove_temp_image(item.get("temp_image_path"))
                        removed_count += 1
                    else:
                        updated_history.append(item)
                except Exception as e:
                    logging.error(f"履歴項目処理エラー: {e}")
                    # エラーがあっても項目は残す
                    updated_history.append(item)
            
            # 履歴を更新
            self.history["image_recognition_history"] = updated_history
            
            # 孤立したファイルの削除
            if self.temp_images_dir.exists():
                for file_path in self.temp_images_dir.iterdir():
                    if file_path.is_file():
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_date:
                            try:
                                file_path.unlink()
                                removed_count += 1
                            except Exception as e:
                                logging.error(f"孤立ファイル削除エラー: {e}")
            
            if removed_count > 0:
                logging.info(f"古い画像ファイルを{removed_count}件削除しました")
                self.save_history()
            
        except Exception as e:
            logging.error(f"古い画像ファイル削除エラー: {e}")
    
    def get_recent_history(self, limit=10):
        """最近の認識履歴を取得する"""
        try:
            history = self.history["image_recognition_history"]
            # 日付でソート（新しい順）
            sorted_history = sorted(history, key=lambda x: x["timestamp"], reverse=True)
            return sorted_history[:limit]
        except Exception as e:
            logging.error(f"履歴取得エラー: {e}")
            return []
    
    def search_history(self, keyword):
        """履歴を検索する"""
        try:
            results = []
            for item in self.history["image_recognition_history"]:
                if (keyword.lower() in item["question"].lower() or 
                    keyword.lower() in item["recognition_result"].lower()):
                    results.append(item)
            
            # 日付でソート（新しい順）
            return sorted(results, key=lambda x: x["timestamp"], reverse=True)
        except Exception as e:
            logging.error(f"履歴検索エラー: {e}")
            return []
    
    def get_statistics(self):
        """統計情報を取得する"""
        try:
            history = self.history["image_recognition_history"]
            
            if not history:
                return {
                    "total_count": 0,
                    "recent_count": 0,
                    "characters_used": {},
                    "image_formats": {}
                }
            
            # 最近7日間の件数
            recent_date = datetime.now() - timedelta(days=7)
            recent_count = 0
            
            # キャラクター別使用回数
            characters_used = {}
            
            # 画像形式別件数
            image_formats = {}
            
            for item in history:
                try:
                    item_date = datetime.fromisoformat(item["timestamp"])
                    if item_date >= recent_date:
                        recent_count += 1
                    
                    # キャラクター使用回数
                    char_name = item.get("character_used", "不明")
                    characters_used[char_name] = characters_used.get(char_name, 0) + 1
                    
                    # 画像形式
                    img_format = item.get("image_info", {}).get("format", "不明")
                    image_formats[img_format] = image_formats.get(img_format, 0) + 1
                    
                except Exception as e:
                    logging.error(f"統計処理エラー: {e}")
            
            return {
                "total_count": len(history),
                "recent_count": recent_count,
                "characters_used": characters_used,
                "image_formats": image_formats
            }
            
        except Exception as e:
            logging.error(f"統計情報取得エラー: {e}")
            return {
                "total_count": 0,
                "recent_count": 0,
                "characters_used": {},
                "image_formats": {}
            }
    
    def export_history(self, export_path):
        """履歴をエクスポートする"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            logging.info(f"履歴をエクスポートしました: {export_path}")
            return True
        except Exception as e:
            logging.error(f"履歴エクスポートエラー: {e}")
            return False
    
    def get_temp_image_dir(self):
        """一時画像ディレクトリのパスを取得する"""
        return str(self.temp_images_dir)
    
    def get_supported_extensions(self):
        """サポートされているファイル拡張子を取得する"""
        return ['.jpg', '.jpeg', '.png', '.gif', '.webp']

# シングルトンインスタンス
image_recognition_manager = ImageRecognitionManager() 
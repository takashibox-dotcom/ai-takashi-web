import json
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

class ConversationMemory:
    """会話記憶クラス"""
    
    def __init__(self, title: str, content: str, **kwargs):
        self.memory_id = kwargs.get('memory_id', str(uuid.uuid4()))
        self.title = title
        self.content = content
        
        # ユーザー情報
        self.user_id = kwargs.get('user_id', None)
        
        # キャラクター情報
        self.character_id = kwargs.get('character_id', 'AI_takashi')
        self.character_name = kwargs.get('character_name', 'AI_takashi')
        
        # 会話履歴
        self.conversation_history = kwargs.get('conversation_history', [])
        
        # メタデータ
        self.category = kwargs.get('category', 'その他')
        self.tags = kwargs.get('tags', [])
        self.importance = kwargs.get('importance', '中')  # 高/中/低
        
        # 日時情報
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.updated_at = kwargs.get('updated_at', datetime.now().isoformat())
        self.last_accessed = kwargs.get('last_accessed', None)
        
        # 統計情報
        self.access_count = kwargs.get('access_count', 0)
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'memory_id': self.memory_id,
            'title': self.title,
            'content': self.content,
            'user_id': self.user_id,
            'character_id': self.character_id,
            'character_name': self.character_name,
            'conversation_history': self.conversation_history,
            'category': self.category,
            'tags': self.tags,
            'importance': self.importance,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'last_accessed': self.last_accessed,
            'access_count': self.access_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationMemory':
        """辞書からインスタンスを作成"""
        return cls(
            title=data['title'],
            content=data['content'],
            memory_id=data.get('memory_id'),
            user_id=data.get('user_id'),
            character_id=data.get('character_id', 'AI_takashi'),
            character_name=data.get('character_name', 'AI_takashi'),
            conversation_history=data.get('conversation_history', []),
            category=data.get('category', 'その他'),
            tags=data.get('tags', []),
            importance=data.get('importance', '中'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            last_accessed=data.get('last_accessed'),
            access_count=data.get('access_count', 0)
        )
    
    def update_access(self):
        """アクセス情報を更新"""
        self.last_accessed = datetime.now().isoformat()
        self.access_count += 1
    
    def update_content(self, title: str = None, content: str = None, 
                      category: str = None, tags: List[str] = None,
                      importance: str = None):
        """記憶内容を更新"""
        if title is not None:
            self.title = title
        if content is not None:
            self.content = content
        if category is not None:
            self.category = category
        if tags is not None:
            self.tags = tags
        if importance is not None:
            self.importance = importance
        self.updated_at = datetime.now().isoformat()

class MemoryManager:
    """会話記憶管理クラス"""
    
    def __init__(self, user_id: str = None, memory_file: str = None):
        self.user_id = user_id
        
        if memory_file is None:
            # ユーザー別フォルダー構造に対応
            if user_id:
                import os
                user_dir = f"users/{user_id}"
                os.makedirs(user_dir, exist_ok=True)
                memory_file = f"{user_dir}/memories.json"
            else:
                # デフォルトファイル（後方互換性のため）
                memory_file = "conversation_memories.json"
        
        self.memory_file = str(memory_file)
        self.memories: List[ConversationMemory] = []
        self.max_memories = 1000  # 最大記憶数
        
        # カテゴリ定義
        self.categories = [
            'ユーザー情報',
            'プロジェクト',
            '技術メモ',
            '雑談',
            '相談',
            'アイデア',
            'その他'
        ]
        
        # 重要度定義
        self.importance_levels = ['高', '中', '低']
        
        self.load_memories()
        
        logging.info("会話記憶マネージャーを初期化しました")
    
    def load_memories(self):
        """記憶ファイルから読み込み"""
        try:
            if Path(self.memory_file).exists():
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = [ConversationMemory.from_dict(m) for m in data]
                logging.info(f"会話記憶{len(self.memories)}件を読み込みました")
            else:
                self.memories = []
                logging.info("新しい会話記憶ファイルを作成します")
        except FileNotFoundError:
            self.memories = []
            logging.info("会話記憶ファイルが見つかりません。新規作成します。")
        except json.JSONDecodeError as e:
            self.memories = []
            logging.error(f"会話記憶ファイルのJSON解析エラー: {e}")
        except PermissionError as e:
            self.memories = []
            logging.error(f"会話記憶ファイルへのアクセス権限がありません: {e}")
        except Exception as e:
            self.memories = []
            logging.error(f"予期しない会話記憶読み込みエラー: {e}", exc_info=True)
    
    def save_memories(self) -> bool:
        """記憶ファイルに保存"""
        try:
            data = [memory.to_dict() for memory in self.memories]
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"会話記憶{len(self.memories)}件を保存しました")
            return True
        except PermissionError as e:
            logging.warning(f"権限エラーで会話記憶を保存できません: {e}")
            return False
        except Exception as e:
            logging.error(f"会話記憶保存エラー: {e}", exc_info=True)
            return False
    
    def add_memory(self, title: str, content: str, character_id: str,
                   character_name: str, conversation_history: List[str],
                   category: str = 'その他', tags: List[str] = None,
                   importance: str = '中', user_id: str = None) -> Optional[str]:
        """新しい記憶を追加"""
        try:
            # 最大数チェック
            if len(self.memories) >= self.max_memories:
                logging.warning(f"記憶最大数({self.max_memories})に達しています")
                # 古い低重要度の記憶を削除
                self._cleanup_old_memories()
            
            # 新しい記憶を作成
            memory = ConversationMemory(
                title=title,
                content=content,
                user_id=user_id or self.user_id,
                character_id=character_id,
                character_name=character_name,
                conversation_history=conversation_history,
                category=category,
                tags=tags or [],
                importance=importance
            )
            
            self.memories.append(memory)
            self.save_memories()
            
            logging.info(f"新しい会話記憶を追加しました: {title}")
            return memory.memory_id
            
        except Exception as e:
            logging.error(f"会話記憶追加エラー: {e}", exc_info=True)
            return None
    
    def get_memory(self, memory_id: str) -> Optional[ConversationMemory]:
        """IDで記憶を取得"""
        for memory in self.memories:
            if memory.memory_id == memory_id:
                memory.update_access()
                self.save_memories()
                return memory
        return None
    
    def get_all_memories(self, sort_by: str = 'created_at', 
                        reverse: bool = True) -> List[ConversationMemory]:
        """全記憶を取得"""
        sorted_memories = sorted(
            self.memories,
            key=lambda m: getattr(m, sort_by, m.created_at),
            reverse=reverse
        )
        return sorted_memories
    
    def search_memories(self, keyword: str = None, character_id: str = None,
                       category: str = None, tags: List[str] = None,
                       importance: str = None) -> List[ConversationMemory]:
        """記憶を検索"""
        results = self.memories.copy()
        
        # キーワード検索
        if keyword:
            keyword_lower = keyword.lower()
            results = [m for m in results if 
                      keyword_lower in m.title.lower() or
                      keyword_lower in m.content.lower() or
                      keyword_lower in m.character_name.lower()]
        
        # キャラクターでフィルター
        if character_id:
            results = [m for m in results if m.character_id == character_id]
        
        # カテゴリでフィルター
        if category:
            results = [m for m in results if m.category == category]
        
        # タグでフィルター
        if tags:
            results = [m for m in results if any(tag in m.tags for tag in tags)]
        
        # 重要度でフィルター
        if importance:
            results = [m for m in results if m.importance == importance]
        
        return results
    
    def update_memory(self, memory_id: str, **updates) -> bool:
        """記憶を更新"""
        try:
            memory = self.get_memory(memory_id)
            if not memory:
                logging.warning(f"記憶ID'{memory_id}'が見つかりません")
                return False
            
            memory.update_content(**updates)
            self.save_memories()
            
            logging.info(f"記憶を更新しました: {memory.title}")
            return True
            
        except Exception as e:
            logging.error(f"記憶更新エラー: {e}", exc_info=True)
            return False
    
    def delete_memory(self, memory_id: str) -> bool:
        """記憶を削除"""
        try:
            memory = None
            for m in self.memories:
                if m.memory_id == memory_id:
                    memory = m
                    break
            
            if not memory:
                logging.warning(f"記憶ID'{memory_id}'が見つかりません")
                return False
            
            self.memories.remove(memory)
            self.save_memories()
            
            logging.info(f"記憶を削除しました: {memory.title}")
            return True
            
        except Exception as e:
            logging.error(f"記憶削除エラー: {e}", exc_info=True)
            return False
    
    def get_memories_by_character(self, character_id: str) -> List[ConversationMemory]:
        """キャラクター別に記憶を取得"""
        return [m for m in self.memories if m.character_id == character_id]
    
    def get_recent_memories(self, limit: int = 10) -> List[ConversationMemory]:
        """最近の記憶を取得"""
        sorted_memories = sorted(
            self.memories,
            key=lambda m: m.created_at,
            reverse=True
        )
        return sorted_memories[:limit]
    
    def get_frequently_accessed_memories(self, limit: int = 10) -> List[ConversationMemory]:
        """よくアクセスされる記憶を取得"""
        sorted_memories = sorted(
            self.memories,
            key=lambda m: m.access_count,
            reverse=True
        )
        return sorted_memories[:limit]
    
    def get_statistics(self) -> Dict:
        """統計情報を取得"""
        try:
            total_count = len(self.memories)
            
            # カテゴリ別集計
            category_counts = {}
            for memory in self.memories:
                category_counts[memory.category] = category_counts.get(memory.category, 0) + 1
            
            # キャラクター別集計
            character_counts = {}
            for memory in self.memories:
                character_counts[memory.character_name] = character_counts.get(memory.character_name, 0) + 1
            
            # 重要度別集計
            importance_counts = {}
            for memory in self.memories:
                importance_counts[memory.importance] = importance_counts.get(memory.importance, 0) + 1
            
            return {
                'total_count': total_count,
                'category_counts': category_counts,
                'character_counts': character_counts,
                'importance_counts': importance_counts,
                'most_accessed': self.get_frequently_accessed_memories(5)
            }
            
        except Exception as e:
            logging.error(f"統計情報取得エラー: {e}", exc_info=True)
            return {}
    
    def _cleanup_old_memories(self):
        """古い低重要度の記憶を削除"""
        try:
            # 低重要度で古い順にソート
            low_importance = [m for m in self.memories if m.importance == '低']
            if low_importance:
                low_importance.sort(key=lambda m: m.created_at)
                # 最も古い低重要度の記憶を削除
                oldest = low_importance[0]
                self.memories.remove(oldest)
                logging.info(f"容量確保のため古い記憶を削除: {oldest.title}")
        except Exception as e:
            logging.error(f"古い記憶削除エラー: {e}", exc_info=True)
    
    def export_memories(self, export_path: str) -> bool:
        """記憶をエクスポート"""
        try:
            data = [memory.to_dict() for memory in self.memories]
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"記憶をエクスポートしました: {export_path}")
            return True
        except Exception as e:
            logging.error(f"記憶エクスポートエラー: {e}", exc_info=True)
            return False
    
    def import_memories(self, import_path: str) -> bool:
        """記憶をインポート"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                imported_memories = [ConversationMemory.from_dict(m) for m in data]
            
            # 既存の記憶とマージ（IDで重複チェック）
            existing_ids = {m.memory_id for m in self.memories}
            new_memories = [m for m in imported_memories if m.memory_id not in existing_ids]
            
            self.memories.extend(new_memories)
            self.save_memories()
            
            logging.info(f"記憶をインポートしました: {len(new_memories)}件")
            return True
        except Exception as e:
            logging.error(f"記憶インポートエラー: {e}", exc_info=True)
            return False

# ユーザー別記憶マネージャーの管理
user_memory_managers: Dict[str, MemoryManager] = {}

def get_or_create_user_memory_manager(user_id: str) -> MemoryManager:
    """ユーザー別の記憶マネージャーを取得または作成"""
    if user_id not in user_memory_managers:
        user_memory_managers[user_id] = MemoryManager(user_id=user_id)
    return user_memory_managers[user_id]

# グローバル記憶マネージャーインスタンス（後方互換性のため）
memory_manager = MemoryManager()


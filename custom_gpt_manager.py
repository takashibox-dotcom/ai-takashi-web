import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

class CustomGPT:
    """完全自由設定可能なカスタムGPTキャラクタークラス"""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.character_id = kwargs.get('character_id', self._generate_id())
        
        # 完全自由設定項目
        self.personality = kwargs.get('personality', '')           # 性格・キャラクター設定
        self.speaking_style = kwargs.get('speaking_style', '')     # 話し方・口調
        self.specialization = kwargs.get('specialization', '')     # 専門分野・得意なこと
        self.response_style = kwargs.get('response_style', '')     # 応答スタイル
        self.background = kwargs.get('background', '')             # 背景・設定
        self.constraints = kwargs.get('constraints', '')           # 制約事項
        self.catchphrase = kwargs.get('catchphrase', '')           # 決まり文句・口癖
        self.greeting = kwargs.get('greeting', '')                 # 挨拶の仕方
        self.custom_instructions = kwargs.get('custom_instructions', '')  # その他の指示
        
        # システム管理項目
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.updated_at = datetime.now().isoformat()
        self.usage_count = kwargs.get('usage_count', 0)
        self.is_default = kwargs.get('is_default', False)
        
        # 会話履歴（キャラクター別）
        self.conversation_history = kwargs.get('conversation_history', [])
    
    def _generate_id(self) -> str:
        """ユニークなキャラクターIDを生成"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def build_system_prompt(self) -> str:
        """ユーザーの自由設定からシステムプロンプトを動的生成"""
        prompt_parts = []
        
        # 基本的なキャラクター紹介
        prompt_parts.append(f"あなたは「{self.name}」というキャラクターです。")
        
        # 性格・キャラクター設定
        if self.personality.strip():
            prompt_parts.append(f"\n【性格・キャラクター】\n{self.personality}")
        
        # 話し方・口調
        if self.speaking_style.strip():
            prompt_parts.append(f"\n【話し方・口調】\n{self.speaking_style}")
        
        # 専門分野・得意なこと
        if self.specialization.strip():
            prompt_parts.append(f"\n【専門分野・得意なこと】\n{self.specialization}")
        
        # 応答スタイル
        if self.response_style.strip():
            prompt_parts.append(f"\n【応答スタイル】\n{self.response_style}")
        
        # 背景・設定
        if self.background.strip():
            prompt_parts.append(f"\n【背景・設定】\n{self.background}")
        
        # 決まり文句・口癖
        if self.catchphrase.strip():
            prompt_parts.append(f"\n【決まり文句・口癖】\n{self.catchphrase}")
        
        # 挨拶の仕方
        if self.greeting.strip():
            prompt_parts.append(f"\n【挨拶の仕方】\n{self.greeting}")
        
        # 制約事項
        if self.constraints.strip():
            prompt_parts.append(f"\n【制約事項・注意点】\n{self.constraints}")
        
        # その他のカスタム指示
        if self.custom_instructions.strip():
            prompt_parts.append(f"\n【その他の指示】\n{self.custom_instructions}")
        
        # 最終的な行動指針
        prompt_parts.append(f"\n上記の設定に従って、「{self.name}」として一貫した personality で会話してください。")
        
        return "\n".join(prompt_parts)
    
    def add_conversation(self, user_message: str, ai_response: str):
        """会話履歴を追加"""
        conversation_entry = {
            'timestamp': datetime.now().isoformat(),
            'user': user_message,
            'ai': ai_response
        }
        self.conversation_history.append(conversation_entry)
        self.usage_count += 1
        self.updated_at = datetime.now().isoformat()
    
    def clear_conversation_history(self):
        """会話履歴をクリア"""
        self.conversation_history = []
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（保存用）"""
        return {
            'name': self.name,
            'character_id': self.character_id,
            'personality': self.personality,
            'speaking_style': self.speaking_style,
            'specialization': self.specialization,
            'response_style': self.response_style,
            'background': self.background,
            'constraints': self.constraints,
            'catchphrase': self.catchphrase,
            'greeting': self.greeting,
            'custom_instructions': self.custom_instructions,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'usage_count': self.usage_count,
            'is_default': self.is_default,
            'conversation_history': self.conversation_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CustomGPT':
        """辞書からインスタンスを作成"""
        return cls(
            name=data['name'],
            character_id=data.get('character_id'),
            personality=data.get('personality', ''),
            speaking_style=data.get('speaking_style', ''),
            specialization=data.get('specialization', ''),
            response_style=data.get('response_style', ''),
            background=data.get('background', ''),
            constraints=data.get('constraints', ''),
            catchphrase=data.get('catchphrase', ''),
            greeting=data.get('greeting', ''),
            custom_instructions=data.get('custom_instructions', ''),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            usage_count=data.get('usage_count', 0),
            is_default=data.get('is_default', False),
            conversation_history=data.get('conversation_history', [])
        )
    
    def clone(self, new_name: str = None) -> 'CustomGPT':
        """キャラクターを複製（テンプレートとして使用）"""
        clone_data = self.to_dict()
        clone_data['name'] = new_name or f"{self.name}のコピー"
        clone_data['character_id'] = None  # 新しいIDを生成
        clone_data['conversation_history'] = []  # 履歴はクリア
        clone_data['usage_count'] = 0
        clone_data['is_default'] = False
        clone_data['created_at'] = None  # 新しい作成日時
        return CustomGPT.from_dict(clone_data)

class CustomGPTManager:
    """完全自由なカスタムGPT管理クラス"""
    
    def __init__(self, characters_file: str = None, user_id: str = None):
        self.user_id = user_id
        if characters_file is None:
            if user_id:
                # ユーザー別フォルダー構造に対応
                self.user_dir = f"users/{user_id}"
                os.makedirs(self.user_dir, exist_ok=True)
                characters_file = f"{self.user_dir}/characters.json"
            else:
                # ユーザーのホームディレクトリに設定ファイルを作成
                home_dir = Path.home()
                ai_config_dir = home_dir / ".ai_takashi_config"
                ai_config_dir.mkdir(exist_ok=True)  # ディレクトリが存在しない場合は作成
                characters_file = ai_config_dir / "custom_characters.json"
        self.characters_file = str(characters_file)
        self.characters: List[CustomGPT] = []
        self.active_character: Optional[CustomGPT] = None
        self.max_characters = 100  # より多くのキャラクターを保存可能
        
        self.load_characters()
        
        # デフォルトキャラクター（AI_takashi）を初期化
        if not self.characters:
            self._create_default_ai_takashi()
        
        # AI_takashiをアクティブキャラクターに設定
        if not self.active_character:
            ai_takashi = self.get_character_by_name("AI_takashi")
            if ai_takashi:
                self.set_active_character(ai_takashi)
    
    def load_characters(self):
        """キャラクターファイルから読み込み"""
        try:
            if os.path.exists(self.characters_file):
                with open(self.characters_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.characters = [CustomGPT.from_dict(char_data) for char_data in data]
                logging.info(f"カスタムキャラクター{len(self.characters)}件を読み込みました")
            else:
                self.characters = []
                logging.info("新しいカスタムキャラクターファイルを作成します")
        except FileNotFoundError:
            self.characters = []
            logging.info("キャラクターファイルが見つかりません。新規作成します。")
        except json.JSONDecodeError as e:
            self.characters = []
            logging.error(f"キャラクターファイルのJSON解析エラー: {e}")
        except PermissionError as e:
            self.characters = []
            logging.error(f"キャラクターファイルへのアクセス権限がありません: {e}")
        except Exception as e:
            self.characters = []
            logging.error(f"予期しないキャラクター読み込みエラー: {e}", exc_info=True)
    
    def save_characters(self):
        """キャラクターファイルに保存"""
        try:
            data = [character.to_dict() for character in self.characters]
            with open(self.characters_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"カスタムキャラクター{len(self.characters)}件を保存しました")
        except PermissionError as e:
            logging.warning(f"権限エラーでキャラクター保存できません: {e}")
            logging.warning("一時的にメモリ上でキャラクターを管理します")
            # 権限エラーの場合は例外を発生させずに継続
            return False
        except Exception as e:
            logging.error(f"キャラクター保存エラー: {e}")
            return False
        return True
    
    def create_character(self, name: str, **settings) -> bool:
        """新しいキャラクターを作成"""
        try:
            # 最大数チェック
            if len(self.characters) >= self.max_characters:
                logging.warning(f"キャラクター最大数({self.max_characters})に達しています")
                return False
            
            # 名前の重複チェック
            if self.get_character_by_name(name):
                logging.warning(f"キャラクター名'{name}'は既に存在します")
                return False
            
            # 新しいキャラクター作成
            character = CustomGPT(name=name, **settings)
            self.characters.append(character)
            saved = self.save_characters()
            
            if saved:
                logging.info(f"新しいキャラクター'{name}'を作成しました")
            else:
                logging.warning(f"新しいキャラクター'{name}'を作成しました（メモリ上のみ）")
            return True
            
        except Exception as e:
            logging.error(f"キャラクター作成エラー: {e}")
            return False
    
    def update_character(self, character_id: str, **settings) -> bool:
        """既存キャラクターを更新"""
        try:
            character = self.get_character_by_id(character_id)
            if not character:
                logging.warning(f"キャラクターID'{character_id}'が見つかりません")
                return False
            
            # 設定を更新
            for key, value in settings.items():
                if hasattr(character, key):
                    setattr(character, key, value)
            
            character.updated_at = datetime.now().isoformat()
            saved = self.save_characters()
            
            if saved:
                logging.info(f"キャラクター'{character.name}'を更新しました")
            else:
                logging.warning(f"キャラクター'{character.name}'を更新しました（メモリ上のみ）")
            return True
            
        except Exception as e:
            logging.error(f"キャラクター更新エラー: {e}")
            return False
    
    def delete_character(self, character_id: str) -> bool:
        """キャラクターを削除"""
        try:
            character = self.get_character_by_id(character_id)
            if not character:
                logging.warning(f"キャラクターID'{character_id}'が見つかりません")
                return False
            
            # デフォルトキャラクターは削除不可
            if character.is_default:
                logging.warning(f"デフォルトキャラクター'{character.name}'は削除できません")
                return False
            
            # アクティブキャラクターの場合はAI_takashiに切り替え
            if self.active_character and self.active_character.character_id == character_id:
                ai_takashi = self.get_character_by_name("AI_takashi")
                if ai_takashi:
                    self.set_active_character(ai_takashi)
            
            self.characters.remove(character)
            saved = self.save_characters()
            
            if saved:
                logging.info(f"キャラクター'{character.name}'を削除しました")
            else:
                logging.warning(f"キャラクター'{character.name}'を削除しました（メモリ上のみ）")
            return True
            
        except Exception as e:
            logging.error(f"キャラクター削除エラー: {e}")
            return False
    
    def get_character_by_id(self, character_id: str) -> Optional[CustomGPT]:
        """IDでキャラクターを取得"""
        for character in self.characters:
            if character.character_id == character_id:
                return character
        return None
    
    def get_character_by_name(self, name: str) -> Optional[CustomGPT]:
        """名前でキャラクターを取得"""
        for character in self.characters:
            if character.name == name:
                return character
        return None
    
    def search_characters(self, keyword: str) -> List[CustomGPT]:
        """キーワードでキャラクターを検索"""
        keyword_lower = keyword.lower()
        results = []
        
        for character in self.characters:
            # 名前、性格、専門分野、背景から検索
            searchable_text = f"{character.name} {character.personality} {character.specialization} {character.background}".lower()
            if keyword_lower in searchable_text:
                results.append(character)
        
        return results
    
    def get_all_characters(self) -> List[CustomGPT]:
        """全キャラクターを取得"""
        return self.characters.copy()
    
    def set_active_character(self, character: CustomGPT):
        """アクティブキャラクターを設定"""
        self.active_character = character
        logging.info(f"アクティブキャラクターを'{character.name}'に変更しました")
    
    def get_active_character(self) -> Optional[CustomGPT]:
        """現在のアクティブキャラクターを取得"""
        return self.active_character
    
    def get_character_count(self) -> int:
        """キャラクター数を取得"""
        return len(self.characters)
    
    def _create_default_ai_takashi(self):
        """デフォルトのAI_takashiキャラクターを作成"""
        ai_takashi = CustomGPT(
            name="AI_takashi",
            personality="親しみやすく、気さくで話しかけやすい性格。豊富な知識を持ちながらも堅苦しくない。ユーザーの質問に丁寧に答える。",
            speaking_style="フレンドリーで親しみやすい口調。「質問あるかね?」のような気さくな話し方。",
            specialization="一般的な質問への回答、様々な分野の基本的な知識。",
            response_style="分かりやすく丁寧な説明。必要に応じて具体例を交えて説明する。",
            greeting="質問あるかね?",
            is_default=True
        )
        
        self.characters.append(ai_takashi)
        saved = self.save_characters()
        if saved:
            logging.info("デフォルトキャラクター AI_takashi を作成しました")
        else:
            logging.warning("デフォルトキャラクター AI_takashi を作成しました（メモリ上のみ）")

# グローバルカスタムGPTマネージャーインスタンス
custom_gpt_manager = CustomGPTManager() 
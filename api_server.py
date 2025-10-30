"""
AI Takashi API Server
FastAPIを使用したRESTful APIサーバー

主要機能:
- テキスト応答生成
- 画像認識
- カスタムGPTキャラクター管理
- 会話履歴管理
- トークン使用量管理
- メモリ機能
"""

import os
import json
import logging
import base64
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# 既存のモジュールをインポート
from text_build import get_google_api_key, configure_api, generate_response, generate_image_response
from custom_gpt_manager import custom_gpt_manager, CustomGPT
from user_manager import user_manager
from memory_manager import memory_manager, get_or_create_user_memory_manager
# response_time_manager は削除されたため、コメントアウト
# from response_time_manager import response_time_manager
from security_utils import get_secure_api_key

# ログ設定（ローカルディレクトリに保存）
import tempfile
temp_dir = tempfile.gettempdir()
log_file = os.path.join(temp_dir, 'ai_takashi_api_server.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# FastAPIアプリケーションの初期化（lifespanで再定義されます）

# グローバル変数
model = None
api_key = None
conversation_sessions = {}  # セッション管理
token_usage_data = {}  # トークン使用量管理
memory_data = {}  # メモリデータ管理

# データモデル定義
class ChatRequest(BaseModel):
    """チャットリクエスト"""
    session_id: str = Field(..., description="セッションID")
    message: str = Field(..., description="ユーザーのメッセージ")
    character_id: Optional[str] = Field(None, description="キャラクターID")
    user_id: Optional[str] = Field(None, description="ユーザーID")

# アカウント管理用モデル
class RegisterRequest(BaseModel):
    """ユーザー登録リクエスト"""
    username: str = Field(..., description="ユーザー名")
    email: str = Field(..., description="メールアドレス")
    password: str = Field(..., description="パスワード")

class LoginRequest(BaseModel):
    """ログインリクエスト"""
    username_or_email: str = Field(..., description="ユーザー名またはメールアドレス")
    password: str = Field(..., description="パスワード")

class ProfileUpdateRequest(BaseModel):
    """プロフィール更新リクエスト"""
    display_name: Optional[str] = Field(None, description="表示名")
    bio: Optional[str] = Field(None, description="自己紹介")
    avatar: Optional[str] = Field(None, description="アバターURL")

class PasswordChangeRequest(BaseModel):
    """パスワード変更リクエスト"""
    current_password: str = Field(..., description="現在のパスワード")
    new_password: str = Field(..., description="新しいパスワード")

class PasswordResetRequest(BaseModel):
    """パスワードリセットリクエスト"""
    email: str = Field(..., description="メールアドレス")

class ReRegisterRequest(BaseModel):
    """再登録リクエスト"""
    email: str = Field(..., description="メールアドレス")
    new_password: str = Field(..., description="新しいパスワード")

class ChatResponse(BaseModel):
    """チャットレスポンス"""
    session_id: str = Field(..., description="セッションID")
    response: str = Field(..., description="AIの応答")
    tokens_used: int = Field(..., description="使用トークン数")
    response_time: float = Field(..., description="応答時間（秒）")
    timestamp: str = Field(..., description="タイムスタンプ")

class ImageChatRequest(BaseModel):
    """画像チャットリクエスト"""
    session_id: str = Field(..., description="セッションID")
    message: str = Field(..., description="ユーザーのメッセージ")
    character_id: Optional[str] = Field(None, description="キャラクターID")

class SessionInfo(BaseModel):
    """セッション情報"""
    session_id: str
    created_at: str
    message_count: int
    total_tokens: int
    character_id: Optional[str] = None

class TokenUsageStats(BaseModel):
    """トークン使用統計"""
    total_tokens: int
    daily_usage: List[Dict[str, Any]]
    monthly_reset_date: str
    warning_threshold: int

class MemoryEntry(BaseModel):
    """メモリエントリ"""
    id: str
    title: str
    content: str
    category: str
    tags: List[str]
    importance: str
    created_at: str
    character_id: str

# 依存性注入
def get_model():
    """モデルインスタンスを取得"""
    global model
    if model is None:
        raise HTTPException(status_code=500, detail="モデルが初期化されていません")
    return model

def get_session(session_id: str) -> Dict[str, Any]:
    """セッション情報を取得"""
    if session_id not in conversation_sessions:
        # 新しいセッションを作成
        conversation_sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "conversation_history": [],
            "total_tokens": 0,
            "message_count": 0,
            "character_id": None
        }
    return conversation_sessions[session_id]

# API初期化
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    global model, api_key
    
    try:
        # APIキーの取得
        api_key = get_google_api_key()
        if not api_key:
            raise Exception("Google APIキーが設定されていません")
        
        # モデルの初期化
        model = configure_api(api_key)
        
        # カスタムGPTマネージャーの初期化
        custom_gpt_manager.load_characters()
        
        # メモリマネージャーの初期化
        memory_manager.load_memories()
        
        # ユーザーマネージャーの初期化
        user_manager.cleanup_expired_sessions()
        
        logging.info("APIサーバーが正常に初期化されました")
        
    except Exception as e:
        logging.error(f"APIサーバーの初期化エラー: {e}")
        raise
    
    yield  # アプリケーション実行中
    
    # クリーンアップ処理（必要に応じて）
    logging.info("APIサーバーを終了しています...")

# FastAPIアプリケーションにlifespanを設定
app = FastAPI(
    title="AI Takashi API",
    description="AI TakashiのAPIサーバー",
    version="1.0.0",
    lifespan=lifespan
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限してください
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ヘルスチェック
@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# アカウント管理エンドポイント
@app.post("/api/auth/register")
async def register_user(request: RegisterRequest):
    """ユーザー登録"""
    try:
        success, message = user_manager.create_user(
            username=request.username,
            email=request.email,
            password=request.password
        )
        
        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        logging.error(f"ユーザー登録エラー: {e}")
        raise HTTPException(status_code=500, detail=f"登録に失敗しました: {str(e)}")

@app.post("/api/auth/login")
async def login_user(request: LoginRequest):
    """ユーザーログイン"""
    try:
        success, message, user = user_manager.authenticate_user(
            username_or_email=request.username_or_email,
            password=request.password
        )
        
        if success and user:
            session_id = user_manager.create_session(user.user_id)
            return {
                "success": True,
                "message": message,
                "session_id": session_id,
                "user": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "profile": user.profile
                }
            }
        else:
            raise HTTPException(status_code=401, detail=message)
            
    except Exception as e:
        logging.error(f"ログインエラー: {e}")
        raise HTTPException(status_code=500, detail=f"ログインに失敗しました: {str(e)}")

@app.post("/api/auth/logout")
async def logout_user(session_id: str):
    """ユーザーログアウト"""
    try:
        success = user_manager.logout(session_id)
        if success:
            return {"success": True, "message": "ログアウトしました"}
        else:
            raise HTTPException(status_code=400, detail="セッションが見つかりません")
            
    except Exception as e:
        logging.error(f"ログアウトエラー: {e}")
        raise HTTPException(status_code=500, detail=f"ログアウトに失敗しました: {str(e)}")

@app.get("/api/auth/me")
async def get_current_user(session_id: str):
    """現在のユーザー情報取得"""
    try:
        user = user_manager.get_user_by_session(session_id)
        if user:
            return {
                "success": True,
                "user": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "profile": user.profile,
                    "created_at": user.created_at,
                    "last_login": user.last_login
                }
            }
        else:
            raise HTTPException(status_code=401, detail="セッションが無効です")
            
    except Exception as e:
        logging.error(f"ユーザー情報取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ユーザー情報の取得に失敗しました: {str(e)}")

@app.put("/api/auth/profile")
async def update_profile(request: ProfileUpdateRequest, session_id: str):
    """プロフィール更新"""
    try:
        user = user_manager.get_user_by_session(session_id)
        if not user:
            raise HTTPException(status_code=401, detail="セッションが無効です")
        
        profile_data = {}
        if request.display_name is not None:
            profile_data["display_name"] = request.display_name
        if request.bio is not None:
            profile_data["bio"] = request.bio
        if request.avatar is not None:
            profile_data["avatar"] = request.avatar
        
        success, message = user_manager.update_profile(user.user_id, profile_data)
        
        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        logging.error(f"プロフィール更新エラー: {e}")
        raise HTTPException(status_code=500, detail=f"プロフィール更新に失敗しました: {str(e)}")

@app.post("/api/auth/change-password")
async def change_password(request: PasswordChangeRequest, session_id: str):
    """パスワード変更"""
    try:
        user = user_manager.get_user_by_session(session_id)
        if not user:
            raise HTTPException(status_code=401, detail="セッションが無効です")
        
        success, message = user_manager.change_password(
            user_id=user.user_id,
            current_password=request.current_password,
            new_password=request.new_password
        )
        
        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        logging.error(f"パスワード変更エラー: {e}")
        raise HTTPException(status_code=500, detail=f"パスワード変更に失敗しました: {str(e)}")

@app.post("/api/auth/reset-password")
async def reset_password(request: PasswordResetRequest):
    """パスワードリセット"""
    try:
        # メールアドレスでユーザーを検索
        user = user_manager.get_user_by_email(request.email)
        if not user:
            # セキュリティのため、ユーザーが存在しない場合でも成功メッセージを返す
            return {"success": True, "message": "パスワードをリセットしました。新しいパスワードを設定してください。"}
        
        # 新しいパスワードを生成（テスト用）
        import secrets
        import string
        new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        
        # パスワードを更新
        success, message = user_manager.reset_password(user.user_id, new_password)
        
        if success:
            logging.info(f"パスワードリセット: ユーザー {user.username} のパスワードをリセットしました")
            return {
                "success": True, 
                "message": "パスワードをリセットしました。新しいパスワードを設定してください。"
            }
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        logging.error(f"パスワードリセットエラー: {e}")
        raise HTTPException(status_code=500, detail=f"パスワードリセットに失敗しました: {str(e)}")

@app.post("/api/auth/re-register")
async def re_register(request: ReRegisterRequest):
    """パスワード再設定（再登録）"""
    try:
        # メールアドレスでユーザーを検索
        user = user_manager.get_user_by_email(request.email)
        if not user:
            raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
        
        # パスワードを更新
        success, message = user_manager.reset_password(user.user_id, request.new_password)
        
        if success:
            return {
                "success": True, 
                "message": "パスワードが再設定されました。新しいパスワードでログインしてください。"
            }
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        logging.error(f"パスワード再設定エラー: {e}")
        raise HTTPException(status_code=500, detail=f"パスワード再設定に失敗しました: {str(e)}")

@app.delete("/api/auth/account")
async def deactivate_account(session_id: str):
    """アカウント無効化"""
    try:
        user = user_manager.get_user_by_session(session_id)
        if not user:
            raise HTTPException(status_code=401, detail="セッションが無効です")
        
        success, message = user_manager.deactivate_user(user.user_id)
        
        if success:
            return {"success": True, "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        logging.error(f"アカウント無効化エラー: {e}")
        raise HTTPException(status_code=500, detail=f"アカウント無効化に失敗しました: {str(e)}")

# チャット関連エンドポイント
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, model_instance=Depends(get_model)):
    """テキストチャット"""
    try:
        session = get_session(request.session_id)
        start_time = datetime.now()
        
        # アクティブキャラクターのシステムプロンプトを適用
        enhanced_history = session["conversation_history"].copy()
        if request.character_id and request.character_id != "default":
            # ユーザーIDが提供されている場合はユーザー別キャラクターを取得
            if hasattr(request, 'user_id') and request.user_id:
                user_manager = get_or_create_user_manager(request.user_id)
                character = user_manager.get_character_by_id(request.character_id)
                if character:
                    system_prompt = character.build_system_prompt()
                    enhanced_history = [f"System: {system_prompt}"] + enhanced_history
                    session["character_id"] = request.character_id
        
        # AI応答生成
        response = generate_response(model_instance, request.message, enhanced_history)
        response_text = response.text.strip()
        
        # トークン数の推定（簡易版）
        estimated_tokens = len(request.message.split()) + len(response_text.split())
        
        # セッション情報の更新
        session["conversation_history"].append(f"User: {request.message}")
        session["conversation_history"].append(f"Assistant: {response_text}")
        session["total_tokens"] += estimated_tokens
        session["message_count"] += 1
        
        # 応答時間の計算
        response_time = (datetime.now() - start_time).total_seconds()
        
        # 応答時間を記録
        # response_time_manager.add_response_time(response_time)  # 削除されたためコメントアウト
        
        # トークン使用量を記録
        if request.session_id not in token_usage_data:
            token_usage_data[request.session_id] = []
        token_usage_data[request.session_id].append({
            "date": datetime.now().isoformat(),
            "tokens": estimated_tokens
        })
        
        return ChatResponse(
            session_id=request.session_id,
            response=response_text,
            tokens_used=estimated_tokens,
            response_time=response_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logging.error(f"チャット処理エラー: {e}")
        raise HTTPException(status_code=500, detail=f"チャット処理中にエラーが発生しました: {str(e)}")

@app.post("/api/chat/image", response_model=ChatResponse)
async def chat_with_image(
    session_id: str,
    message: str,
    character_id: Optional[str] = None,
    image: UploadFile = File(...),
    model_instance=Depends(get_model)
):
    """画像付きチャット"""
    try:
        session = get_session(session_id)
        start_time = datetime.now()
        
        # 画像を一時ファイルとして保存（ローカルディレクトリに保存）
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_image_path = os.path.join(temp_dir, f"temp_{uuid.uuid4().hex}.{image.filename.split('.')[-1]}")
        with open(temp_image_path, "wb") as buffer:
            content = await image.read()
            buffer.write(content)
        
        try:
            # アクティブキャラクターのシステムプロンプトを適用
            enhanced_history = session["conversation_history"].copy()
            if character_id:
                character = custom_gpt_manager.get_character_by_id(character_id)
                if character:
                    system_prompt = character.build_system_prompt()
                    enhanced_history = [f"System: {system_prompt}"] + enhanced_history
                    session["character_id"] = character_id
            
            # 画像認識応答生成
            response, success, error_message = generate_image_response(
                model_instance, message, temp_image_path, enhanced_history
            )
            
            if not success:
                raise HTTPException(status_code=400, detail=error_message)
            
            response_text = response.text.strip()
            
            # トークン数の推定（画像は258トークンとして計算）
            estimated_tokens = len(message.split()) + len(response_text.split()) + 258
            
            # セッション情報の更新
            session["conversation_history"].append(f"User: {message} [画像付き]")
            session["conversation_history"].append(f"Assistant: {response_text}")
            session["total_tokens"] += estimated_tokens
            session["message_count"] += 1
            
            # 応答時間の計算
            response_time = (datetime.now() - start_time).total_seconds()
            
            # 応答時間を記録
            # response_time_manager.add_response_time(response_time)  # 削除されたためコメントアウト
            
            # トークン使用量を記録
            if session_id not in token_usage_data:
                token_usage_data[session_id] = []
            token_usage_data[session_id].append({
                "date": datetime.now().isoformat(),
                "tokens": estimated_tokens
            })
            
            return ChatResponse(
                session_id=session_id,
                response=response_text,
                tokens_used=estimated_tokens,
                response_time=response_time,
                timestamp=datetime.now().isoformat()
            )
            
        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
        
    except Exception as e:
        logging.error(f"画像チャット処理エラー: {e}")
        raise HTTPException(status_code=500, detail=f"画像チャット処理中にエラーが発生しました: {str(e)}")

# セッション管理エンドポイント
@app.get("/api/sessions", response_model=List[SessionInfo])
async def get_sessions():
    """セッション一覧を取得"""
    sessions = []
    for session_id, data in conversation_sessions.items():
        sessions.append(SessionInfo(
            session_id=session_id,
            created_at=data["created_at"],
            message_count=data["message_count"],
            total_tokens=data["total_tokens"],
            character_id=data["character_id"]
        ))
    return sessions

@app.get("/api/sessions/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """特定のセッション情報を取得"""
    if session_id not in conversation_sessions:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    data = conversation_sessions[session_id]
    return SessionInfo(
        session_id=session_id,
        created_at=data["created_at"],
        message_count=data["message_count"],
        total_tokens=data["total_tokens"],
        character_id=data["character_id"]
    )

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """セッションを削除"""
    if session_id not in conversation_sessions:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    del conversation_sessions[session_id]
    if session_id in token_usage_data:
        del token_usage_data[session_id]
    
    return {"message": "セッションが削除されました"}

@app.get("/api/sessions/{session_id}/history")
async def get_conversation_history(session_id: str):
    """会話履歴を取得"""
    if session_id not in conversation_sessions:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    return {
        "session_id": session_id,
        "history": conversation_sessions[session_id]["conversation_history"]
    }

# ユーザー管理
user_character_managers = {}  # ユーザーID -> CustomGPTManager

def get_or_create_user_manager(user_id: str):
    """ユーザー用のキャラクターマネージャーを取得または作成"""
    if user_id not in user_character_managers:
        from custom_gpt_manager import CustomGPTManager
        # ユーザー別フォルダー構造を使用
        user_manager = CustomGPTManager(user_id=user_id)
        user_character_managers[user_id] = user_manager
    return user_character_managers[user_id]

# カスタムGPTキャラクター管理エンドポイント
@app.get("/api/characters")
async def get_characters(user_id: str = None):
    """ユーザー別キャラクター一覧を取得"""
    if not user_id:
        # デフォルトキャラクターのみ返す
        return {"characters": [{
            "id": "default",
            "name": "AI_takashi",
            "description": "デフォルトキャラクター",
            "system_prompt": "あなたはAI_takashiです。",
            "is_active": True,
            "personality": "優しくて知識豊富なAIアシスタント",
            "speaking_style": "丁寧で親しみやすい",
            "specialization": "一般的な質問への回答"
        }]}
    
    # ユーザー別のキャラクターマネージャーを取得
    user_manager = get_or_create_user_manager(user_id)
    
    characters = []
    for character in user_manager.characters:
        characters.append({
            "id": character.character_id,
            "name": character.name,
            "description": character.personality or character.specialization or "カスタムキャラクター",
            "system_prompt": character.build_system_prompt(),
            "is_active": getattr(character, 'is_active', False),
            "personality": character.personality,
            "speaking_style": character.speaking_style,
            "specialization": character.specialization
        })
    return {"characters": characters}

@app.get("/api/characters/{character_id}")
async def get_character(character_id: str, user_id: str = None):
    """ユーザー別の特定キャラクター情報を取得"""
    if character_id == "default":
        return {
            "id": "default",
            "name": "AI_takashi",
            "description": "デフォルトキャラクター",
            "system_prompt": "あなたはAI_takashiです。",
            "personality": "優しくて知識豊富なAIアシスタント",
            "speaking_style": "丁寧で親しみやすい",
            "specialization": "一般的な質問への回答",
            "response_style": "分かりやすく丁寧に",
            "background": "AIアシスタントとして設計された",
            "catchphrase": "質問あるかね？",
            "greeting": "こんにちは！AI_takashiです。"
        }
    
    if not user_id:
        raise HTTPException(status_code=400, detail="ユーザーIDが必要です")
    
    # ユーザー別のキャラクターマネージャーを取得
    user_manager = get_or_create_user_manager(user_id)
    
    character = user_manager.get_character_by_id(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")
    
    return {
        "id": character.character_id,
        "name": character.name,
        "description": character.personality or character.specialization or "カスタムキャラクター",
        "system_prompt": character.build_system_prompt(),
        "is_active": getattr(character, 'is_active', False),
        "personality": character.personality,
        "speaking_style": character.speaking_style,
        "specialization": character.specialization
    }

@app.post("/api/characters")
async def create_character(character_data: dict, user_id: str = None):
    """ユーザー別にキャラクターを作成"""
    if not user_id:
        raise HTTPException(status_code=400, detail="ユーザーIDが必要です")
    
    # ユーザー別のキャラクターマネージャーを取得
    user_manager = get_or_create_user_manager(user_id)
    
    try:
        # キャラクターを作成
        character_id = user_manager.create_character(
            name=character_data["name"],
            personality=character_data.get("personality", ""),
            speaking_style=character_data.get("speaking_style", ""),
            specialization=character_data.get("specialization", ""),
            response_style=character_data.get("response_style", ""),
            background=character_data.get("background", ""),
            catchphrase=character_data.get("catchphrase", ""),
            greeting=character_data.get("greeting", "")
        )
        
        # キャラクターを保存
        user_manager.save_characters()
        
        return {
            "message": f"キャラクター「{character_data['name']}」を作成しました",
            "character_id": character_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"キャラクター作成エラー: {str(e)}")

@app.post("/api/characters/{character_id}/activate")
async def activate_character(character_id: str):
    """キャラクターをアクティブにする"""
    character = custom_gpt_manager.get_character_by_id(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")
    
    custom_gpt_manager.set_active_character(character_id)
    return {"message": f"キャラクター '{character.name}' がアクティブになりました"}

# トークン使用量管理エンドポイント
@app.get("/api/tokens/usage", response_model=TokenUsageStats)
async def get_token_usage():
    """トークン使用統計を取得"""
    total_tokens = sum(
        sum(entry["tokens"] for entry in entries)
        for entries in token_usage_data.values()
    )
    
    # 日別使用量の集計
    daily_usage = {}
    for session_data in token_usage_data.values():
        for entry in session_data:
            date = entry["date"][:10]  # YYYY-MM-DD形式
            if date not in daily_usage:
                daily_usage[date] = 0
            daily_usage[date] += entry["tokens"]
    
    daily_usage_list = [
        {"date": date, "tokens": tokens}
        for date, tokens in daily_usage.items()
    ]
    
    return TokenUsageStats(
        total_tokens=total_tokens,
        daily_usage=daily_usage_list,
        monthly_reset_date=datetime.now().isoformat(),
        warning_threshold=10000  # デフォルト値
    )

# メモリ管理エンドポイント
@app.get("/api/memories", response_model=List[MemoryEntry])
async def get_memories(user_id: Optional[str] = None):
    """メモリ一覧を取得"""
    if user_id:
        # ユーザー別の記憶マネージャーを使用
        user_memory_manager = get_or_create_user_memory_manager(user_id)
        memories = user_memory_manager.get_all_memories()
    else:
        # デフォルトの記憶マネージャーを使用
        memories = memory_manager.get_all_memories()
    
    return [
        MemoryEntry(
            id=memory.memory_id,
            title=memory.title,
            content=memory.content,
            category=memory.category,
            tags=memory.tags,
            importance=memory.importance,
            created_at=memory.created_at,
            character_id=memory.character_id
        )
        for memory in memories
    ]

@app.post("/api/memories", response_model=MemoryEntry)
async def create_memory(request: Request):
    """新しいメモリを作成"""
    try:
        # リクエストボディからデータを取得
        memory_data = await request.json()
        
        # クエリパラメータからuser_idを取得
        user_id = request.query_params.get("user_id")
        
        if user_id:
            # ユーザー別の記憶マネージャーを使用
            user_memory_manager = get_or_create_user_memory_manager(user_id)
            memory_id = user_memory_manager.add_memory(
                title=memory_data["title"],
                content=memory_data["content"],
                character_id=memory_data.get("character_id", "AI_takashi"),
                character_name=memory_data.get("character_name", "AI_takashi"),
                conversation_history=memory_data.get("conversation_history", []),
                category=memory_data.get("category", "その他"),
                tags=memory_data.get("tags", []),
                importance=memory_data.get("importance", "中"),
                user_id=user_id
            )
            
            if memory_id:
                memory = user_memory_manager.get_memory(memory_id)
                return MemoryEntry(
                    id=memory.memory_id,
                    title=memory.title,
                    content=memory.content,
                    category=memory.category,
                    tags=memory.tags,
                    importance=memory.importance,
                    created_at=memory.created_at,
                    character_id=memory.character_id
                )
        else:
            # デフォルトの記憶マネージャーを使用（後方互換性）
            memory_id = str(uuid.uuid4())
            memory_entry = {
                "id": memory_id,
                "title": memory_data["title"],
                "content": memory_data["content"],
                "category": memory_data.get("category", "その他"),
                "tags": memory_data.get("tags", []),
                "importance": memory_data.get("importance", "中"),
                "created_at": datetime.now().isoformat(),
                "character_id": memory_data.get("character_id", "AI_takashi"),
                "conversation_history": memory_data.get("conversation_history", [])
            }
            
            memory_manager.save_memory(memory_entry)
            
            return MemoryEntry(
                id=memory_entry["id"],
                title=memory_entry["title"],
                content=memory_entry["content"],
                category=memory_entry["category"],
                tags=memory_entry["tags"],
                importance=memory_entry["importance"],
                created_at=memory_entry["created_at"],
                character_id=memory_entry["character_id"]
            )
    
    except Exception as e:
        logging.error(f"メモリ作成エラー: {e}")
        raise HTTPException(status_code=500, detail=f"メモリ作成エラー: {str(e)}")

@app.get("/api/memories/{memory_id}", response_model=MemoryEntry)
async def get_memory(request: Request, memory_id: str):
    """個別メモリの詳細を取得"""
    try:
        # クエリパラメータからuser_idを取得
        user_id = request.query_params.get("user_id")
        
        if user_id:
            # ユーザー別の記憶マネージャーを使用
            user_memory_manager = get_or_create_user_memory_manager(user_id)
            memory = user_memory_manager.get_memory(memory_id)
        else:
            # デフォルトの記憶マネージャーを使用
            memory = memory_manager.get_memory(memory_id)
        
        if memory:
            return MemoryEntry(
                id=memory.memory_id,
                title=memory.title,
                content=memory.content,
                category=memory.category,
                tags=memory.tags,
                importance=memory.importance,
                created_at=memory.created_at,
                character_id=memory.character_id
            )
        else:
            raise HTTPException(status_code=404, detail="メモリが見つかりません")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"メモリ取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"メモリ取得エラー: {str(e)}")

@app.delete("/api/memories/{memory_id}")
async def delete_memory(request: Request, memory_id: str):
    """メモリを削除"""
    try:
        # クエリパラメータからuser_idを取得
        user_id = request.query_params.get("user_id")
        
        if user_id:
            # ユーザー別の記憶マネージャーを使用
            user_memory_manager = get_or_create_user_memory_manager(user_id)
            success = user_memory_manager.delete_memory(memory_id)
        else:
            # デフォルトの記憶マネージャーを使用
            # 後方互換性のため、簡単な実装
            success = True
        
        if success:
            return {"message": "メモリを削除しました", "success": True}
        else:
            return {"message": "メモリが見つかりません", "success": False}
    except Exception as e:
        logging.error(f"メモリ削除エラー: {e}")
        return {"message": f"メモリ削除エラー: {str(e)}", "success": False}

# メイン実行
if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

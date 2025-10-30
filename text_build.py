import os
import dotenv
import google.generativeai as genai
from security_utils import get_secure_api_key
import base64
import mimetypes
from PIL import Image, ImageOps
import io
import logging

# .envファイルから環境変数を読み込む
dotenv.load_dotenv()

# Google APIキーを取得する関数
def get_google_api_key():
    """
    Google APIキーを取得する
    
    優先順位:
    1. 暗号化された設定ファイルから取得
    2. 環境変数から取得
    
    Returns:
        str: APIキー、取得できない場合はNone
    """
    try:
        # セキュアなAPIキー取得を試行
        api_key = get_secure_api_key()
        if api_key:
            return api_key
        
        # フォールバック: 環境変数から取得
        env_key = os.getenv("GOOGLE_API_KEY")
        if env_key:
            logging.info("環境変数からAPIキーを取得しました")
        else:
            logging.warning("APIキーが設定されていません")
        return env_key
    except Exception as e:
        logging.error(f"APIキー取得エラー: {e}", exc_info=True)
        # 最後のフォールバック
        return os.getenv("GOOGLE_API_KEY")

# AIモデルを設定する関数
def configure_api(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.5-flash")  

# 画像ファイルを読み込んでBase64エンコードする関数
def encode_image_to_base64(image_path):
    """
    画像ファイルをBase64エンコードして返す
    
    Args:
        image_path (str): 画像ファイルのパス
    
    Returns:
        tuple: (base64_string, mime_type) または (None, None) if エラー
    """
    try:
        # ファイルの存在確認
        if not os.path.exists(image_path):
            logging.error(f"画像ファイルが見つかりません: {image_path}")
            return None, None
        
        # MIME タイプの取得
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith('image/'):
            logging.error(f"サポートされていないファイル形式: {image_path}")
            return None, None
        
        # 画像の読み込みと最適化
        with Image.open(image_path) as img:
            # 画像の向きを修正
            img = ImageOps.exif_transpose(img)
            
            # 画像サイズの最適化（3072x3072以下にリサイズ）
            max_size = 3072
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                logging.info(f"画像をリサイズしました: {image_path}")
            
            # 画像をバイトストリームに変換
            img_byte_arr = io.BytesIO()
            img_format = img.format or 'JPEG'
            img.save(img_byte_arr, format=img_format, quality=85, optimize=True)
            img_byte_arr.seek(0)
            
            # Base64エンコード
            base64_string = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            
            logging.info(f"画像を正常にエンコードしました: {image_path}")
            return base64_string, mime_type
            
    except Exception as e:
        logging.error(f"画像エンコードエラー: {e}")
        return None, None

# 画像サイズとファイル情報を検証する関数
def validate_image_file(image_path):
    """
    画像ファイルの妥当性を検証する
    
    Args:
        image_path (str): 画像ファイルのパス
    
    Returns:
        dict: 検証結果の辞書
    """
    result = {
        "valid": False,
        "error_message": "",
        "file_size": 0,
        "image_size": (0, 0),
        "format": ""
    }
    
    try:
        # ファイルサイズチェック（20MB制限）
        file_size = os.path.getsize(image_path)
        result["file_size"] = file_size
        
        if file_size > 20 * 1024 * 1024:  # 20MB
            result["error_message"] = "ファイルサイズが20MBを超えています"
            return result
        
        # 画像の読み込みと検証
        with Image.open(image_path) as img:
            result["image_size"] = img.size
            result["format"] = img.format
            
            # 対応形式の確認
            supported_formats = ['JPEG', 'PNG', 'GIF', 'WEBP']
            if img.format not in supported_formats:
                result["error_message"] = f"サポートされていない形式: {img.format}"
                return result
            
            # 解像度チェック（8192x8192制限）
            max_resolution = 8192
            if img.width > max_resolution or img.height > max_resolution:
                result["error_message"] = f"解像度が{max_resolution}x{max_resolution}を超えています"
                return result
            
            result["valid"] = True
            logging.info(f"画像検証成功: {image_path}")
            
    except Exception as e:
        result["error_message"] = f"画像検証エラー: {str(e)}"
        logging.error(f"画像検証エラー: {e}")
    
    return result

# 画像認識用の応答生成関数
def generate_image_response(model, user_input, image_path, conversation_history):
    """
    画像とテキストを組み合わせた応答を生成する
    
    Args:
        model: Gemini モデル
        user_input (str): ユーザーの質問
        image_path (str): 画像ファイルのパス
        conversation_history (list): 会話履歴
    
    Returns:
        tuple: (response, success, error_message)
    """
    try:
        # 画像の検証
        validation_result = validate_image_file(image_path)
        if not validation_result["valid"]:
            return None, False, validation_result["error_message"]
        
        # 画像をBase64エンコード
        base64_image, mime_type = encode_image_to_base64(image_path)
        if not base64_image:
            return None, False, "画像の読み込みに失敗しました"
        
        # 会話履歴を含めた入力の準備
        context = "\n".join(conversation_history) if conversation_history else ""
        
        # 画像とテキストを組み合わせたプロンプト
        if context:
            full_prompt = f"{context}\n\nUser: {user_input}\n\n[画像が添付されています]"
        else:
            full_prompt = f"User: {user_input}\n\n[画像が添付されています]"
        
        # Gemini APIに送信するためのパート作成
        image_part = {
            "mime_type": mime_type,
            "data": base64_image
        }
        
        # APIに送信
        response = model.generate_content([full_prompt, image_part])
        
        logging.info(f"画像認識応答を生成しました: {image_path}")
        return response, True, ""
        
    except Exception as e:
        error_message = f"画像認識エラー: {str(e)}"
        logging.error(error_message)
        return None, False, error_message

# 質問を生成する関数（既存）
def generate_response(model, user_input, conversation_history):
    full_input = "\n".join(conversation_history + [f"User: {user_input}"])
    response = model.generate_content(full_input)
    return response  #  <.text.strip() を削除>

# 画像認識機能が利用可能かチェックする関数
def check_image_recognition_available():
    """
    画像認識機能が利用可能かチェックする
    
    Returns:
        bool: 利用可能かどうか
    """
    try:
        # 必要なライブラリの確認
        import PIL
        import base64
        import mimetypes
        
        # APIキーの確認
        api_key = get_google_api_key()
        if not api_key:
            return False
        
        logging.info("画像認識機能が利用可能です")
        return True
        
    except ImportError as e:
        logging.error(f"必要なライブラリがインストールされていません: {e}")
        return False
    except Exception as e:
        logging.error(f"画像認識機能チェックエラー: {e}")
        return False

# 対応している画像形式を取得する関数
def get_supported_image_formats():
    """
    対応している画像形式のリストを返す
    
    Returns:
        list: 対応形式のリスト
    """
    return [
        {"format": "JPEG", "extensions": [".jpg", ".jpeg"], "mime_type": "image/jpeg"},
        {"format": "PNG", "extensions": [".png"], "mime_type": "image/png"},
        {"format": "GIF", "extensions": [".gif"], "mime_type": "image/gif"},
        {"format": "WEBP", "extensions": [".webp"], "mime_type": "image/webp"}
    ]








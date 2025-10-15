import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re

# PDF生成のためのライブラリ（オプション）
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_LEFT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("reportlabが利用できません。PDF出力機能が無効になります。")

class ConversationEntry:
    """会話エントリー"""
    
    def __init__(self, user_text: str, ai_text: str, timestamp: datetime = None):
        self.user_text = user_text
        self.ai_text = ai_text
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            'user_text': self.user_text,
            'ai_text': self.ai_text,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationEntry':
        """辞書からインスタンスを作成"""
        return cls(
            user_text=data['user_text'],
            ai_text=data['ai_text'],
            timestamp=datetime.fromisoformat(data['timestamp'])
        )

class ExportManager:
    """エクスポート管理クラス"""
    
    def __init__(self):
        self.conversation_history = []
    
    def parse_conversation_history(self, conversation_history: List[str]) -> List[ConversationEntry]:
        """会話履歴を解析してConversationEntryのリストに変換"""
        entries = []
        user_text = ""
        ai_text = ""
        
        for line in conversation_history:
            if line.startswith("User: "):
                if user_text and ai_text:
                    # 前の会話を保存
                    entries.append(ConversationEntry(user_text, ai_text))
                user_text = line[6:]  # "User: "を削除
                ai_text = ""
            elif line.startswith("AI_takashi: "):
                ai_text = line[12:]  # "AI_takashi: "を削除
        
        # 最後の会話を保存
        if user_text and ai_text:
            entries.append(ConversationEntry(user_text, ai_text))
        
        return entries
    
    def filter_by_date_range(self, entries: List[ConversationEntry], 
                           start_date: datetime = None, 
                           end_date: datetime = None) -> List[ConversationEntry]:
        """日付範囲でフィルタリング"""
        filtered_entries = []
        
        for entry in entries:
            include_entry = True
            
            if start_date and entry.timestamp < start_date:
                include_entry = False
            
            if end_date and entry.timestamp > end_date:
                include_entry = False
            
            if include_entry:
                filtered_entries.append(entry)
        
        return filtered_entries
    
    def export_to_txt(self, entries: List[ConversationEntry], file_path: str) -> bool:
        """テキストファイルにエクスポート"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # ヘッダー情報
                f.write("=" * 50 + "\n")
                f.write("AI_takashi 会話履歴エクスポート\n")
                f.write(f"エクスポート日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
                f.write(f"会話数: {len(entries)}件\n")
                f.write("=" * 50 + "\n\n")
                
                # 会話内容
                for i, entry in enumerate(entries, 1):
                    f.write(f"【会話 {i}】\n")
                    f.write(f"日時: {entry.timestamp.strftime('%Y年%m月%d日 %H:%M:%S')}\n")
                    f.write("-" * 30 + "\n")
                    f.write(f"ユーザー: {entry.user_text}\n\n")
                    f.write(f"AI_takashi: {entry.ai_text}\n")
                    f.write("=" * 50 + "\n\n")
                
                # フッター情報
                f.write(f"総会話数: {len(entries)}件\n")
                if entries:
                    f.write(f"期間: {entries[0].timestamp.strftime('%Y年%m月%d日')} ～ {entries[-1].timestamp.strftime('%Y年%m月%d日')}\n")
            
            logging.info(f"テキストファイルにエクスポート完了: {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"テキストファイルエクスポートエラー: {e}")
            return False
    
    def export_to_pdf(self, entries: List[ConversationEntry], file_path: str) -> bool:
        """PDFファイルにエクスポート"""
        if not PDF_AVAILABLE:
            logging.error("reportlabが利用できないため、PDF出力ができません")
            return False
        
        try:
            # PDF文書を作成
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            story = []
            
            # スタイルを取得
            styles = getSampleStyleSheet()
            
            # 日本語フォントの設定（システムフォントを試行）
            try:
                # Windows日本語フォントを試行
                font_paths = [
                    "C:/Windows/Fonts/msgothic.ttc",
                    "C:/Windows/Fonts/meiryo.ttc",
                    "C:/Windows/Fonts/BIZ-UDGothicR.ttc"
                ]
                
                font_registered = False
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        try:
                            pdfmetrics.registerFont(TTFont('Japanese', font_path))
                            font_registered = True
                            break
                        except:
                            continue
                
                if font_registered:
                    # 日本語対応スタイルを作成
                    title_style = ParagraphStyle(
                        'CustomTitle',
                        parent=styles['Title'],
                        fontName='Japanese',
                        fontSize=16,
                        alignment=TA_LEFT
                    )
                    
                    normal_style = ParagraphStyle(
                        'CustomNormal',
                        parent=styles['Normal'],
                        fontName='Japanese',
                        fontSize=10,
                        alignment=TA_LEFT
                    )
                else:
                    # フォールバック: デフォルトフォント
                    title_style = styles['Title']
                    normal_style = styles['Normal']
                
            except Exception as e:
                logging.warning(f"日本語フォント設定に失敗: {e}")
                title_style = styles['Title']
                normal_style = styles['Normal']
            
            # タイトル
            title = Paragraph("AI_takashi 会話履歴エクスポート", title_style)
            story.append(title)
            story.append(Spacer(1, 12))
            
            # ヘッダー情報
            header_info = f"""
            エクスポート日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}<br/>
            会話数: {len(entries)}件<br/>
            """
            
            if entries:
                header_info += f"期間: {entries[0].timestamp.strftime('%Y年%m月%d日')} ～ {entries[-1].timestamp.strftime('%Y年%m月%d日')}<br/>"
            
            header = Paragraph(header_info, normal_style)
            story.append(header)
            story.append(Spacer(1, 20))
            
            # 会話内容
            for i, entry in enumerate(entries, 1):
                # 会話番号と日時
                conv_header = f"【会話 {i}】 {entry.timestamp.strftime('%Y年%m月%d日 %H:%M:%S')}"
                story.append(Paragraph(conv_header, title_style))
                story.append(Spacer(1, 6))
                
                # ユーザーの発言
                user_text = f"<b>ユーザー:</b> {self._escape_html(entry.user_text)}"
                story.append(Paragraph(user_text, normal_style))
                story.append(Spacer(1, 6))
                
                # AIの発言
                ai_text = f"<b>AI_takashi:</b> {self._escape_html(entry.ai_text)}"
                story.append(Paragraph(ai_text, normal_style))
                story.append(Spacer(1, 12))
            
            # PDF生成
            doc.build(story)
            
            logging.info(f"PDFファイルにエクスポート完了: {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"PDFファイルエクスポートエラー: {e}")
            return False
    
    def _escape_html(self, text: str) -> str:
        """HTML特殊文字をエスケープ"""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))
    
    def export_to_json(self, entries: List[ConversationEntry], file_path: str) -> bool:
        """JSON形式でエクスポート"""
        try:
            export_data = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'total_conversations': len(entries),
                    'date_range': {
                        'start': entries[0].timestamp.isoformat() if entries else None,
                        'end': entries[-1].timestamp.isoformat() if entries else None
                    }
                },
                'conversations': [entry.to_dict() for entry in entries]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"JSONファイルにエクスポート完了: {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"JSONファイルエクスポートエラー: {e}")
            return False
    
    def get_conversation_stats(self, entries: List[ConversationEntry]) -> Dict:
        """会話統計を取得"""
        if not entries:
            return {
                'total_conversations': 0,
                'date_range': None,
                'avg_user_length': 0,
                'avg_ai_length': 0,
                'total_characters': 0
            }
        
        # 統計計算
        total_conversations = len(entries)
        
        user_lengths = [len(entry.user_text) for entry in entries]
        ai_lengths = [len(entry.ai_text) for entry in entries]
        
        avg_user_length = sum(user_lengths) / len(user_lengths)
        avg_ai_length = sum(ai_lengths) / len(ai_lengths)
        total_characters = sum(user_lengths) + sum(ai_lengths)
        
        date_range = {
            'start': min(entry.timestamp for entry in entries),
            'end': max(entry.timestamp for entry in entries)
        }
        
        return {
            'total_conversations': total_conversations,
            'date_range': date_range,
            'avg_user_length': avg_user_length,
            'avg_ai_length': avg_ai_length,
            'total_characters': total_characters
        }

# グローバルエクスポートマネージャーインスタンス
export_manager = ExportManager() 
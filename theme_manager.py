import json
import logging
import os
from typing import Dict, Optional
from pathlib import Path

class ThemeManager:
    """テーマ管理クラス"""
    
    def __init__(self, theme_file: str = None):
        if theme_file is None:
            # ユーザーのホームディレクトリに設定ファイルを作成
            home_dir = Path.home()
            ai_config_dir = home_dir / ".ai_takashi_config"
            ai_config_dir.mkdir(exist_ok=True)
            theme_file = ai_config_dir / "theme_settings.json"
        self.theme_file = str(theme_file)
        self.current_theme = "light"  # デフォルトはライトモード
        
        # テーマ定義
        self.themes = {
            "light": self._create_light_theme(),
            "dark": self._create_dark_theme()
        }
        
        self.load_theme_settings()
    
    def _create_light_theme(self) -> Dict[str, str]:
        """ライトテーマを作成"""
        return {
            # 基本色
            "background_color": "#ffffff",
            "text_color": "#000000",
            "border_color": "#cccccc",
            "selection_color": "#0078d4",
            "selection_background": "#e6f3ff",
            
            # ボタン
            "button_background": "#f0f0f0",
            "button_hover": "#e0e0e0",
            "button_pressed": "#d0d0d0",
            "button_text": "#000000",
            
            # 入力フィールド
            "input_background": "#ffffff",
            "input_border": "#cccccc",
            "input_focus_border": "#0078d4",
            "input_text": "#000000",
            
            # メニュー・タブ
            "menu_background": "#f8f8f8",
            "menu_text": "#000000",
            "menu_hover": "#e0e0e0",
            "tab_background": "#f0f0f0",
            "tab_active": "#ffffff",
            "tab_text": "#000000",
            
            # プログレスバー
            "progress_background": "#f0f0f0",
            "progress_chunk": "#0078d4",
            
            # スクロールバー
            "scrollbar_background": "#f0f0f0",
            "scrollbar_handle": "#c0c0c0",
            "scrollbar_hover": "#a0a0a0",
            
            # テーブル
            "table_background": "#ffffff",
            "table_alternate": "#f8f8f8",
            "table_header": "#e8e8e8",
            "table_grid": "#cccccc",
            "table_text": "#000000",
            
            # ダイアログ
            "dialog_background": "#ffffff",
            "dialog_border": "#cccccc",
            "dialog_text": "#000000",
            
            # 状態色
            "success_color": "#28a745",
            "warning_color": "#ffc107",
            "error_color": "#dc3545",
            "info_color": "#17a2b8",
            
            # 透明度
            "disabled_opacity": "0.6",
            "hover_opacity": "0.8"
        }
    
    def _create_dark_theme(self) -> Dict[str, str]:
        """ダークテーマを作成"""
        return {
            # 基本色
            "background_color": "#2d2d2d",
            "text_color": "#ffffff",
            "border_color": "#555555",
            "selection_color": "#0078d4",
            "selection_background": "#404040",
            
            # ボタン
            "button_background": "#404040",
            "button_hover": "#505050",
            "button_pressed": "#606060",
            "button_text": "#ffffff",
            
            # 入力フィールド
            "input_background": "#3c3c3c",
            "input_border": "#555555",
            "input_focus_border": "#0078d4",
            "input_text": "#ffffff",
            
            # メニュー・タブ
            "menu_background": "#353535",
            "menu_text": "#ffffff",
            "menu_hover": "#505050",
            "tab_background": "#404040",
            "tab_active": "#2d2d2d",
            "tab_text": "#ffffff",
            
            # プログレスバー
            "progress_background": "#404040",
            "progress_chunk": "#0078d4",
            
            # スクロールバー
            "scrollbar_background": "#404040",
            "scrollbar_handle": "#606060",
            "scrollbar_hover": "#707070",
            
            # テーブル
            "table_background": "#2d2d2d",
            "table_alternate": "#363636",
            "table_header": "#404040",
            "table_grid": "#555555",
            "table_text": "#ffffff",
            
            # ダイアログ
            "dialog_background": "#2d2d2d",
            "dialog_border": "#555555",
            "dialog_text": "#ffffff",
            
            # 状態色
            "success_color": "#28a745",
            "warning_color": "#ffc107",
            "error_color": "#dc3545",
            "info_color": "#17a2b8",
            
            # 透明度
            "disabled_opacity": "0.6",
            "hover_opacity": "0.8"
        }
    
    def load_theme_settings(self):
        """テーマ設定を読み込み"""
        try:
            if os.path.exists(self.theme_file):
                with open(self.theme_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.current_theme = settings.get('current_theme', 'light')
                logging.info(f"テーマ設定を読み込みました: {self.current_theme}")
            else:
                logging.info("新しいテーマ設定ファイルを作成します")
                self.save_theme_settings()
        except PermissionError as e:
            logging.warning(f"権限エラーでテーマ設定を読み込めません: {e}")
            self.current_theme = 'light'
        except Exception as e:
            logging.error(f"テーマ設定読み込みエラー: {e}")
            self.current_theme = 'light'
    
    def save_theme_settings(self):
        """テーマ設定を保存"""
        try:
            settings = {
                'current_theme': self.current_theme
            }
            with open(self.theme_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            logging.info(f"テーマ設定を保存しました: {self.current_theme}")
        except PermissionError as e:
            logging.warning(f"権限エラーでテーマ設定を保存できません: {e}")
        except Exception as e:
            logging.error(f"テーマ設定保存エラー: {e}")
    
    def set_theme(self, theme_name: str) -> bool:
        """テーマを設定"""
        if theme_name not in self.themes:
            logging.error(f"未知のテーマ: {theme_name}")
            return False
        
        self.current_theme = theme_name
        self.save_theme_settings()
        logging.info(f"テーマを変更しました: {theme_name}")
        return True
    
    def get_current_theme(self) -> str:
        """現在のテーマ名を取得"""
        return self.current_theme
    
    def get_theme_colors(self, theme_name: Optional[str] = None) -> Dict[str, str]:
        """テーマの色設定を取得"""
        theme = theme_name or self.current_theme
        return self.themes.get(theme, self.themes['light']).copy()
    
    def toggle_theme(self) -> str:
        """テーマを切り替え"""
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.set_theme(new_theme)
        return new_theme
    
    def is_dark_mode(self) -> bool:
        """ダークモードかどうかを判定"""
        return self.current_theme == "dark"
    
    def generate_stylesheet(self, theme_name: Optional[str] = None) -> str:
        """テーマに基づいたスタイルシートを生成"""
        colors = self.get_theme_colors(theme_name)
        
        stylesheet = f"""
        /* メインウィンドウ */
        QMainWindow {{
            background-color: {colors['background_color']};
            color: {colors['text_color']};
        }}
        
        /* 基本ウィジェット */
        QWidget {{
            background-color: {colors['background_color']};
            color: {colors['text_color']};
            border: 1px solid {colors['border_color']};
        }}
        
        /* ラベル */
        QLabel {{
            background-color: transparent;
            border: none;
            color: {colors['text_color']};
        }}
        
        /* ボタン */
        QPushButton {{
            background-color: {colors['button_background']};
            border: 1px solid {colors['border_color']};
            color: {colors['button_text']};
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: normal;
        }}
        
        QPushButton:hover {{
            background-color: {colors['button_hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {colors['button_pressed']};
        }}
        
        QPushButton:disabled {{
            opacity: {colors['disabled_opacity']};
        }}
        
        /* テキスト入力 */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {colors['input_background']};
            border: 1px solid {colors['input_border']};
            color: {colors['input_text']};
            padding: 4px;
            border-radius: 3px;
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 2px solid {colors['input_focus_border']};
        }}
        
        /* コンボボックス */
        QComboBox {{
            background-color: {colors['input_background']};
            border: 1px solid {colors['input_border']};
            color: {colors['input_text']};
            padding: 4px 8px;
            border-radius: 3px;
        }}
        
        QComboBox:focus {{
            border: 2px solid {colors['input_focus_border']};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {colors['text_color']};
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {colors['input_background']};
            border: 1px solid {colors['border_color']};
            color: {colors['input_text']};
            selection-background-color: {colors['selection_background']};
        }}
        
        /* スピンボックス */
        QSpinBox, QDoubleSpinBox {{
            background-color: {colors['input_background']};
            border: 1px solid {colors['input_border']};
            color: {colors['input_text']};
            padding: 4px;
            border-radius: 3px;
        }}
        
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 2px solid {colors['input_focus_border']};
        }}
        
        /* リストウィジェット */
        QListWidget, QTreeWidget {{
            background-color: {colors['table_background']};
            border: 1px solid {colors['border_color']};
            color: {colors['table_text']};
            alternate-background-color: {colors['table_alternate']};
        }}
        
        QListWidget::item, QTreeWidget::item {{
            padding: 4px;
            border-bottom: 1px solid {colors['table_grid']};
        }}
        
        QListWidget::item:selected, QTreeWidget::item:selected {{
            background-color: {colors['selection_background']};
            color: {colors['selection_color']};
        }}
        
        QListWidget::item:hover, QTreeWidget::item:hover {{
            background-color: {colors['menu_hover']};
        }}
        
        /* テーブルウィジェット */
        QTableWidget {{
            background-color: {colors['table_background']};
            border: 1px solid {colors['border_color']};
            color: {colors['table_text']};
            gridline-color: {colors['table_grid']};
            alternate-background-color: {colors['table_alternate']};
        }}
        
        QTableWidget::item {{
            padding: 4px;
            border: none;
        }}
        
        QTableWidget::item:selected {{
            background-color: {colors['selection_background']};
            color: {colors['selection_color']};
        }}
        
        QHeaderView::section {{
            background-color: {colors['table_header']};
            border: 1px solid {colors['border_color']};
            color: {colors['table_text']};
            padding: 6px;
            font-weight: bold;
        }}
        
        /* タブウィジェット */
        QTabWidget::pane {{
            background-color: {colors['background_color']};
            border: 1px solid {colors['border_color']};
        }}
        
        QTabBar::tab {{
            background-color: {colors['tab_background']};
            border: 1px solid {colors['border_color']};
            color: {colors['tab_text']};
            padding: 8px 16px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {colors['tab_active']};
            border-bottom: 2px solid {colors['selection_color']};
        }}
        
        QTabBar::tab:hover {{
            background-color: {colors['menu_hover']};
        }}
        
        /* グループボックス */
        QGroupBox {{
            background-color: {colors['background_color']};
            border: 1px solid {colors['border_color']};
            color: {colors['text_color']};
            font-weight: bold;
            margin-top: 10px;
            padding-top: 10px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }}
        
        /* チェックボックス・ラジオボタン */
        QCheckBox, QRadioButton {{
            background-color: transparent;
            color: {colors['text_color']};
            spacing: 5px;
        }}
        
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            background-color: {colors['input_background']};
            border: 1px solid {colors['border_color']};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {colors['selection_color']};
            border: 1px solid {colors['selection_color']};
        }}
        
        QRadioButton::indicator {{
            border-radius: 8px;
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {colors['selection_color']};
            border: 1px solid {colors['selection_color']};
        }}
        
        /* プログレスバー */
        QProgressBar {{
            background-color: {colors['progress_background']};
            border: 1px solid {colors['border_color']};
            border-radius: 3px;
            text-align: center;
            color: {colors['text_color']};
        }}
        
        QProgressBar::chunk {{
            background-color: {colors['progress_chunk']};
            border-radius: 3px;
        }}
        
        /* スクロールバー */
        QScrollBar:vertical {{
            background-color: {colors['scrollbar_background']};
            width: 12px;
            border: none;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {colors['scrollbar_handle']};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {colors['scrollbar_hover']};
        }}
        
        QScrollBar:horizontal {{
            background-color: {colors['scrollbar_background']};
            height: 12px;
            border: none;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {colors['scrollbar_handle']};
            border-radius: 6px;
            min-width: 20px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors['scrollbar_hover']};
        }}
        
        QScrollBar::add-line, QScrollBar::sub-line {{
            border: none;
            background: none;
        }}
        
        /* ダイアログ */
        QDialog {{
            background-color: {colors['dialog_background']};
            border: 1px solid {colors['dialog_border']};
            color: {colors['dialog_text']};
        }}
        
        /* メッセージボックス */
        QMessageBox {{
            background-color: {colors['dialog_background']};
            color: {colors['dialog_text']};
        }}
        
        /* ツールチップ */
        QToolTip {{
            background-color: {colors['menu_background']};
            border: 1px solid {colors['border_color']};
            color: {colors['menu_text']};
            padding: 4px;
            border-radius: 3px;
        }}
        
        /* 日付編集 */
        QDateEdit {{
            background-color: {colors['input_background']};
            border: 1px solid {colors['input_border']};
            color: {colors['input_text']};
            padding: 4px;
            border-radius: 3px;
        }}
        
        QDateEdit:focus {{
            border: 2px solid {colors['input_focus_border']};
        }}
        
        /* カレンダーウィジェット */
        QCalendarWidget {{
            background-color: {colors['background_color']};
            color: {colors['text_color']};
        }}
        
        QCalendarWidget QAbstractItemView {{
            background-color: {colors['table_background']};
            color: {colors['table_text']};
            selection-background-color: {colors['selection_background']};
        }}
        """
        
        return stylesheet
    
    def get_available_themes(self) -> list:
        """利用可能なテーマ一覧を取得"""
        return list(self.themes.keys())
    
    def get_theme_display_name(self, theme_name: str) -> str:
        """テーマの表示名を取得"""
        display_names = {
            "light": "ライトモード",
            "dark": "ダークモード"
        }
        return display_names.get(theme_name, theme_name)

# グローバルテーママネージャーインスタンス
theme_manager = ThemeManager() 
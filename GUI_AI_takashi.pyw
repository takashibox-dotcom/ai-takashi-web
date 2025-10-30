import logging
from logging.handlers import RotatingFileHandler
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QThread, pyqtSignal, QWaitCondition, QMutex, QMutexLocker
from text_build import get_google_api_key, configure_api, generate_response, generate_image_response, check_image_recognition_available
from custom_gpt_manager import custom_gpt_manager, CustomGPT
from export_manager import export_manager, ConversationEntry
from backup_manager import backup_manager
from system_requirements import system_requirements
from response_time_manager import response_time_manager
from theme_manager import theme_manager
from image_recognition_manager import image_recognition_manager
from memory_manager import memory_manager, ConversationMemory
from datetime import datetime, timedelta
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import time
from pathlib import Path
import os
import shutil
import requests          # WEB画像ダウンロード用
import tempfile          # 一時ファイル作成用
import urllib.parse      # URL解析用
import mimetypes         # MIME Type処理用
from typing import Optional  # 型ヒント用

# matplotlibの日本語フォント設定
plt.rcParams['font.family'] = 'MS Gothic'  # Windows用
plt.rcParams['axes.unicode_minus'] = False  # マイナス記号の文字化け防止

# ログ設定（ユーザーのホームディレクトリに保存）
home_dir = Path.home()
ai_config_dir = home_dir / ".ai_takashi_config"
ai_config_dir.mkdir(exist_ok=True)
app_log = ai_config_dir / "app.log"
handler = RotatingFileHandler(str(app_log), maxBytes=10*1024*1024, backupCount=5)
logging.basicConfig(
    handlers=[handler],
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class GenerateThread(QThread):
    result_ready = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str, str)  # エラー発生時のシグナル

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.user_question = None
        self.conversation_history = []
        self.lock = QMutex()
        self.condition = QWaitCondition()
        self.running = True
        self.max_retries = 3  # 最大リトライ回数

    def run(self):
        while self.running:
            with QMutexLocker(self.lock):
                if not self.user_question:
                    self.condition.wait(self.lock)
                if self.user_question:
                    retry_count = 0
                    success = False
                    
                    while retry_count < self.max_retries and not success:
                        try:
                            response = generate_response(self.model, self.user_question, self.conversation_history)
                            response_text = response.text.strip()
                            self.result_ready.emit(self.user_question, response_text)
                            success = True
                            logging.info(f"API応答成功 (試行回数: {retry_count + 1})")
                        except Exception as e:
                            retry_count += 1
                            error_msg = str(e)
                            logging.error(f"GenerateThreadの実行中にエラーが発生しました (試行{retry_count}/{self.max_retries}): {error_msg}")
                            
                            if retry_count < self.max_retries:
                                # リトライ前に少し待機
                                self.msleep(1000 * retry_count)  # 指数バックオフ
                                logging.info(f"リトライします... ({retry_count + 1}/{self.max_retries})")
                            else:
                                # 最大リトライ回数に達した場合
                                detailed_error = f"最大リトライ回数({self.max_retries})に達しました。\n最後のエラー: {error_msg}"
                                self.error_occurred.emit(self.user_question, detailed_error)
                                logging.error(detailed_error)
                    
                    self.user_question = None

    def generate_response(self, user_question, conversation_history):
        with QMutexLocker(self.lock):
            self.user_question = user_question
            self.conversation_history = conversation_history
            self.condition.wakeOne()

    def stop(self):
        with QMutexLocker(self.lock):
            self.running = False
            self.condition.wakeOne()

class ImageRecognitionThread(QThread):
    result_ready = pyqtSignal(str, str, str)  # question, response, image_path
    error_occurred = pyqtSignal(str, str)  # error_message, image_path

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.user_question = None
        self.image_path = None
        self.conversation_history = []
        self.lock = QMutex()
        self.condition = QWaitCondition()
        self.running = True
        self.max_retries = 3  # 最大リトライ回数

    def run(self):
        while self.running:
            with QMutexLocker(self.lock):
                if not self.user_question or not self.image_path:
                    self.condition.wait(self.lock)
                if self.user_question and self.image_path:
                    retry_count = 0
                    success = False
                    
                    while retry_count < self.max_retries and not success:
                        try:
                            response, success_flag, error_message = generate_image_response(
                                self.model, self.user_question, self.image_path, self.conversation_history
                            )
                            
                            if success_flag and response:
                                response_text = response.text.strip()
                                self.result_ready.emit(self.user_question, response_text, self.image_path)
                                success = True
                                logging.info(f"画像認識API応答成功 (試行回数: {retry_count + 1})")
                            else:
                                raise Exception(error_message or "画像認識に失敗しました")
                                
                        except Exception as e:
                            retry_count += 1
                            error_msg = str(e)
                            logging.error(f"ImageRecognitionThreadの実行中にエラーが発生しました (試行{retry_count}/{self.max_retries}): {error_msg}")
                            
                            if retry_count < self.max_retries:
                                # リトライ前に少し待機
                                self.msleep(1000 * retry_count)  # 指数バックオフ
                                logging.info(f"画像認識リトライします... ({retry_count + 1}/{self.max_retries})")
                            else:
                                # 最大リトライ回数に達した場合
                                detailed_error = f"画像認識の最大リトライ回数({self.max_retries})に達しました。\n最後のエラー: {error_msg}"
                                self.error_occurred.emit(detailed_error, self.image_path)
                                logging.error(detailed_error)
                    
                    self.user_question = None
                    self.image_path = None

    def generate_image_response(self, user_question, image_path, conversation_history):
        with QMutexLocker(self.lock):
            self.user_question = user_question
            self.image_path = image_path
            self.conversation_history = conversation_history
            self.condition.wakeOne()

    def stop(self):
        with QMutexLocker(self.lock):
            self.running = False
            self.condition.wakeOne()

class App(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.conversation_history = []
        self.total_tokens = 0
        self.last_reset_date = datetime.now()
        self.token_history = []
        
        # 画像認識関連の初期化
        self.selected_image_path = None
        self.image_recognition_available = False
        
        # ドラッグ＆ドロップを有効化
        self.setAcceptDrops(True)
        self.drag_active = False  # ドラッグ中フラグ
        self.temp_image_files = []  # WEB画像の一時ファイルリスト（終了時削除用）
        
        # 設定ファイルのパスを設定
        home_dir = Path.home()
        ai_config_dir = home_dir / ".ai_takashi_config"
        ai_config_dir.mkdir(exist_ok=True)
        self.token_usage_file = ai_config_dir / "token_usage.json"
        self.token_settings_file = ai_config_dir / "token_settings.json"
        
        # 警告閾値の設定を先に行う
        self.warning_threshold = self.load_warning_threshold()
        
        self.initUI()
        self.load_token_usage()
        self.check_monthly_reset()

        try:
            self.api_key = get_google_api_key()
            if not self.api_key:
                self.show_error("Google APIキーが設定されていません。")
                QtCore.QCoreApplication.quit()
            logging.info("Google APIキーを取得しました。")
        except Exception as e:
            logging.error(f"APIキーの取得中にエラーが発生しました: {str(e)}")
            self.show_error(f"APIキーの取得中にエラーが発生しました。詳細はログを確認してください。")
            QtCore.QCoreApplication.quit()

        self.init_model()
        self.load_characters()
        self.start_backup_scheduler()
        self.check_system_requirements()
        self.check_image_recognition_support()
        self.apply_theme()
        self.showMaximized()

    def check_image_recognition_support(self):
        """画像認識機能のサポート状況をチェックする"""
        try:
            self.image_recognition_available = check_image_recognition_available()
            if self.image_recognition_available:
                logging.info("画像認識機能が利用可能です")
            else:
                logging.warning("画像認識機能が利用できません")
            
            # UIの状態を更新
            self.update_image_recognition_ui()
            
        except Exception as e:
            logging.error(f"画像認識機能チェックエラー: {e}")
            self.image_recognition_available = False
            self.update_image_recognition_ui()

    def update_image_recognition_ui(self):
        """画像認識機能のUI状態を更新する"""
        try:
            # 画像アップロードボタンの状態を更新
            if hasattr(self, 'image_upload_button'):
                self.image_upload_button.setEnabled(self.image_recognition_available)
            
            # クイックセレクトボタンの状態を更新
            if hasattr(self, 'quick_select_button'):
                self.quick_select_button.setEnabled(self.image_recognition_available)
            
            # 警告ラベルの表示/非表示を更新
            if hasattr(self, 'image_warning_label'):
                self.image_warning_label.setVisible(not self.image_recognition_available)
            
            # 画像状態インジケーターを更新
            self.update_image_status_indicator()
            
            logging.info(f"画像認識UI状態を更新しました: {'有効' if self.image_recognition_available else '無効'}")
            
        except Exception as e:
            logging.error(f"画像認識UI更新エラー: {e}")

    def initUI(self):
        self.setWindowTitle("AI_takashi")

        # メインレイアウト
        main_layout = QtWidgets.QVBoxLayout(self)

        # タブウィジェットの作成
        tab_widget = QtWidgets.QTabWidget()

        # チャットタブ
        chat_tab = QtWidgets.QWidget()
        chat_layout = QtWidgets.QVBoxLayout(chat_tab)

        # スプリッター
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # 左側のウィジェット
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)

        # ラベル
        self.label = QtWidgets.QLabel("質問あるかね? (プロンプトをインプットしてください):")
        font = QtGui.QFont("メイリオ", 10)
        self.label.setFont(font)
        left_layout.addWidget(self.label)

        # カスタムGPTキャラクター選択機能
        character_layout = QtWidgets.QHBoxLayout()
        character_label = QtWidgets.QLabel("キャラクター:")
        character_label.setFont(font)
        
        self.character_display = QtWidgets.QLabel("AI_takashi")
        self.character_display.setFont(font)
        self.character_display.setStyleSheet("QLabel { background-color: #e3f2fd; padding: 5px; border-radius: 3px; }")
        
        self.character_create_button = QtWidgets.QPushButton("新規作成", self)
        self.character_create_button.setFont(font)
        self.character_create_button.clicked.connect(self.show_character_creator)
        
        self.character_manage_button = QtWidgets.QPushButton("管理", self)
        self.character_manage_button.setFont(font)
        self.character_manage_button.clicked.connect(self.show_character_manager)
        
        self.character_switch_button = QtWidgets.QPushButton("切替", self)
        self.character_switch_button.setFont(font)
        self.character_switch_button.clicked.connect(self.show_character_selector)
        
        character_layout.addWidget(character_label)
        character_layout.addWidget(self.character_display, 1)
        character_layout.addWidget(self.character_create_button)
        character_layout.addWidget(self.character_manage_button)
        character_layout.addWidget(self.character_switch_button)
        left_layout.addLayout(character_layout)
        
        # ユーザー入力のエントリー
        self.user_input = QtWidgets.QTextEdit(self)
        self.user_input.setFont(font)
        self.user_input.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.user_input.installEventFilter(self)
        left_layout.addWidget(self.user_input)

        # 画像認識機能のUI（コンパクト版）
        self.create_compact_image_ui(left_layout, font)

        # 生成ボタン
        self.generate_button = QtWidgets.QPushButton("応答生成する", self)
        self.generate_button.setFont(font)
        self.generate_button.clicked.connect(self.start_generate_thread)
        left_layout.addWidget(self.generate_button)
        
        # プログレスバー
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # 不確定プログレス
        left_layout.addWidget(self.progress_bar)
        
        # 応答時間表示
        response_time_layout = QtWidgets.QHBoxLayout()
        
        self.response_time_label = QtWidgets.QLabel("", self)
        self.response_time_label.setFont(QtGui.QFont("メイリオ", 8))
        self.response_time_label.setStyleSheet("color: gray;")
        
        self.response_stats_button = QtWidgets.QPushButton("統計", self)
        self.response_stats_button.setFont(QtGui.QFont("メイリオ", 8))
        self.response_stats_button.setMaximumWidth(50)
        self.response_stats_button.clicked.connect(self.show_response_time_stats)
        
        response_time_layout.addWidget(self.response_time_label, 1)
        response_time_layout.addWidget(self.response_stats_button)
        left_layout.addLayout(response_time_layout)

        # 検索機能の追加
        search_layout = QtWidgets.QHBoxLayout()
        self.search_input = QtWidgets.QLineEdit(self)
        self.search_input.setPlaceholderText("会話履歴を検索...")
        self.search_input.setFont(font)
        self.search_button = QtWidgets.QPushButton("検索", self)
        self.search_button.setFont(font)
        self.search_button.clicked.connect(self.search_conversation)
        self.search_input.returnPressed.connect(self.search_conversation)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        left_layout.addLayout(search_layout)

        # 会話操作ボタン
        conversation_button_layout = QtWidgets.QHBoxLayout()
        
        self.clear_button = QtWidgets.QPushButton("会話クリア", self)
        self.clear_button.setFont(font)
        self.clear_button.clicked.connect(self.clear_conversation)
        
        self.export_button = QtWidgets.QPushButton("エクスポート", self)
        self.export_button.setFont(font)
        self.export_button.clicked.connect(self.show_export_dialog)
        
        conversation_button_layout.addWidget(self.clear_button)
        conversation_button_layout.addWidget(self.export_button)
        left_layout.addLayout(conversation_button_layout)

        # 管理ボタン
        management_button_layout = QtWidgets.QHBoxLayout()
        
        self.about_button = QtWidgets.QPushButton("About", self)
        self.about_button.setFont(font)
        self.about_button.clicked.connect(self.show_about_dialog)
        
        self.backup_manager_button = QtWidgets.QPushButton("バックアップ管理", self)
        self.backup_manager_button.setFont(font)
        self.backup_manager_button.clicked.connect(self.show_backup_manager)
        
        self.system_info_button = QtWidgets.QPushButton("システム情報", self)
        self.system_info_button.setFont(font)
        self.system_info_button.clicked.connect(self.show_system_info)
        
        self.theme_toggle_button = QtWidgets.QPushButton("🌙", self)  # 月のアイコン
        self.theme_toggle_button.setFont(QtGui.QFont("メイリオ", 12))
        self.theme_toggle_button.setMaximumWidth(40)
        self.theme_toggle_button.setToolTip("ダークモード切り替え")
        self.theme_toggle_button.clicked.connect(self.toggle_theme)
        
        management_button_layout.addWidget(self.about_button)
        management_button_layout.addWidget(self.backup_manager_button)
        management_button_layout.addWidget(self.system_info_button)
        management_button_layout.addWidget(self.theme_toggle_button)
        left_layout.addLayout(management_button_layout)
        
        # 終了ボタン
        self.quit_button = QtWidgets.QPushButton("終了", self)
        self.quit_button.setFont(font)
        self.quit_button.clicked.connect(self.close_application)
        left_layout.addWidget(self.quit_button)

        left_layout.setStretch(1, 1)

        # 右側のウィジェット
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)

        # 返答を表示するテキストボックス
        self.response_text = QtWidgets.QTextEdit(self)
        self.response_text.setFont(font)
        self.response_text.setLineWrapMode(
            QtWidgets.QTextEdit.WidgetWidth
        )
        right_layout.addWidget(self.response_text)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        chat_layout.addWidget(splitter)
        tab_widget.addTab(chat_tab, "チャット")

        # トークン管理タブ
        token_tab = QtWidgets.QWidget()
        token_layout = QtWidgets.QVBoxLayout(token_tab)

        # トークン使用量表示用のラベル
        self.token_label = QtWidgets.QLabel("今月のトークン使用量: 0")
        self.token_label.setFont(font)
        token_layout.addWidget(self.token_label)

        # 警告閾値設定
        threshold_layout = QtWidgets.QHBoxLayout()
        threshold_label = QtWidgets.QLabel("警告閾値:")
        self.threshold_input = QtWidgets.QSpinBox()
        self.threshold_input.setRange(1000, 1000000)
        self.threshold_input.setValue(self.warning_threshold)
        self.threshold_input.valueChanged.connect(self.update_warning_threshold)
        threshold_layout.addWidget(threshold_label)
        threshold_layout.addWidget(self.threshold_input)
        token_layout.addLayout(threshold_layout)

        # トークン使用量のグラフ
        self.figure, self.ax = plt.subplots(figsize=(8, 4))
        self.canvas = FigureCanvas(self.figure)
        token_layout.addWidget(self.canvas)

        # 統計情報表示
        self.stats_label = QtWidgets.QLabel()
        self.stats_label.setFont(font)
        token_layout.addWidget(self.stats_label)

        # トークン使用量リセットボタン
        self.reset_token_button = QtWidgets.QPushButton("トークン使用量リセット", self)
        self.reset_token_button.setFont(font)
        self.reset_token_button.clicked.connect(self.reset_token_usage)
        token_layout.addWidget(self.reset_token_button)

        tab_widget.addTab(token_tab, "トークン管理")

        # 会話記憶タブ
        memory_tab = QtWidgets.QWidget()
        memory_layout = QtWidgets.QVBoxLayout(memory_tab)
        
        # ヘッダー部分
        memory_header = QtWidgets.QLabel("💭 会話記憶")
        memory_header.setFont(QtGui.QFont("メイリオ", 14, QtGui.QFont.Bold))
        memory_layout.addWidget(memory_header)
        
        # 説明文
        memory_desc = QtWidgets.QLabel("キャラクターとの会話を記憶して、いつでも続きから話せます")
        memory_desc.setStyleSheet("color: #666; padding: 5px;")
        memory_layout.addWidget(memory_desc)
        
        # 上部コントロール
        control_layout = QtWidgets.QHBoxLayout()
        
        # 現在の会話を記憶ボタン
        self.save_memory_button = QtWidgets.QPushButton("📝 現在の会話を記憶", self)
        self.save_memory_button.setFont(font)
        self.save_memory_button.clicked.connect(self.save_current_conversation_as_memory)
        self.save_memory_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        control_layout.addWidget(self.save_memory_button)
        
        # 新規記憶作成ボタン
        self.new_memory_button = QtWidgets.QPushButton("➕ 新規記憶", self)
        self.new_memory_button.setFont(font)
        self.new_memory_button.clicked.connect(self.create_new_memory_manually)
        control_layout.addWidget(self.new_memory_button)
        
        # 統計情報ボタン
        self.memory_stats_button = QtWidgets.QPushButton("📊 統計", self)
        self.memory_stats_button.setFont(font)
        self.memory_stats_button.clicked.connect(self.show_memory_statistics)
        control_layout.addWidget(self.memory_stats_button)
        
        control_layout.addStretch()
        memory_layout.addLayout(control_layout)
        
        # 検索・フィルターエリア
        filter_layout = QtWidgets.QHBoxLayout()
        
        # 検索ボックス
        self.memory_search_input = QtWidgets.QLineEdit()
        self.memory_search_input.setPlaceholderText("🔍 記憶を検索...")
        self.memory_search_input.setFont(font)
        self.memory_search_input.textChanged.connect(self.filter_memories)
        filter_layout.addWidget(self.memory_search_input, 3)
        
        # キャラクターフィルター
        self.memory_character_filter = QtWidgets.QComboBox()
        self.memory_character_filter.setFont(font)
        self.memory_character_filter.addItem("全キャラクター")
        self.memory_character_filter.currentTextChanged.connect(self.filter_memories)
        filter_layout.addWidget(self.memory_character_filter, 1)
        
        # カテゴリフィルター
        self.memory_category_filter = QtWidgets.QComboBox()
        self.memory_category_filter.setFont(font)
        self.memory_category_filter.addItem("全カテゴリ")
        for category in memory_manager.categories:
            self.memory_category_filter.addItem(category)
        self.memory_category_filter.currentTextChanged.connect(self.filter_memories)
        filter_layout.addWidget(self.memory_category_filter, 1)
        
        # 重要度フィルター
        self.memory_importance_filter = QtWidgets.QComboBox()
        self.memory_importance_filter.setFont(font)
        self.memory_importance_filter.addItem("全重要度")
        for importance in memory_manager.importance_levels:
            self.memory_importance_filter.addItem(importance)
        self.memory_importance_filter.currentTextChanged.connect(self.filter_memories)
        filter_layout.addWidget(self.memory_importance_filter, 1)
        
        memory_layout.addLayout(filter_layout)
        
        # 記憶リストエリア（スプリッター使用）
        memory_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        # 左側: 記憶リスト
        self.memory_list = QtWidgets.QListWidget()
        self.memory_list.setFont(font)
        self.memory_list.itemClicked.connect(self.on_memory_selected)
        memory_splitter.addWidget(self.memory_list)
        
        # 右側: 記憶詳細パネル
        memory_detail_widget = QtWidgets.QWidget()
        memory_detail_layout = QtWidgets.QVBoxLayout(memory_detail_widget)
        
        # 記憶詳細表示
        self.memory_detail_text = QtWidgets.QTextBrowser()
        self.memory_detail_text.setFont(font)
        self.memory_detail_text.setOpenExternalLinks(False)
        memory_detail_layout.addWidget(self.memory_detail_text)
        
        # アクションボタン
        memory_action_layout = QtWidgets.QHBoxLayout()
        
        self.continue_conversation_button = QtWidgets.QPushButton("💬 続きを話す", self)
        self.continue_conversation_button.setFont(font)
        self.continue_conversation_button.clicked.connect(self.continue_conversation_from_memory)
        self.continue_conversation_button.setEnabled(False)
        self.continue_conversation_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        memory_action_layout.addWidget(self.continue_conversation_button)
        
        self.edit_memory_button = QtWidgets.QPushButton("✏️ 編集", self)
        self.edit_memory_button.setFont(font)
        self.edit_memory_button.clicked.connect(self.edit_selected_memory)
        self.edit_memory_button.setEnabled(False)
        memory_action_layout.addWidget(self.edit_memory_button)
        
        self.delete_memory_button = QtWidgets.QPushButton("🗑️ 削除", self)
        self.delete_memory_button.setFont(font)
        self.delete_memory_button.clicked.connect(self.delete_selected_memory)
        self.delete_memory_button.setEnabled(False)
        memory_action_layout.addWidget(self.delete_memory_button)
        
        memory_action_layout.addStretch()
        memory_detail_layout.addLayout(memory_action_layout)
        
        memory_splitter.addWidget(memory_detail_widget)
        memory_splitter.setStretchFactor(0, 1)
        memory_splitter.setStretchFactor(1, 2)
        
        memory_layout.addWidget(memory_splitter)
        
        tab_widget.addTab(memory_tab, "💭 会話記憶")
        
        # 記憶リストを初期化（変数のみ初期化、データ読み込みは後で）
        self.selected_memory_id = None

        main_layout.addWidget(tab_widget)
        self.setLayout(main_layout)
        
        # UI構築後に記憶リストを読み込む
        QtCore.QTimer.singleShot(100, self.initialize_memory_tab)

    def create_compact_image_ui(self, parent_layout, font):
        """コンパクトな画像認識UIを作成"""
        # メイン画像機能コンテナ
        image_container = QtWidgets.QWidget()
        image_container_layout = QtWidgets.QVBoxLayout()
        image_container_layout.setContentsMargins(5, 5, 5, 5)
        
        # 画像機能のヘッダー（折りたたみ可能）
        header_layout = QtWidgets.QHBoxLayout()
        
        # 折りたたみボタン
        self.image_toggle_button = QtWidgets.QPushButton("🖼️ 画像機能")
        self.image_toggle_button.setFont(font)
        self.image_toggle_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.image_toggle_button.clicked.connect(self.toggle_image_panel)
        
        # 画像状態インジケーター
        self.image_status_label = QtWidgets.QLabel("📷")
        self.image_status_label.setFont(QtGui.QFont("メイリオ", 12))
        self.image_status_label.setToolTip("画像が選択されていません")
        
        # クイックアクションボタン
        self.quick_select_button = QtWidgets.QPushButton("📁")
        self.quick_select_button.setMaximumSize(30, 30)
        self.quick_select_button.setToolTip("画像を選択")
        self.quick_select_button.clicked.connect(self.select_image)
        self.quick_select_button.setEnabled(self.image_recognition_available)
        
        header_layout.addWidget(self.image_toggle_button, 1)
        header_layout.addWidget(self.image_status_label)
        header_layout.addWidget(self.quick_select_button)
        
        image_container_layout.addLayout(header_layout)
        
        # 展開可能な詳細パネル
        self.image_detail_panel = QtWidgets.QWidget()
        self.image_detail_panel.setVisible(False)  # 初期状態は折りたたみ
        
        detail_layout = QtWidgets.QVBoxLayout()
        detail_layout.setContentsMargins(10, 5, 10, 5)
        
        # コンパクトボタンレイアウト
        button_layout = QtWidgets.QHBoxLayout()
        
        self.image_upload_button = QtWidgets.QPushButton("📷 選択", self)
        self.image_upload_button.setFont(QtGui.QFont("メイリオ", 9))
        self.image_upload_button.clicked.connect(self.select_image)
        self.image_upload_button.setEnabled(self.image_recognition_available)
        
        self.image_clear_button = QtWidgets.QPushButton("🗑️ 削除", self)
        self.image_clear_button.setFont(QtGui.QFont("メイリオ", 9))
        self.image_clear_button.clicked.connect(self.clear_image)
        self.image_clear_button.setEnabled(False)
        
        self.image_recheck_button = QtWidgets.QPushButton("🔄", self)
        self.image_recheck_button.setMaximumSize(35, 25)
        self.image_recheck_button.setFont(QtGui.QFont("メイリオ", 8))
        self.image_recheck_button.clicked.connect(self.recheck_image_recognition)
        self.image_recheck_button.setToolTip("画像認識機能を再チェック")
        
        button_layout.addWidget(self.image_upload_button)
        button_layout.addWidget(self.image_clear_button)
        button_layout.addWidget(self.image_recheck_button)
        button_layout.addStretch()
        
        detail_layout.addLayout(button_layout)
        
        # コンパクトプレビュー（動的サイズ）
        self.image_preview = QtWidgets.QLabel("画像が選択されていません")
        self.image_preview.setFont(QtGui.QFont("メイリオ", 8))
        self.image_preview.setStyleSheet("""
            QLabel {
                border: 1px dashed #ccc;
                border-radius: 3px;
                padding: 5px;
                background-color: #f9f9f9;
                color: #666;
                text-align: center;
            }
        """)
        self.image_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.image_preview.setMinimumHeight(60)
        self.image_preview.setMaximumHeight(120)  # より小さく
        self.image_preview.setScaledContents(True)
        detail_layout.addWidget(self.image_preview)
        
        # コンパクト情報表示
        self.image_info_label = QtWidgets.QLabel("")
        self.image_info_label.setFont(QtGui.QFont("メイリオ", 7))
        self.image_info_label.setStyleSheet("color: #666;")
        self.image_info_label.setWordWrap(True)
        detail_layout.addWidget(self.image_info_label)
        
        # 警告ラベル（コンパクト）
        self.image_warning_label = QtWidgets.QLabel("⚠️ 画像認識機能が利用できません")
        self.image_warning_label.setFont(QtGui.QFont("メイリオ", 7))
        self.image_warning_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        self.image_warning_label.setVisible(not self.image_recognition_available)
        detail_layout.addWidget(self.image_warning_label)
        
        # ドラッグ＆ドロップヒント
        drag_hint_label = QtWidgets.QLabel(
            "💡 ヒント: 画像ファイルを直接ドラッグ＆ドロップ、または\n"
            "   画像を右クリック→「画像をコピー」→ Ctrl+V で貼り付けできます"
        )
        drag_hint_label.setFont(QtGui.QFont("メイリオ", 7))
        drag_hint_label.setStyleSheet("color: #2196F3; font-style: italic;")
        drag_hint_label.setWordWrap(True)
        detail_layout.addWidget(drag_hint_label)
        
        self.image_detail_panel.setLayout(detail_layout)
        image_container_layout.addWidget(self.image_detail_panel)
        
        image_container.setLayout(image_container_layout)
        parent_layout.addWidget(image_container)

    def toggle_image_panel(self):
        """画像パネルの表示/非表示を切り替え"""
        try:
            is_visible = self.image_detail_panel.isVisible()
            self.image_detail_panel.setVisible(not is_visible)
            
            # ボタンテキストを更新
            if not is_visible:
                self.image_toggle_button.setText("🖼️ 画像機能 ▼")
            else:
                self.image_toggle_button.setText("🖼️ 画像機能 ▶")
                
            logging.info(f"画像パネル: {'展開' if not is_visible else '折りたたみ'}")
            
        except Exception as e:
            logging.error(f"画像パネル切り替えエラー: {e}")

    def update_image_status_indicator(self):
        """画像状態インジケーターを更新"""
        try:
            if self.selected_image_path:
                self.image_status_label.setText("🖼️")
                self.image_status_label.setToolTip(f"画像選択済み: {Path(self.selected_image_path).name}")
                self.image_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            else:
                self.image_status_label.setText("📷")
                self.image_status_label.setToolTip("画像が選択されていません")
                self.image_status_label.setStyleSheet("color: #666;")
                
        except Exception as e:
            logging.error(f"画像状態インジケーター更新エラー: {e}")

    def init_model(self):
        try:
            self.model = configure_api(self.api_key)
            
            # テキスト用スレッド
            self.thread = GenerateThread(self.model)
            self.thread.result_ready.connect(self.on_result_ready)
            self.thread.error_occurred.connect(self.on_error_occurred)
            self.thread.start()
            
            # 画像認識用スレッド
            self.image_thread = ImageRecognitionThread(self.model)
            self.image_thread.result_ready.connect(self.on_image_result_ready)
            self.image_thread.error_occurred.connect(self.on_image_error_occurred)
            self.image_thread.start()
            
            logging.info("AIモデルを設定しました。")
        except Exception as e:
            logging.error(f"AIモデルの設定中にエラーが発生しました: {str(e)}")
            self.show_error(f"AIモデルの設定中にエラーが発生しました。詳細はログを確認してください。\n{str(e)}")

            # エラーメッセージを表示し、再試行のオプションを提供
            msg_box = QtWidgets.QMessageBox()
            msg_box.setIcon(QtWidgets.QMessageBox.Critical)
            msg_box.setText("AIモデルの設定中にエラーが発生しました。")
            msg_box.setInformativeText("詳細はログを確認してください。再試行しますか？")
            msg_box.setWindowTitle("エラー")
            msg_box.setStandardButtons(QtWidgets.QMessageBox.Retry | QtWidgets.QMessageBox.Cancel)
            ret = msg_box.exec_()

            if ret == QtWidgets.QMessageBox.Retry:
                self.init_model()
            else:
                QtCore.QCoreApplication.quit()

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.KeyPress and source is self.user_input:
            if event.key() == QtCore.Qt.Key_Return and not (
                event.modifiers() & QtCore.Qt.ShiftModifier
            ):
                self.start_generate_thread()
                return True
        return super().eventFilter(source, event)

    def start_generate_thread(self):
        """応答生成スレッドを開始する"""
        user_question = self.user_input.toPlainText()
        if not user_question.strip():
            self.show_error("質問を入力してください。")
            return

        # 画像が選択されている場合は画像認識を実行
        if self.selected_image_path and self.image_recognition_available:
            self.start_image_recognition_thread(user_question)
        else:
            self.start_text_generation_thread(user_question)

    def start_text_generation_thread(self, user_question):
        """テキストのみの応答生成スレッドを開始する"""
        try:
            # アクティブキャラクターのシステムプロンプトを適用
            active_character = custom_gpt_manager.get_active_character()
            if active_character:
                system_prompt = active_character.build_system_prompt()
                enhanced_history = [f"System: {system_prompt}"] + self.conversation_history
            else:
                enhanced_history = self.conversation_history

            # 応答時間測定開始
            self.start_time = time.time()
            
            # UIの状態を更新
            self.generate_button.setEnabled(False)
            self.generate_button.setText("生成中...")
            self.progress_bar.setVisible(True)
            self.response_time_label.setText("応答を生成しています...")
            
            self.thread.generate_response(user_question, enhanced_history)
            logging.info(f"テキスト応答生成を開始しました: {user_question}")
            
        except Exception as e:
            logging.error(f"テキスト応答生成エラー: {e}")
            self.show_error(f"応答生成中にエラーが発生しました: {str(e)}")
            self.reset_ui_state()

    def start_image_recognition_thread(self, user_question):
        """画像認識スレッドを開始する"""
        try:
            # アクティブキャラクターのシステムプロンプトを適用
            active_character = custom_gpt_manager.get_active_character()
            if active_character:
                system_prompt = active_character.build_system_prompt()
                enhanced_history = [f"System: {system_prompt}"] + self.conversation_history
            else:
                enhanced_history = self.conversation_history

            # 応答時間測定開始
            self.start_time = time.time()
            
            # UIの状態を更新
            self.generate_button.setEnabled(False)
            self.generate_button.setText("画像認識中...")
            self.progress_bar.setVisible(True)
            self.response_time_label.setText("画像を認識しています...")
            
            self.image_thread.generate_image_response(
                user_question, self.selected_image_path, enhanced_history
            )
            logging.info(f"画像認識を開始しました: {user_question}, 画像: {self.selected_image_path}")
            
        except Exception as e:
            logging.error(f"画像認識エラー: {e}")
            self.show_error(f"画像認識中にエラーが発生しました: {str(e)}")
            self.reset_ui_state()

    def on_result_ready(self, user_question, response_text):
        # 応答時間測定終了
        end_time = time.time()
        response_time = end_time - self.start_time
        
        # UIの状態を元に戻す
        self.generate_button.setEnabled(True)
        self.generate_button.setText("応答生成する")
        self.progress_bar.setVisible(False)
        
        # 応答時間を記録
        response_time_manager.add_response_time(
            response_time=response_time,
            user_text=user_question,
            ai_text=response_text
        )
        
        # パフォーマンス警告をチェック
        warnings = response_time_manager.check_performance_warnings(response_time)
        if warnings:
            warning_text = "\n".join(warnings)
            logging.warning(f"応答時間警告: {warning_text}")
        
        # 応答時間表示を更新
        self.update_response_time_display(response_time)
        
        # トークン使用量の更新（実際のトークン数はAPIレスポンスから取得する必要があります）
        estimated_tokens = len(user_question.split()) + len(response_text.split())
        self.add_token_usage(estimated_tokens)

        # アクティブキャラクターの会話履歴に追加
        active_character = custom_gpt_manager.get_active_character()
        if active_character:
            active_character.add_conversation(user_question, response_text)
            custom_gpt_manager.save_characters()
            character_name = active_character.name
        else:
            character_name = "AI_takashi"
        
        self.conversation_history.append(f"User: {user_question}")
        self.conversation_history.append(f"{character_name}: {response_text}")

        self.response_text.append(
            f"<span style='color:red;'>User: {user_question}</span>"
        )
        self.response_text.append(f"{character_name}: {response_text}\n")

        self.user_input.clear()
        logging.info(f"AIの応答を表示しました: {response_text} (応答時間: {response_time:.2f}秒)")

    def on_error_occurred(self, user_question, error_message):
        """エラー発生時の処理"""
        # UIの状態を元に戻す
        self.generate_button.setEnabled(True)
        self.generate_button.setText("応答生成する")
        self.progress_bar.setVisible(False)
        self.response_time_label.setText("エラーが発生しました")
        
        # エラーメッセージを表示
        self.response_text.append(
            f"<span style='color:red;'>User: {user_question}</span>"
        )
        self.response_text.append(
            f"<span style='color:red;'>Error: {error_message}</span>\n"
        )
        
        # 詳細なエラーダイアログを表示
        self.show_detailed_error("通信エラー", error_message)
        logging.error(f"エラー処理完了: {user_question} - {error_message}")

    def show_detailed_error(self, title, message):
        """詳細なエラーダイアログを表示"""
        error_dialog = QtWidgets.QMessageBox(self)
        error_dialog.setIcon(QtWidgets.QMessageBox.Critical)
        error_dialog.setWindowTitle(title)
        error_dialog.setText("エラーが発生しました")
        error_dialog.setDetailedText(message)
        error_dialog.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Retry)
        
        result = error_dialog.exec_()
        if result == QtWidgets.QMessageBox.Retry:
            # リトライボタンが押された場合
            self.start_generate_thread()

    def search_conversation(self):
        """会話履歴を検索する"""
        search_keyword = self.search_input.text().strip()
        if not search_keyword:
            self.show_error("検索キーワードを入力してください。")
            return
        
        # 検索結果をハイライト表示
        self.highlight_search_results(search_keyword)
        logging.info(f"会話履歴を検索しました: {search_keyword}")
    
    def highlight_search_results(self, keyword):
        """検索結果をハイライト表示する"""
        # 現在の表示内容を取得
        current_text = self.response_text.toPlainText()
        
        # ハイライト用のHTMLを作成
        highlighted_text = ""
        lines = current_text.split('\n')
        
        for line in lines:
            if keyword.lower() in line.lower():
                # キーワードをハイライト
                highlighted_line = line.replace(
                    keyword, f"<span style='background-color: yellow; color: black;'>{keyword}</span>"
                )
                highlighted_text += f"<div style='background-color: #e6f3ff; padding: 2px;'>{highlighted_line}</div><br>"
            else:
                highlighted_text += line + "<br>"
        
        # HTMLで表示
        self.response_text.setHtml(highlighted_text)
        
        # 検索結果の統計を表示
        matches = current_text.lower().count(keyword.lower())
        if matches > 0:
            self.show_info(f"検索結果: {matches}件の一致が見つかりました")
        else:
            self.show_info("検索結果: 一致するものが見つかりませんでした")
    
    def show_info(self, message):
        """情報メッセージを表示"""
        info_dialog = QtWidgets.QMessageBox(self)
        info_dialog.setIcon(QtWidgets.QMessageBox.Information)
        info_dialog.setText(message)
        info_dialog.setWindowTitle("検索結果")
        info_dialog.exec_()

    def clear_conversation(self):
        self.response_text.clear()
        self.conversation_history = []
        self.search_input.clear()  # 検索フィールドもクリア
        logging.info("会話履歴をクリアしました。")

    def show_error(self, message):
        error_dialog = QtWidgets.QErrorMessage(self)
        error_dialog.showMessage(message)
        logging.error(message)

    def show_about_dialog(self):
        """Aboutダイアログを表示"""
        about_text = """AI_takashi v1.1

Google Generative AI (Gemini)を活用したデスクトップ型AI対話チャットシステム

【主な機能】
• AI対話機能
• 会話履歴検索
• トークン使用量監視
• セキュリティ強化
• 暗号化データ保存

【使用ライブラリ】
• PyQt5 (GPL v3)
• google-generativeai (Apache License 2.0)
• matplotlib (Matplotlib License)
• cryptography (Apache License 2.0)
• python-dotenv (BSD 3-Clause)

詳細なライセンス情報は THIRD-PARTY-LICENSES.md をご参照ください。

© 2024 AI_takashi Project"""
        
        QtWidgets.QMessageBox.about(self, "About AI_takashi", about_text)
        logging.info("Aboutダイアログを表示しました")

    def load_characters(self):
        """カスタムキャラクターを読み込んで表示を更新"""
        active_character = custom_gpt_manager.get_active_character()
        if active_character:
            self.update_character_display(active_character)
        
        logging.info(f"カスタムキャラクター{custom_gpt_manager.get_character_count()}件をロードしました")
    
    def update_character_display(self, character: CustomGPT):
        """キャラクター表示を更新"""
        display_text = character.name
        if hasattr(character, 'specialization') and character.specialization.strip():
            # 専門分野がある場合は簡潔に表示
            spec_short = character.specialization[:20] + "..." if len(character.specialization) > 20 else character.specialization
            display_text += f" ({spec_short})"
        
        self.character_display.setText(display_text)
        
        # ツールチップで詳細情報を表示
        tooltip = f"キャラクター: {character.name}\n"
        if character.personality:
            tooltip += f"性格: {character.personality[:50]}...\n"
        if character.specialization:
            tooltip += f"専門分野: {character.specialization[:50]}...\n"
        tooltip += f"使用回数: {character.usage_count}回"
        
        self.character_display.setToolTip(tooltip)
        logging.info(f"アクティブキャラクターを'{character.name}'に更新しました")
    
    def show_character_creator(self):
        """キャラクター作成ダイアログを表示"""
        dialog = CharacterCreatorDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            # 新しいキャラクターが作成された場合、表示を更新
            self.load_characters()
            logging.info("キャラクター作成ダイアログを閉じ、表示を更新しました")
    
    def show_character_manager(self):
        """キャラクター管理ダイアログを表示"""
        dialog = CharacterManagerDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            # キャラクターが変更された場合、表示を更新
            self.load_characters()
            logging.info("キャラクター管理ダイアログを閉じ、表示を更新しました")
    
    def show_character_selector(self):
        """キャラクター切替ダイアログを表示"""
        dialog = CharacterSelectorDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            # キャラクターが切り替えられた場合、表示を更新
            self.load_characters()
            logging.info("キャラクター切替ダイアログを閉じ、表示を更新しました")

    def show_export_dialog(self):
        """エクスポートダイアログを表示"""
        if not self.conversation_history:
            QtWidgets.QMessageBox.information(
                self, "情報", "エクスポートする会話がありません。"
            )
            return
        
        dialog = ExportDialog(self, self.conversation_history)
        dialog.exec_()
        logging.info("エクスポートダイアログを表示しました")

    def start_backup_scheduler(self):
        """バックアップスケジューラーを開始"""
        try:
            backup_manager.start_backup_scheduler()
            logging.info("バックアップスケジューラーを開始しました")
        except Exception as e:
            logging.error(f"バックアップスケジューラー開始エラー: {e}")
    
    def show_backup_manager(self):
        """バックアップ管理ダイアログを表示"""
        dialog = BackupManagerDialog(self)
        dialog.exec_()
        logging.info("バックアップ管理ダイアログを表示しました")
    
    def create_manual_backup(self):
        """手動バックアップを作成"""
        try:
            backup_path = backup_manager.create_backup(auto_backup=False)
            if backup_path:
                QtWidgets.QMessageBox.information(
                    self, "成功", f"バックアップを作成しました。\n{backup_path}"
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self, "エラー", "バックアップの作成に失敗しました。"
                )
        except Exception as e:
            logging.error(f"手動バックアップエラー: {e}")
            QtWidgets.QMessageBox.critical(
                self, "エラー", f"バックアップ作成中にエラーが発生しました。\n{str(e)}"
            )

    def check_system_requirements(self):
        """システム要件をチェック"""
        try:
            overall_status = system_requirements.get_overall_status()
            
            # 要件を満たしていない場合は警告を表示
            if not overall_status['all_passed']:
                failed_requirements = overall_status['failed_requirements']
                warnings = overall_status['warnings']
                
                message = "システム要件の一部が満たされていません:\n\n"
                for req in failed_requirements:
                    req_info = system_requirements.requirements_met[req]
                    message += f"• {req}: {req_info['message']}\n"
                
                if warnings:
                    message += "\n警告:\n"
                    for warning in warnings:
                        message += f"• {warning}\n"
                
                message += "\n詳細な情報はシステム情報から確認できます。"
                
                QtWidgets.QMessageBox.warning(self, "システム要件警告", message)
            
            logging.info(f"システム要件チェック: {overall_status['passed_requirements']}/{overall_status['total_requirements']} 合格")
            
        except Exception as e:
            logging.error(f"システム要件チェックエラー: {e}")
    
    def show_system_info(self):
        """システム情報ダイアログを表示"""
        try:
            report = system_requirements.get_detailed_report()
            
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("システム情報")
            dialog.setModal(True)
            dialog.resize(600, 500)
            
            layout = QtWidgets.QVBoxLayout(dialog)
            
            # テキストエリア
            text_area = QtWidgets.QTextEdit()
            text_area.setPlainText(report)
            text_area.setReadOnly(True)
            text_area.setFont(QtGui.QFont("Consolas", 9))
            layout.addWidget(text_area)
            
            # ボタン
            button_layout = QtWidgets.QHBoxLayout()
            
            refresh_button = QtWidgets.QPushButton("更新")
            refresh_button.clicked.connect(lambda: self.refresh_system_info(text_area))
            
            close_button = QtWidgets.QPushButton("閉じる")
            close_button.clicked.connect(dialog.accept)
            
            button_layout.addWidget(refresh_button)
            button_layout.addStretch()
            button_layout.addWidget(close_button)
            
            layout.addLayout(button_layout)
            
            dialog.exec_()
            
        except Exception as e:
            logging.error(f"システム情報表示エラー: {e}")
            QtWidgets.QMessageBox.critical(
                self, "エラー", f"システム情報の表示に失敗しました。\n{str(e)}"
            )
    
    def refresh_system_info(self, text_area):
        """システム情報を更新"""
        try:
            # システム要件を再チェック
            system_requirements.check_system_requirements()
            
            # レポートを再生成
            report = system_requirements.get_detailed_report()
            text_area.setPlainText(report)
            
        except Exception as e:
            logging.error(f"システム情報更新エラー: {e}")
            QtWidgets.QMessageBox.warning(
                self, "エラー", f"システム情報の更新に失敗しました。\n{str(e)}"
            )

    def update_response_time_display(self, response_time: float):
        """応答時間表示を更新"""
        try:
            # 基本の応答時間表示
            base_text = f"応答時間: {response_time:.2f}秒"
            
            # 最近の統計と比較
            recent_stats = response_time_manager.get_statistics(days=7)
            if recent_stats.get('total_count', 0) > 0:
                avg_time = recent_stats['average_time']
                
                # 平均より速い/遅いかを表示
                if response_time <= avg_time * 0.8:
                    status = " (高速)"
                    color = "green"
                elif response_time >= avg_time * 1.5:
                    status = " (低速)"
                    color = "red"
                elif response_time >= avg_time * 1.2:
                    status = " (やや遅い)"
                    color = "orange"
                else:
                    status = ""
                    color = "gray"
                
                if status:
                    base_text += status
                    self.response_time_label.setStyleSheet(f"color: {color};")
                else:
                    self.response_time_label.setStyleSheet("color: gray;")
            else:
                self.response_time_label.setStyleSheet("color: gray;")
            
            self.response_time_label.setText(base_text)
            
        except Exception as e:
            logging.error(f"応答時間表示更新エラー: {e}")
            self.response_time_label.setText(f"応答時間: {response_time:.2f}秒")
    
    def show_response_time_stats(self):
        """応答時間統計ダイアログを表示"""
        try:
            dialog = ResponseTimeStatsDialog(self)
            dialog.exec_()
            logging.info("応答時間統計ダイアログを表示しました")
        except Exception as e:
            logging.error(f"応答時間統計表示エラー: {e}")
            QtWidgets.QMessageBox.critical(
                self, "エラー", f"応答時間統計の表示に失敗しました。\n{str(e)}"
            )

    def apply_theme(self):
        """テーマを適用する"""
        try:
            current_theme = theme_manager.get_current_theme()
            stylesheet = theme_manager.generate_stylesheet()
            
            # アプリケーション全体にスタイルシートを適用
            self.setStyleSheet(stylesheet)
            
            # テーマ切り替えボタンのアイコンを更新
            if hasattr(self, 'theme_toggle_button'):
                if current_theme == 'light':
                    self.theme_toggle_button.setText("🌙")
                    self.theme_toggle_button.setToolTip("ダークモード切り替え")
                else:
                    self.theme_toggle_button.setText("☀️")
                    self.theme_toggle_button.setToolTip("ライトモード切り替え")
            
            logging.info(f"テーマを適用しました: {current_theme}")
            
        except Exception as e:
            logging.error(f"テーマ適用エラー: {e}")

    def toggle_theme(self):
        """テーマを切り替える"""
        theme_manager.toggle_theme()
        self.apply_theme()
        logging.info("テーマを切り替えました")

    def update_theme_button(self):
        """テーマボタンのアイコンを更新"""
        try:
            if theme_manager.is_dark_mode():
                self.theme_toggle_button.setText("☀️")  # 太陽のアイコン（ライトモードに切り替え）
                self.theme_toggle_button.setToolTip("ライトモードに切り替え")
            else:
                self.theme_toggle_button.setText("🌙")  # 月のアイコン（ダークモードに切り替え）
                self.theme_toggle_button.setToolTip("ダークモードに切り替え")
                
        except Exception as e:
            logging.error(f"テーマボタン更新エラー: {e}")
    
    def show_theme_change_message(self, theme_name: str):
        """テーマ変更メッセージを表示"""
        try:
            # 一時的な通知を表示（3秒後に自動で閉じる）
            msg = QtWidgets.QLabel(f"{theme_name}に切り替えました", self)
            msg.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 120, 212, 200);
                    color: white;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)
            msg.setAlignment(QtCore.Qt.AlignCenter)
            msg.setGeometry(
                self.width() // 2 - 100, 
                self.height() - 100, 
                200, 40
            )
            msg.show()
            
            # 3秒後に非表示
            QtCore.QTimer.singleShot(3000, msg.deleteLater)
            
        except Exception as e:
            logging.error(f"テーマ変更メッセージ表示エラー: {e}")

    def close_application(self):
        """アプリケーションを終了"""
        try:
            # スレッドを停止
            if hasattr(self, 'thread'):
                self.thread.stop()
                self.thread.wait()
            
            if hasattr(self, 'image_thread'):
                self.image_thread.stop()
                self.image_thread.wait()
            
            # 設定を保存
            self.save_token_usage()
            
            logging.info("アプリケーションを終了しました")
            QtCore.QCoreApplication.quit()
            
        except Exception as e:
            logging.error(f"アプリケーション終了エラー: {e}")
            QtCore.QCoreApplication.quit()

    def check_monthly_reset(self):
        current_date = datetime.now()
        if current_date.month != self.last_reset_date.month or current_date.year != self.last_reset_date.year:
            self.reset_token_usage()

    def load_warning_threshold(self):
        try:
            with open(self.token_settings_file, 'r') as f:
                settings = json.load(f)
                return settings.get('warning_threshold', 100000)
        except FileNotFoundError:
            return 100000
        except PermissionError as e:
            logging.warning(f"権限エラーで警告閾値を読み込めません: {e}")
            return 100000

    def save_warning_threshold(self):
        try:
            with open(self.token_settings_file, 'w') as f:
                json.dump({'warning_threshold': self.warning_threshold}, f)
        except PermissionError as e:
            logging.warning(f"権限エラーで警告閾値を保存できません: {e}")
        except Exception as e:
            logging.error(f"警告閾値の保存エラー: {e}")

    def update_warning_threshold(self, value):
        self.warning_threshold = value
        self.save_warning_threshold()

    def load_token_usage(self):
        try:
            with open(self.token_usage_file, 'r') as f:
                data = json.load(f)
                self.total_tokens = data.get('total_tokens', 0)
                self.last_reset_date = datetime.fromisoformat(data.get('last_reset_date', datetime.now().isoformat()))
                
                # トークン履歴の整合性チェック
                token_history = data.get('token_history', [])
                valid_history = []
                for entry in token_history:
                    if isinstance(entry, dict) and 'date' in entry and 'tokens' in entry:
                        try:
                            # 日付とトークン数の形式をチェック
                            datetime.fromisoformat(entry['date'])
                            if isinstance(entry['tokens'], (int, float)) and entry['tokens'] >= 0:
                                valid_history.append(entry)
                            else:
                                logging.warning(f"無効なトークン数をスキップします: {entry}")
                        except (ValueError, TypeError) as e:
                            logging.warning(f"無効な日付形式をスキップします: {entry}, エラー: {e}")
                    else:
                        logging.warning(f"無効な履歴エントリをスキップします: {entry}")
                
                self.token_history = valid_history
                
                # 無効なデータがあった場合は保存
                if len(valid_history) != len(token_history):
                    logging.info(f"トークン履歴をクリーンアップしました。{len(valid_history)}件の有効なエントリを保持")
                    self.save_token_usage()
                
                self.update_token_label()
                self.update_graph()
                self.update_stats()
        except FileNotFoundError:
            self.save_token_usage()
        except PermissionError as e:
            logging.warning(f"権限エラーでトークン使用量を読み込めません: {e}")
            # デフォルト値を設定
            self.total_tokens = 0
            self.last_reset_date = datetime.now()
            self.token_history = []
            self.update_token_label()
            self.update_graph()
            self.update_stats()
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logging.error(f"トークン使用量ファイルの読み込みエラー: {e}")
            # デフォルト値を設定
            self.total_tokens = 0
            self.last_reset_date = datetime.now()
            self.token_history = []
            self.update_token_label()
            self.update_graph()
            self.update_stats()

    def save_token_usage(self):
        try:
            with open(self.token_usage_file, 'w') as f:
                json.dump({
                    'total_tokens': self.total_tokens,
                    'last_reset_date': self.last_reset_date.isoformat(),
                    'token_history': self.token_history
                }, f)
        except PermissionError as e:
            logging.warning(f"権限エラーでトークン使用量を保存できません: {e}")
        except Exception as e:
            logging.error(f"トークン使用量の保存エラー: {e}")

    def update_token_label(self):
        self.token_label.setText(f"今月のトークン使用量: {self.total_tokens:,}")

    def update_graph(self):
        self.ax.clear()
        if self.token_history:
            # データの整合性チェックとフィルタリング
            valid_entries = []
            for h in self.token_history:
                if isinstance(h, dict) and 'date' in h and 'tokens' in h:
                    try:
                        # 日付の形式をチェック
                        datetime.fromisoformat(h['date'])
                        valid_entries.append(h)
                    except (ValueError, TypeError) as e:
                        logging.warning(f"無効な日付形式をスキップします: {h['date']}, エラー: {e}")
                        continue
                else:
                    logging.warning(f"無効なデータ形式をスキップします: {h}")
                    continue
            
            if valid_entries:
                dates = [datetime.fromisoformat(h['date']) for h in valid_entries]
                tokens = [h['tokens'] for h in valid_entries]
                self.ax.plot(dates, tokens, marker='o')
                self.ax.set_title('トークン使用量の推移', fontsize=12)
                self.ax.set_xlabel('日付', fontsize=10)
                self.ax.set_ylabel('トークン数', fontsize=10)
                plt.xticks(rotation=45)
                self.figure.tight_layout()  # レイアウトの自動調整
                
                # 無効なデータがあった場合は、クリーンアップされたデータで更新
                if len(valid_entries) != len(self.token_history):
                    self.token_history = valid_entries
                    self.save_token_usage()
                    logging.info(f"トークン履歴をクリーンアップしました。{len(valid_entries)}件の有効なエントリを保持")
        self.canvas.draw()

    def update_stats(self):
        if self.token_history:
            # 有効なデータのみをフィルタリング
            valid_entries = []
            for h in self.token_history:
                if isinstance(h, dict) and 'tokens' in h and isinstance(h['tokens'], (int, float)):
                    valid_entries.append(h)
                else:
                    logging.warning(f"無効なトークンデータをスキップします: {h}")
            
            if valid_entries:
                total = sum(h['tokens'] for h in valid_entries)
                avg = total / len(valid_entries)
                max_tokens = max(h['tokens'] for h in valid_entries)
                stats_text = f"""
                統計情報:
                総トークン数: {total:,}
                平均トークン数: {avg:.1f}
                最大トークン数: {max_tokens:,}
                使用日数: {len(valid_entries)}
                """
                self.stats_label.setText(stats_text)
            else:
                self.stats_label.setText("統計情報: データなし")

    def add_token_usage(self, tokens):
        # トークン数の検証
        if not isinstance(tokens, (int, float)) or tokens < 0:
            logging.warning(f"無効なトークン数です: {tokens}")
            return
        
        self.total_tokens += tokens
        self.token_history.append({
            'date': datetime.now().isoformat(),
            'tokens': tokens
        })
        self.save_token_usage()
        self.update_token_label()
        self.update_graph()
        self.update_stats()

        # 警告閾値チェック
        if self.total_tokens >= self.warning_threshold:
            self.show_warning(f"トークン使用量が警告閾値（{self.warning_threshold:,}）を超えました！")

    def show_warning(self, message):
        warning_dialog = QtWidgets.QMessageBox()
        warning_dialog.setIcon(QtWidgets.QMessageBox.Warning)
        warning_dialog.setText(message)
        warning_dialog.setWindowTitle("警告")
        warning_dialog.exec_()

    def reset_token_usage(self):
        self.total_tokens = 0
        self.last_reset_date = datetime.now()
        self.token_history = []
        self.save_token_usage()
        self.update_token_label()
        self.update_graph()
        self.update_stats()
        logging.info("トークン使用量をリセットしました。")

    # 画像認識関連メソッド
    def select_image(self):
        """画像ファイルを選択する"""
        try:
            if not self.image_recognition_available:
                self.show_error("画像認識機能が利用できません。")
                return
            
            # サポートされている形式のフィルタを作成
            supported_formats = image_recognition_manager.get_supported_extensions()
            format_filter = "画像ファイル (" + " ".join(f"*{ext}" for ext in supported_formats) + ")"
            
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "画像を選択", "", format_filter
            )
            
            if file_path:
                self.set_selected_image(file_path)
                logging.info(f"画像を選択しました: {file_path}")
                
        except Exception as e:
            logging.error(f"画像選択エラー: {e}")
            self.show_error(f"画像の選択中にエラーが発生しました: {str(e)}")

    def set_selected_image(self, image_path):
        """選択された画像を設定する"""
        try:
            from text_build import validate_image_file
            
            # 画像の妥当性をチェック
            validation_result = validate_image_file(image_path)
            
            if not validation_result["valid"]:
                self.show_error(f"画像が無効です: {validation_result['error_message']}")
                return
            
            # 画像パスを保存
            self.selected_image_path = image_path
            
            # プレビューを更新
            self.update_image_preview()
            
            # 画像情報を表示
            self.update_image_info(validation_result)
            
            # ボタンの状態を更新
            self.image_clear_button.setEnabled(True)
            self.generate_button.setText("画像認識・応答生成")
            
            # 画像状態インジケーターを更新
            self.update_image_status_indicator()
            
            # パネルが折りたたまれている場合は自動展開
            if hasattr(self, 'image_detail_panel') and not self.image_detail_panel.isVisible():
                self.toggle_image_panel()
            
        except Exception as e:
            logging.error(f"画像設定エラー: {e}")
            self.show_error(f"画像の設定中にエラーが発生しました: {str(e)}")

    def update_image_preview(self):
        """画像プレビューを更新する"""
        try:
            if not self.selected_image_path:
                self.image_preview.setText("画像が選択されていません")
                self.image_preview.setStyleSheet("""
                    QLabel {
                        border: 1px dashed #ccc;
                        border-radius: 3px;
                        padding: 5px;
                        background-color: #f9f9f9;
                        color: #666;
                        text-align: center;
                    }
                """)
                return
            
            # 画像を読み込んでプレビュー表示
            pixmap = QtGui.QPixmap(self.selected_image_path)
            if not pixmap.isNull():
                # コンパクトサイズでアスペクト比を保持してリサイズ
                preview_size = QtCore.QSize(100, 100)  # より小さなサイズ
                scaled_pixmap = pixmap.scaled(
                    preview_size,
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation
                )
                self.image_preview.setPixmap(scaled_pixmap)
                self.image_preview.setStyleSheet("""
                    QLabel {
                        border: 1px solid #4CAF50;
                        border-radius: 3px;
                        padding: 2px;
                        background-color: #ffffff;
                    }
                """)
                
                # プレビューサイズを動的に調整
                actual_size = scaled_pixmap.size()
                self.image_preview.setMaximumHeight(actual_size.height() + 10)
                
            else:
                self.image_preview.setText("画像を読み込めませんでした")
                
        except Exception as e:
            logging.error(f"画像プレビュー更新エラー: {e}")
            self.image_preview.setText("プレビューエラー")

    def update_image_info(self, validation_result):
        """画像情報を更新する"""
        try:
            if not validation_result["valid"]:
                self.image_info_label.setText("")
                return
            
            # ファイル名
            file_name = Path(self.selected_image_path).name
            
            # サイズ情報
            width, height = validation_result["image_size"]
            file_size_mb = validation_result["file_size"] / (1024 * 1024)
            
            # 情報文字列を作成
            info_text = f"📁 {file_name}\n"
            info_text += f"📐 {width} × {height} px\n"
            info_text += f"🗂️ {validation_result['format']}\n"
            info_text += f"📊 {file_size_mb:.2f} MB"
            
            self.image_info_label.setText(info_text)
            
        except Exception as e:
            logging.error(f"画像情報更新エラー: {e}")
            self.image_info_label.setText("情報取得エラー")

    def clear_image(self):
        """選択された画像をクリアする"""
        try:
            self.selected_image_path = None
            
            # プレビューとボタンの状態を更新
            self.update_image_preview()
            self.image_info_label.setText("")
            self.image_clear_button.setEnabled(False)
            self.generate_button.setText("応答生成する")
            
            # 画像状態インジケーターを更新
            self.update_image_status_indicator()
            
            logging.info("選択された画像をクリアしました")
            
        except Exception as e:
            logging.error(f"画像クリアエラー: {e}")

    def start_generate_thread(self):
        """応答生成スレッドを開始する"""
        user_question = self.user_input.toPlainText()
        if not user_question.strip():
            self.show_error("質問を入力してください。")
            return

        # 画像が選択されている場合は画像認識を実行
        if self.selected_image_path and self.image_recognition_available:
            self.start_image_recognition_thread(user_question)
        else:
            self.start_text_generation_thread(user_question)

    def start_text_generation_thread(self, user_question):
        """テキストのみの応答生成スレッドを開始する"""
        try:
            # アクティブキャラクターのシステムプロンプトを適用
            active_character = custom_gpt_manager.get_active_character()
            if active_character:
                system_prompt = active_character.build_system_prompt()
                enhanced_history = [f"System: {system_prompt}"] + self.conversation_history
            else:
                enhanced_history = self.conversation_history

            # 応答時間測定開始
            self.start_time = time.time()
            
            # UIの状態を更新
            self.generate_button.setEnabled(False)
            self.generate_button.setText("生成中...")
            self.progress_bar.setVisible(True)
            self.response_time_label.setText("応答を生成しています...")
            
            self.thread.generate_response(user_question, enhanced_history)
            logging.info(f"テキスト応答生成を開始しました: {user_question}")
            
        except Exception as e:
            logging.error(f"テキスト応答生成エラー: {e}")
            self.show_error(f"応答生成中にエラーが発生しました: {str(e)}")
            self.reset_ui_state()

    def start_image_recognition_thread(self, user_question):
        """画像認識スレッドを開始する"""
        try:
            # アクティブキャラクターのシステムプロンプトを適用
            active_character = custom_gpt_manager.get_active_character()
            if active_character:
                system_prompt = active_character.build_system_prompt()
                enhanced_history = [f"System: {system_prompt}"] + self.conversation_history
            else:
                enhanced_history = self.conversation_history

            # 応答時間測定開始
            self.start_time = time.time()
            
            # UIの状態を更新
            self.generate_button.setEnabled(False)
            self.generate_button.setText("画像認識中...")
            self.progress_bar.setVisible(True)
            self.response_time_label.setText("画像を認識しています...")
            
            self.image_thread.generate_image_response(
                user_question, self.selected_image_path, enhanced_history
            )
            logging.info(f"画像認識を開始しました: {user_question}, 画像: {self.selected_image_path}")
            
        except Exception as e:
            logging.error(f"画像認識エラー: {e}")
            self.show_error(f"画像認識中にエラーが発生しました: {str(e)}")
            self.reset_ui_state()

    def on_image_result_ready(self, user_question, response_text, image_path):
        """画像認識結果を処理する"""
        try:
            # 応答時間を計算
            response_time = time.time() - self.start_time
            
            # 応答を表示
            self.response_text.append(f"User: {user_question}")
            self.response_text.append(f"AI: {response_text}")
            self.response_text.append(f"[画像認識結果 - {Path(image_path).name}]")
            self.response_text.append("-" * 50)
            
            # 会話履歴に追加
            self.conversation_history.append(f"User: {user_question}")
            self.conversation_history.append(f"AI: {response_text}")
            
            # 画像認識結果を履歴に保存
            active_character = custom_gpt_manager.get_active_character()
            character_name = active_character.name if active_character else "AI_takashi"
            
            image_recognition_manager.add_recognition_result(
                image_path, user_question, response_text, character_name
            )
            
            # トークン使用量を更新（画像は258トークンとして計算）
            estimated_tokens = len(user_question) + len(response_text) + 258
            self.add_token_usage(estimated_tokens)
            
            # 応答時間を記録
            response_time_manager.add_response_time(
                response_time, len(user_question), len(response_text)
            )
            
            # 応答時間表示を更新
            self.response_time_label.setText(f"応答時間: {response_time:.2f}秒 (画像認識)")
            
            # 入力エリアをクリア
            self.user_input.clear()
            
            # 画像をクリア（必要に応じて）
            self.clear_image()
            
            logging.info(f"画像認識完了: {response_time:.2f}秒")
            
        except Exception as e:
            logging.error(f"画像認識結果処理エラー: {e}")
            self.show_error(f"画像認識結果の処理中にエラーが発生しました: {str(e)}")
        finally:
            self.reset_ui_state()

    def on_image_error_occurred(self, error_message, image_path):
        """画像認識エラーを処理する"""
        try:
            logging.error(f"画像認識エラー: {error_message}")
            
            # エラーメッセージを表示
            self.response_text.append(f"❌ 画像認識エラー: {error_message}")
            self.response_text.append(f"画像: {Path(image_path).name if image_path else '不明'}")
            self.response_text.append("-" * 50)
            
            # ユーザーにエラーを通知
            self.show_error(f"画像認識に失敗しました:\n{error_message}")
            
        except Exception as e:
            logging.error(f"画像認識エラー処理エラー: {e}")
        finally:
            self.reset_ui_state()

    def reset_ui_state(self):
        """UIの状態をリセットする"""
        try:
            # ボタンとプログレスバーの状態をリセット
            self.generate_button.setEnabled(True)
            if self.selected_image_path:
                self.generate_button.setText("画像認識・応答生成")
            else:
                self.generate_button.setText("応答生成する")
            
            self.progress_bar.setVisible(False)
            
        except Exception as e:
            logging.error(f"UI状態リセットエラー: {e}")

    def recheck_image_recognition(self):
        """画像認識機能の再チェック"""
        try:
            logging.info("画像認識機能の再チェックを開始...")
            self.check_image_recognition_support()
            
            # 結果をユーザーに通知
            if self.image_recognition_available:
                self.show_info("✅ 画像認識機能が利用可能になりました！")
            else:
                self.show_error("❌ 画像認識機能が利用できません。設定を確認してください。")
                
            logging.info("画像認識機能の再チェックを完了しました")
            
        except Exception as e:
            logging.error(f"画像認識機能再チェックエラー: {e}")
            self.show_error(f"再チェック中にエラーが発生しました: {str(e)}")
    
    # ===== 会話記憶機能 =====
    
    def initialize_memory_tab(self):
        """記憶タブを初期化（UI構築後に実行）"""
        try:
            self.load_memory_list()
            self.update_character_filter()
            logging.info("記憶タブの初期化が完了しました")
        except Exception as e:
            logging.error(f"記憶タブ初期化エラー: {e}", exc_info=True)
    
    def load_memory_list(self):
        """記憶リストを読み込む"""
        try:
            if not hasattr(self, 'memory_list'):
                logging.warning("memory_listがまだ初期化されていません")
                return
            
            self.memory_list.clear()
            memories = memory_manager.get_all_memories(sort_by='created_at', reverse=True)
            
            for memory in memories:
                # リスト項目を作成
                item_text = f"📝 {memory.title}\n"
                item_text += f"   👤 {memory.character_name} | "
                item_text += f"📁 {memory.category} | "
                item_text += f"⭐ {memory.importance} | "
                item_text += f"📅 {datetime.fromisoformat(memory.created_at).strftime('%Y/%m/%d %H:%M')}"
                
                item = QtWidgets.QListWidgetItem(item_text)
                item.setData(QtCore.Qt.UserRole, memory.memory_id)
                self.memory_list.addItem(item)
            
            logging.info(f"記憶リストを読み込みました: {len(memories)}件")
            
        except Exception as e:
            logging.error(f"記憶リスト読み込みエラー: {e}", exc_info=True)
    
    def update_character_filter(self):
        """キャラクターフィルターを更新"""
        try:
            if not hasattr(self, 'memory_character_filter'):
                logging.warning("memory_character_filterがまだ初期化されていません")
                return
            
            current_selection = self.memory_character_filter.currentText()
            self.memory_character_filter.clear()
            self.memory_character_filter.addItem("全キャラクター")
            
            # 全キャラクターを取得
            characters = custom_gpt_manager.get_all_characters()
            for character in characters:
                self.memory_character_filter.addItem(character.name)
            
            # 以前の選択を復元
            index = self.memory_character_filter.findText(current_selection)
            if index >= 0:
                self.memory_character_filter.setCurrentIndex(index)
            
        except Exception as e:
            logging.error(f"キャラクターフィルター更新エラー: {e}", exc_info=True)
    
    def filter_memories(self):
        """記憶をフィルタリング"""
        try:
            keyword = self.memory_search_input.text()
            character = self.memory_character_filter.currentText()
            category = self.memory_category_filter.currentText()
            importance = self.memory_importance_filter.currentText()
            
            # フィルター条件を設定
            character_id = None
            if character != "全キャラクター":
                char = custom_gpt_manager.get_character_by_name(character)
                if char:
                    character_id = char.character_id
            
            category_filter = None if category == "全カテゴリ" else category
            importance_filter = None if importance == "全重要度" else importance
            
            # 検索実行
            memories = memory_manager.search_memories(
                keyword=keyword if keyword else None,
                character_id=character_id,
                category=category_filter,
                importance=importance_filter
            )
            
            # リストを更新
            self.memory_list.clear()
            for memory in memories:
                item_text = f"📝 {memory.title}\n"
                item_text += f"   👤 {memory.character_name} | "
                item_text += f"📁 {memory.category} | "
                item_text += f"⭐ {memory.importance} | "
                item_text += f"📅 {datetime.fromisoformat(memory.created_at).strftime('%Y/%m/%d %H:%M')}"
                
                item = QtWidgets.QListWidgetItem(item_text)
                item.setData(QtCore.Qt.UserRole, memory.memory_id)
                self.memory_list.addItem(item)
            
        except Exception as e:
            logging.error(f"記憶フィルタリングエラー: {e}", exc_info=True)
    
    def on_memory_selected(self, item):
        """記憶が選択されたとき"""
        try:
            memory_id = item.data(QtCore.Qt.UserRole)
            memory = memory_manager.get_memory(memory_id)
            
            if not memory:
                return
            
            self.selected_memory_id = memory_id
            
            # 詳細を表示
            detail_html = f"""
            <h2>📝 {memory.title}</h2>
            <p><b>👤 キャラクター:</b> {memory.character_name}</p>
            <p><b>📁 カテゴリ:</b> {memory.category}</p>
            <p><b>⭐ 重要度:</b> {memory.importance}</p>
            <p><b>📅 作成日時:</b> {datetime.fromisoformat(memory.created_at).strftime('%Y年%m月%d日 %H:%M:%S')}</p>
            <p><b>🔄 更新日時:</b> {datetime.fromisoformat(memory.updated_at).strftime('%Y年%m月%d日 %H:%M:%S')}</p>
            <p><b>👁️ アクセス回数:</b> {memory.access_count}回</p>
            """
            
            if memory.tags:
                detail_html += f"<p><b>🏷️ タグ:</b> {', '.join(memory.tags)}</p>"
            
            detail_html += f"""
            <hr>
            <h3>📄 内容</h3>
            <p>{memory.content.replace(chr(10), '<br>')}</p>
            
            <hr>
            <h3>💬 会話履歴 ({len(memory.conversation_history)}件)</h3>
            """
            
            for i, msg in enumerate(memory.conversation_history[-5:], 1):  # 最新5件を表示
                detail_html += f"<p style='margin: 5px 0; padding: 5px; background-color: #f5f5f5;'>{msg}</p>"
            
            if len(memory.conversation_history) > 5:
                detail_html += f"<p><i>...他 {len(memory.conversation_history) - 5}件</i></p>"
            
            self.memory_detail_text.setHtml(detail_html)
            
            # ボタンを有効化
            self.continue_conversation_button.setEnabled(True)
            self.edit_memory_button.setEnabled(True)
            self.delete_memory_button.setEnabled(True)
            
        except Exception as e:
            logging.error(f"記憶選択エラー: {e}", exc_info=True)
    
    def save_current_conversation_as_memory(self):
        """現在の会話を記憶として保存"""
        try:
            if not self.conversation_history:
                self.show_error("保存する会話がありません")
                return
            
            # ダイアログを表示
            dialog = MemorySaveDialog(self, self.conversation_history, 
                                     custom_gpt_manager.get_active_character())
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                memory_data = dialog.get_memory_data()
                
                # 記憶を保存
                memory_id = memory_manager.add_memory(
                    title=memory_data['title'],
                    content=memory_data['content'],
                    character_id=memory_data['character_id'],
                    character_name=memory_data['character_name'],
                    conversation_history=memory_data['conversation_history'],
                    category=memory_data['category'],
                    tags=memory_data['tags'],
                    importance=memory_data['importance']
                )
                
                if memory_id:
                    self.show_info(f"会話を記憶として保存しました: {memory_data['title']}")
                    self.load_memory_list()
                else:
                    self.show_error("記憶の保存に失敗しました")
            
        except Exception as e:
            logging.error(f"会話記憶保存エラー: {e}", exc_info=True)
            self.show_error(f"会話の保存中にエラーが発生しました: {str(e)}")
    
    def create_new_memory_manually(self):
        """手動で新規記憶を作成"""
        try:
            dialog = MemorySaveDialog(self, [], custom_gpt_manager.get_active_character(),
                                     manual_mode=True)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                memory_data = dialog.get_memory_data()
                
                memory_id = memory_manager.add_memory(
                    title=memory_data['title'],
                    content=memory_data['content'],
                    character_id=memory_data['character_id'],
                    character_name=memory_data['character_name'],
                    conversation_history=memory_data['conversation_history'],
                    category=memory_data['category'],
                    tags=memory_data['tags'],
                    importance=memory_data['importance']
                )
                
                if memory_id:
                    self.show_info(f"新規記憶を作成しました: {memory_data['title']}")
                    self.load_memory_list()
                else:
                    self.show_error("記憶の作成に失敗しました")
            
        except Exception as e:
            logging.error(f"新規記憶作成エラー: {e}", exc_info=True)
            self.show_error(f"記憶の作成中にエラーが発生しました: {str(e)}")
    
    def continue_conversation_from_memory(self):
        """記憶から会話を再開"""
        try:
            if not self.selected_memory_id:
                self.show_error("記憶が選択されていません")
                return
            
            memory = memory_manager.get_memory(self.selected_memory_id)
            if not memory:
                self.show_error("記憶が見つかりません")
                return
            
            # 確認ダイアログ
            reply = QtWidgets.QMessageBox.question(
                self,
                '会話を再開',
                f'「{memory.title}」の会話を再開しますか？\n\n'
                f'キャラクター: {memory.character_name}\n'
                f'会話履歴: {len(memory.conversation_history)}件\n\n'
                f'現在の会話履歴は置き換えられます。',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                # キャラクターを切り替え
                character = custom_gpt_manager.get_character_by_id(memory.character_id)
                if character:
                    custom_gpt_manager.set_active_character(character)
                    self.load_characters()  # キャラクター選択を更新
                    
                    # 会話履歴を復元
                    self.conversation_history = memory.conversation_history.copy()
                    
                    # チャット画面に履歴を表示
                    self.response_text.clear()
                    self.response_text.append(f"📝 記憶「{memory.title}」から会話を再開しました\n")
                    self.response_text.append(f"👤 キャラクター: {memory.character_name}\n")
                    self.response_text.append("=" * 50 + "\n")
                    
                    for msg in self.conversation_history:
                        self.response_text.append(msg)
                        self.response_text.append("")
                    
                    self.response_text.append("=" * 50)
                    self.response_text.append("💬 続きからお話しください")
                    
                    # チャットタブに切り替え
                    tab_widget = self.findChild(QtWidgets.QTabWidget)
                    if tab_widget:
                        tab_widget.setCurrentIndex(0)  # チャットタブ
                    
                    self.show_info(f"「{memory.title}」の会話を再開しました")
                    logging.info(f"記憶から会話を再開: {memory.title}")
                else:
                    self.show_error(f"キャラクター'{memory.character_name}'が見つかりません")
        
        except Exception as e:
            logging.error(f"会話再開エラー: {e}", exc_info=True)
            self.show_error(f"会話の再開中にエラーが発生しました: {str(e)}")
    
    def edit_selected_memory(self):
        """選択された記憶を編集"""
        try:
            if not self.selected_memory_id:
                self.show_error("記憶が選択されていません")
                return
            
            memory = memory_manager.get_memory(self.selected_memory_id)
            if not memory:
                self.show_error("記憶が見つかりません")
                return
            
            # 編集ダイアログを表示
            dialog = MemorySaveDialog(self, memory.conversation_history,
                                     custom_gpt_manager.get_character_by_id(memory.character_id),
                                     edit_mode=True, existing_memory=memory)
            
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                memory_data = dialog.get_memory_data()
                
                success = memory_manager.update_memory(
                    self.selected_memory_id,
                    title=memory_data['title'],
                    content=memory_data['content'],
                    category=memory_data['category'],
                    tags=memory_data['tags'],
                    importance=memory_data['importance']
                )
                
                if success:
                    self.show_info(f"記憶を更新しました: {memory_data['title']}")
                    self.load_memory_list()
                    # 選択状態を保持して再表示
                    for i in range(self.memory_list.count()):
                        item = self.memory_list.item(i)
                        if item.data(QtCore.Qt.UserRole) == self.selected_memory_id:
                            self.memory_list.setCurrentItem(item)
                            self.on_memory_selected(item)
                            break
                else:
                    self.show_error("記憶の更新に失敗しました")
        
        except Exception as e:
            logging.error(f"記憶編集エラー: {e}", exc_info=True)
            self.show_error(f"記憶の編集中にエラーが発生しました: {str(e)}")
    
    def delete_selected_memory(self):
        """選択された記憶を削除"""
        try:
            if not self.selected_memory_id:
                self.show_error("記憶が選択されていません")
                return
            
            memory = memory_manager.get_memory(self.selected_memory_id)
            if not memory:
                self.show_error("記憶が見つかりません")
                return
            
            # 確認ダイアログ
            reply = QtWidgets.QMessageBox.question(
                self,
                '記憶を削除',
                f'記憶「{memory.title}」を削除しますか？\n\nこの操作は取り消せません。',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                success = memory_manager.delete_memory(self.selected_memory_id)
                
                if success:
                    self.show_info(f"記憶を削除しました: {memory.title}")
                    self.selected_memory_id = None
                    self.memory_detail_text.clear()
                    self.continue_conversation_button.setEnabled(False)
                    self.edit_memory_button.setEnabled(False)
                    self.delete_memory_button.setEnabled(False)
                    self.load_memory_list()
                else:
                    self.show_error("記憶の削除に失敗しました")
        
        except Exception as e:
            logging.error(f"記憶削除エラー: {e}", exc_info=True)
            self.show_error(f"記憶の削除中にエラーが発生しました: {str(e)}")
    
    def show_memory_statistics(self):
        """記憶の統計情報を表示"""
        try:
            stats = memory_manager.get_statistics()
            
            stats_text = "📊 会話記憶 統計情報\n"
            stats_text += "=" * 40 + "\n\n"
            stats_text += f"総記憶数: {stats['total_count']}件\n\n"
            
            stats_text += "【カテゴリ別】\n"
            for category, count in stats['category_counts'].items():
                stats_text += f"  • {category}: {count}件\n"
            
            stats_text += "\n【キャラクター別】\n"
            for character, count in stats['character_counts'].items():
                stats_text += f"  • {character}: {count}件\n"
            
            stats_text += "\n【重要度別】\n"
            for importance, count in stats['importance_counts'].items():
                stats_text += f"  • {importance}: {count}件\n"
            
            stats_text += "\n【よくアクセスされる記憶 TOP5】\n"
            for i, memory in enumerate(stats['most_accessed'], 1):
                stats_text += f"  {i}. {memory.title} ({memory.access_count}回)\n"
            
            # ダイアログで表示
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle("記憶統計情報")
            msg_box.setText(stats_text)
            msg_box.setIcon(QtWidgets.QMessageBox.Information)
            msg_box.exec_()
            
        except Exception as e:
            logging.error(f"統計情報表示エラー: {e}", exc_info=True)
            self.show_error(f"統計情報の表示中にエラーが発生しました: {str(e)}")
    
    # ===== ドラッグ＆ドロップ機能 =====
    
    def dragEnterEvent(self, event):
        """ドラッグが開始されたとき"""
        try:
            mime_data = event.mimeData()
            
            # 画像データが直接含まれているかチェック（最優先）
            if mime_data.hasImage():
                event.acceptProposedAction()
                self.drag_active = True
                self._update_drag_visual(True, True)
                logging.info("ドラッグ開始: 画像データを直接検出")
                return
            
            if mime_data.hasUrls():
                # URLリスト（ファイルパスまたはWEB URL）が含まれている場合
                urls = mime_data.urls()
                
                # 少なくとも1つのファイルまたはWEB URLが対応形式か確認
                has_valid_file = False
                has_web_url = False
                for url in urls:
                    file_path = url.toLocalFile()
                    
                    # ローカルファイルのチェック
                    if file_path and self._is_supported_file(file_path):
                        has_valid_file = True
                        break
                    
                    # WEB URLのチェック
                    url_string = url.toString()
                    if self._is_web_url(url_string):
                        has_valid_file = True
                        has_web_url = True
                        break
                
                if has_valid_file:
                    event.acceptProposedAction()
                    self.drag_active = True
                    self._update_drag_visual(True, has_web_url)
                    logging.info("ドラッグ開始: 対応ファイルまたはWEB URLを検出")
                else:
                    event.ignore()
                    logging.warning("ドラッグ開始: 非対応ファイル形式")
            else:
                event.ignore()
        except Exception as e:
            logging.error(f"ドラッグ開始エラー: {e}", exc_info=True)
            event.ignore()
    
    def dragMoveEvent(self, event):
        """ドラッグ中の移動"""
        try:
            mime_data = event.mimeData()
            if mime_data.hasImage() or mime_data.hasUrls():
                event.acceptProposedAction()
        except Exception as e:
            logging.error(f"ドラッグ移動エラー: {e}", exc_info=True)
    
    def dragLeaveEvent(self, event):
        """ドラッグが領域外に出たとき"""
        try:
            self.drag_active = False
            self._update_drag_visual(False)
            logging.debug("ドラッグ終了: 領域外")
        except Exception as e:
            logging.error(f"ドラッグ離脱エラー: {e}", exc_info=True)
    
    def dropEvent(self, event):
        """ファイルがドロップされたとき"""
        try:
            self.drag_active = False
            self._update_drag_visual(False)
            
            mime_data = event.mimeData()
            
            # 画像データが直接含まれている場合（最優先）
            if mime_data.hasImage():
                if self._handle_dropped_image_data(mime_data):
                    event.acceptProposedAction()
                    self.show_info("画像を読み込みました")
                    logging.info("ドロップ完了: 画像データを直接処理")
                else:
                    self.show_error("画像データの処理に失敗しました")
                return
            
            urls = mime_data.urls()
            if not urls:
                return
            
            # ドロップされたファイルまたはWEB URLを処理
            processed_count = 0
            for url in urls:
                # ローカルファイルパスを取得
                file_path = url.toLocalFile()
                
                # ローカルファイルでない場合はWEB URLとして取得
                if not file_path:
                    file_path = url.toString()
                
                if self._handle_dropped_file(file_path):
                    processed_count += 1
            
            if processed_count > 0:
                event.acceptProposedAction()
                logging.info(f"ドロップ完了: {processed_count}件のファイルを処理")
                
                # 成功メッセージ
                if processed_count == 1:
                    self.show_info("ファイルを読み込みました")
                else:
                    self.show_info(f"{processed_count}件のファイルを読み込みました")
            else:
                logging.warning("ドロップ: 処理可能なファイルがありませんでした")
                self.show_error("対応していないファイル形式です")
        
        except Exception as e:
            logging.error(f"ドロップ処理エラー: {e}", exc_info=True)
            self.show_error(f"ファイルの処理中にエラーが発生しました: {str(e)}")
    
    def _is_supported_file(self, file_path: str) -> bool:
        """ファイルが対応形式かチェック"""
        try:
            file_extension = Path(file_path).suffix.lower()
            
            # 画像ファイル
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            if file_extension in image_extensions:
                return True
            
            # 将来の拡張用
            # document_extensions = ['.pdf', '.txt', '.docx']
            # data_extensions = ['.csv', '.xlsx']
            
            return False
        except Exception as e:
            logging.error(f"ファイル形式チェックエラー: {e}", exc_info=True)
            return False
    
    def _handle_dropped_file(self, file_path: str) -> bool:
        """ドロップされたファイルまたはWEB URLを処理"""
        try:
            # WEB URLかどうかをチェック
            if self._is_web_url(file_path):
                # WEB URLの処理
                return self._handle_dropped_web_image(file_path)
            
            # ローカルファイルの処理
            if not os.path.exists(file_path):
                logging.error(f"ファイルが存在しません: {file_path}")
                return False
            
            file_extension = Path(file_path).suffix.lower()
            
            # 画像ファイルの処理
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            if file_extension in image_extensions:
                return self._handle_dropped_image(file_path)
            
            # 将来の拡張: PDF、CSVなど
            
            logging.warning(f"非対応ファイル形式: {file_extension}")
            return False
            
        except Exception as e:
            logging.error(f"ファイル処理エラー: {e}", exc_info=True)
            return False
    
    def _handle_dropped_image(self, image_path: str) -> bool:
        """ドロップされた画像を処理"""
        try:
            # 画像認識が利用可能かチェック
            if not self.image_recognition_available:
                self.show_error("画像認識機能が利用できません")
                return False
            
            # 画像を設定（既存のメソッドを使用）
            self.set_selected_image(image_path)
            
            # 画像パネルを自動展開
            if hasattr(self, 'image_detail_panel') and not self.image_detail_panel.isVisible():
                self.toggle_image_panel()
            
            logging.info(f"画像をドラッグ＆ドロップで読み込みました: {image_path}")
            return True
            
        except Exception as e:
            logging.error(f"画像ドロップ処理エラー: {e}", exc_info=True)
            return False
    
    def _update_drag_visual(self, is_dragging: bool, is_web_url: bool = False):
        """ドラッグ中のビジュアルフィードバック"""
        try:
            if is_dragging:
                # ドラッグ中のスタイル
                self.setStyleSheet("""
                    QWidget {
                        background-color: #e3f2fd;
                        border: 3px dashed #2196F3;
                    }
                """)
                
                # ステータスバー的なメッセージ表示
                if hasattr(self, 'response_text'):
                    cursor = self.response_text.textCursor()
                    cursor.movePosition(QtGui.QTextCursor.End)
                    original_color = self.response_text.textColor()
                    self.response_text.setTextColor(QtGui.QColor("#2196F3"))
                    
                    # WEB URLかローカルファイルかでメッセージを変更
                    if is_web_url:
                        self.response_text.append("\n🌐 WEB画像を検出しました\n📎 ダウンロードしてここにドロップしてください...")
                    else:
                        self.response_text.append("\n📎 ファイルをここにドロップしてください...")
                    
                    self.response_text.setTextColor(original_color)
            else:
                # 通常のスタイルに戻す
                self.setStyleSheet("")
                self.apply_theme()  # テーマを再適用
                
                # ドラッグメッセージを削除
                if hasattr(self, 'response_text'):
                    text = self.response_text.toPlainText()
                    # 両方のメッセージパターンに対応
                    if "📎 ファイルをここにドロップしてください..." in text or "🌐 WEB画像を検出しました" in text:
                        # 最後の行を削除（WEB URLの場合は2行削除）
                        cursor = self.response_text.textCursor()
                        cursor.movePosition(QtGui.QTextCursor.End)
                        
                        # WEB URLメッセージの場合は2行削除
                        if "🌐 WEB画像を検出しました" in text:
                            for _ in range(2):
                                cursor.movePosition(QtGui.QTextCursor.StartOfBlock, QtGui.QTextCursor.KeepAnchor)
                                cursor.movePosition(QtGui.QTextCursor.Left, QtGui.QTextCursor.KeepAnchor, 1)
                                cursor.removeSelectedText()
                                cursor.deletePreviousChar()
                        else:
                            cursor.movePosition(QtGui.QTextCursor.StartOfBlock, QtGui.QTextCursor.KeepAnchor)
                            cursor.movePosition(QtGui.QTextCursor.Left, QtGui.QTextCursor.KeepAnchor, 1)
                            cursor.removeSelectedText()
                            cursor.deletePreviousChar()
        
        except Exception as e:
            logging.error(f"ドラッグビジュアル更新エラー: {e}", exc_info=True)
    
    # ===== WEB画像ドラッグ＆ドロップ機能 =====
    
    def _is_web_url(self, url_string: str) -> bool:
        """WEB URLかどうか判定"""
        try:
            return url_string.startswith('http://') or url_string.startswith('https://')
        except Exception as e:
            logging.error(f"URL判定エラー: {e}", exc_info=True)
            return False
    
    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Content-Typeヘッダーから拡張子を取得"""
        try:
            # Content-Typeから拡張子をマッピング
            content_type_map = {
                'image/jpeg': '.jpg',
                'image/jpg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/webp': '.webp',
                'image/bmp': '.bmp',
                'image/tiff': '.tiff',
            }
            
            # Content-Typeから拡張子を取得（パラメータを除去）
            content_type_clean = content_type.split(';')[0].strip().lower()
            extension = content_type_map.get(content_type_clean, '.jpg')
            
            logging.debug(f"Content-Type '{content_type}' から拡張子 '{extension}' を取得")
            return extension
            
        except Exception as e:
            logging.error(f"拡張子取得エラー: {e}", exc_info=True)
            return '.jpg'  # デフォルトは.jpg
    
    def _download_web_image(self, url: str) -> Optional[str]:
        """
        WEB URLから画像をダウンロードして一時ファイルとして保存
        
        Args:
            url: 画像のURL
            
        Returns:
            一時ファイルの絶対パス（失敗時はNone）
        """
        progress_dialog = None
        temp_file_path = None
        
        try:
            logging.info(f"WEB画像のダウンロード開始: {url}")
            
            # プログレスダイアログの作成
            progress_dialog = QtWidgets.QProgressDialog(
                "画像をダウンロード中...",
                "キャンセル",
                0,
                100,
                self
            )
            progress_dialog.setWindowTitle("ダウンロード")
            progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setValue(0)
            
            # URLの短縮表示
            display_url = url if len(url) <= 60 else url[:57] + "..."
            progress_dialog.setLabelText(f"画像をダウンロード中...\n{display_url}")
            
            # User-Agentヘッダーを設定（サーバーブロック回避）
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # ダウンロード開始（ストリーミング）
            response = requests.get(
                url,
                headers=headers,
                stream=True,
                timeout=(5, 10),  # 接続5秒、読み取り10秒
                allow_redirects=True
            )
            
            # HTTPステータスコードチェック
            if response.status_code == 404:
                self.show_error(f"画像が見つかりませんでした (404)\n詳細: {url}")
                logging.error(f"404 Not Found: {url}")
                return None
            elif response.status_code != 200:
                self.show_error(f"ダウンロードエラー (HTTP {response.status_code})\n詳細: {url}")
                logging.error(f"HTTP {response.status_code}: {url}")
                return None
            
            # Content-Typeチェック
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                # HTMLページの場合はより分かりやすいエラーメッセージ
                if 'text/html' in content_type:
                    self.show_error(
                        "画像ページのURLではなく、画像そのもののURLが必要です\n\n"
                        "💡 ヒント:\n"
                        "・画像を右クリック → 「画像をコピー」→ ここに貼り付け\n"
                        "・または画像を右クリック → 「画像アドレスをコピー」してブラウザで開いてからドラッグ\n"
                        f"\n詳細: このURLはHTMLページです ({content_type})"
                    )
                else:
                    self.show_error(f"対応していない画像形式です\n詳細: Content-Type={content_type}")
                logging.error(f"非画像形式: {content_type}")
                return None
            
            # ファイルサイズチェック
            content_length = response.headers.get('Content-Length')
            max_size = 10 * 1024 * 1024  # 10MB
            
            if content_length and int(content_length) > max_size:
                size_mb = int(content_length) / (1024 * 1024)
                self.show_error(f"画像サイズが大きすぎます（10MB超過）\n詳細: {size_mb:.2f}MB")
                logging.error(f"ファイルサイズ超過: {size_mb:.2f}MB")
                return None
            
            # 拡張子を取得
            extension = self._get_extension_from_content_type(content_type)
            
            # 一時ファイルを作成
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            temp_file = tempfile.NamedTemporaryFile(
                suffix=extension,
                prefix=f'ai_web_image_{timestamp}_',
                delete=False
            )
            temp_file_path = temp_file.name
            
            # ダウンロード処理
            downloaded_size = 0
            total_size = int(content_length) if content_length else 0
            chunk_size = 8192
            
            for chunk in response.iter_content(chunk_size=chunk_size):
                # キャンセルチェック
                if progress_dialog.wasCanceled():
                    temp_file.close()
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                    logging.info("ダウンロードがユーザーによってキャンセルされました")
                    return None
                
                if chunk:
                    temp_file.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # サイズ制限チェック
                    if downloaded_size > max_size:
                        temp_file.close()
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                        size_mb = downloaded_size / (1024 * 1024)
                        self.show_error(f"画像サイズが大きすぎます（10MB超過）\n詳細: {size_mb:.2f}MB")
                        logging.error(f"ダウンロード中にサイズ超過: {size_mb:.2f}MB")
                        return None
                    
                    # プログレスバー更新
                    if total_size > 0:
                        progress = int((downloaded_size / total_size) * 100)
                        progress_dialog.setValue(progress)
                        downloaded_mb = downloaded_size / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        progress_dialog.setLabelText(
                            f"画像をダウンロード中... ({downloaded_mb:.2f}MB / {total_mb:.2f}MB)\n{display_url}"
                        )
                    else:
                        # サイズ不明の場合
                        downloaded_mb = downloaded_size / (1024 * 1024)
                        progress_dialog.setLabelText(
                            f"画像をダウンロード中... ({downloaded_mb:.2f}MB)\n{display_url}"
                        )
            
            temp_file.close()
            progress_dialog.setValue(100)
            
            # 一時ファイルリストに追加
            self.temp_image_files.append(temp_file_path)
            
            logging.info(f"WEB画像をダウンロードしました: {url}")
            logging.info(f"一時ファイルに保存: {temp_file_path}")
            
            return temp_file_path
            
        except requests.exceptions.Timeout as e:
            self.show_error(f"ダウンロードがタイムアウトしました\n詳細: {str(e)}")
            logging.error(f"タイムアウトエラー: {url} - {e}", exc_info=True)
            return None
            
        except requests.exceptions.ConnectionError as e:
            self.show_error(f"ネットワーク接続エラー\n詳細: {str(e)}")
            logging.error(f"接続エラー: {url} - {e}", exc_info=True)
            return None
            
        except requests.exceptions.SSLError as e:
            self.show_error(f"SSL証明書エラー\n詳細: {str(e)}")
            logging.error(f"SSLエラー: {url} - {e}", exc_info=True)
            return None
            
        except Exception as e:
            self.show_error(f"WEB画像のダウンロード中にエラーが発生しました\n詳細: {str(e)}")
            logging.error(f"WEB画像ダウンロードエラー: {url} - {e}", exc_info=True)
            
            # エラー時に一時ファイルを削除
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            
            return None
            
        finally:
            # プログレスダイアログを閉じる
            if progress_dialog:
                progress_dialog.close()
    
    def _handle_dropped_web_image(self, url: str) -> bool:
        """
        ドロップされたWEB画像を処理
        
        Args:
            url: 画像のURL
            
        Returns:
            成功=True, 失敗=False
        """
        try:
            logging.info(f"WEB画像の処理開始: {url}")
            
            # 画像認識が利用可能かチェック
            if not self.image_recognition_available:
                self.show_error("画像認識機能が利用できません")
                return False
            
            # WEB URLから画像をダウンロード
            temp_file_path = self._download_web_image(url)
            
            if not temp_file_path:
                # ダウンロード失敗（エラーメッセージは_download_web_image内で表示済み）
                return False
            
            # 画像を設定（既存のメソッドを使用）
            self.set_selected_image(temp_file_path)
            
            # 画像パネルを自動展開
            if hasattr(self, 'image_detail_panel') and not self.image_detail_panel.isVisible():
                self.toggle_image_panel()
            
            logging.info(f"WEB画像をドラッグ＆ドロップで読み込みました: {url}")
            return True
            
        except Exception as e:
            logging.error(f"WEB画像ドロップ処理エラー: {e}", exc_info=True)
            self.show_error(f"WEB画像の処理中にエラーが発生しました\n詳細: {str(e)}")
            return False
    
    def _handle_dropped_image_data(self, mime_data) -> bool:
        """
        ドロップされた画像データを直接処理
        
        Args:
            mime_data: QMimeData オブジェクト
            
        Returns:
            成功=True, 失敗=False
        """
        try:
            logging.info("画像データの直接処理を開始")
            
            # 画像認識が利用可能かチェック
            if not self.image_recognition_available:
                self.show_error("画像認識機能が利用できません")
                return False
            
            # QImageとして画像データを取得
            image = mime_data.imageData()
            if image is None or image.isNull():
                logging.error("画像データの取得に失敗しました")
                return False
            
            # QImageをQPixmapに変換
            pixmap = QtGui.QPixmap.fromImage(image)
            if pixmap.isNull():
                logging.error("画像の変換に失敗しました")
                return False
            
            # 一時ファイルとして保存
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.png',
                prefix=f'ai_dropped_image_{timestamp}_',
                delete=False
            )
            temp_file_path = temp_file.name
            temp_file.close()
            
            # 画像を保存
            if not pixmap.save(temp_file_path, 'PNG'):
                logging.error(f"画像の保存に失敗しました: {temp_file_path}")
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                return False
            
            # 一時ファイルリストに追加
            self.temp_image_files.append(temp_file_path)
            
            # 画像を設定（既存のメソッドを使用）
            self.set_selected_image(temp_file_path)
            
            # 画像パネルを自動展開
            if hasattr(self, 'image_detail_panel') and not self.image_detail_panel.isVisible():
                self.toggle_image_panel()
            
            logging.info(f"画像データを一時ファイルに保存しました: {temp_file_path}")
            return True
            
        except Exception as e:
            logging.error(f"画像データ処理エラー: {e}", exc_info=True)
            self.show_error(f"画像データの処理中にエラーが発生しました\n詳細: {str(e)}")
            return False
    
    def _cleanup_temp_images(self):
        """アプリ終了時に一時画像ファイルを削除"""
        try:
            if not self.temp_image_files:
                return
            
            deleted_count = 0
            for file_path in self.temp_image_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                        logging.debug(f"一時ファイルを削除: {file_path}")
                except Exception as e:
                    logging.warning(f"一時ファイルの削除に失敗: {file_path} - {e}")
            
            if deleted_count > 0:
                logging.info(f"{deleted_count}件の一時ファイルを削除しました")
            
            self.temp_image_files.clear()
            
        except Exception as e:
            logging.error(f"一時ファイル削除エラー: {e}", exc_info=True)
    
    # ===== クリップボードから画像を貼り付け =====
    
    def keyPressEvent(self, event):
        """キーボードイベント処理"""
        try:
            # Ctrl + V（貼り付け）を検出
            if event.key() == QtCore.Qt.Key_V and event.modifiers() == QtCore.Qt.ControlModifier:
                self._paste_image_from_clipboard()
                event.accept()
            else:
                # その他のキーイベントは通常通り処理
                super().keyPressEvent(event)
        except Exception as e:
            logging.error(f"キーイベント処理エラー: {e}", exc_info=True)
            super().keyPressEvent(event)
    
    def _paste_image_from_clipboard(self):
        """クリップボードから画像を貼り付け"""
        try:
            logging.info("クリップボードから画像を貼り付け中...")
            
            # 画像認識が利用可能かチェック
            if not self.image_recognition_available:
                self.show_error("画像認識機能が利用できません")
                return
            
            # クリップボードを取得
            clipboard = QtWidgets.QApplication.clipboard()
            mime_data = clipboard.mimeData()
            
            # 画像データがあるかチェック
            if not mime_data.hasImage():
                # 画像がない場合はURLをチェック
                if mime_data.hasUrls():
                    urls = mime_data.urls()
                    if urls:
                        url_string = urls[0].toString()
                        if self._is_web_url(url_string):
                            # WEB URLの場合はダウンロード
                            self.show_info("画像URLをクリップボードから検出しました。ダウンロード中...")
                            if self._handle_dropped_web_image(url_string):
                                self.show_info("画像を読み込みました")
                            return
                        else:
                            # ローカルファイルの場合
                            file_path = urls[0].toLocalFile()
                            if file_path and self._is_supported_file(file_path):
                                if self._handle_dropped_image(file_path):
                                    self.show_info("画像を読み込みました")
                                return
                
                self.show_info("クリップボードに画像がありません\n\n💡 ヒント:\n画像を右クリック → 「画像をコピー」を選択してください")
                logging.info("クリップボードに画像データがありません")
                return
            
            # 画像データを処理
            image = mime_data.imageData()
            if image is None or image.isNull():
                self.show_error("画像データの読み込みに失敗しました")
                logging.error("クリップボードの画像データが無効です")
                return
            
            # QImageをQPixmapに変換
            pixmap = QtGui.QPixmap.fromImage(image)
            if pixmap.isNull():
                self.show_error("画像の変換に失敗しました")
                logging.error("画像の変換に失敗しました")
                return
            
            # 一時ファイルとして保存
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.png',
                prefix=f'ai_clipboard_image_{timestamp}_',
                delete=False
            )
            temp_file_path = temp_file.name
            temp_file.close()
            
            # 画像を保存
            if not pixmap.save(temp_file_path, 'PNG'):
                self.show_error("画像の保存に失敗しました")
                logging.error(f"画像の保存に失敗しました: {temp_file_path}")
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                return
            
            # 一時ファイルリストに追加
            self.temp_image_files.append(temp_file_path)
            
            # 画像を設定（既存のメソッドを使用）
            self.set_selected_image(temp_file_path)
            
            # 画像パネルを自動展開
            if hasattr(self, 'image_detail_panel') and not self.image_detail_panel.isVisible():
                self.toggle_image_panel()
            
            self.show_info("📋 クリップボードから画像を読み込みました")
            logging.info(f"クリップボードから画像を読み込みました: {temp_file_path}")
            
        except Exception as e:
            logging.error(f"クリップボード貼り付けエラー: {e}", exc_info=True)
            self.show_error(f"画像の貼り付け中にエラーが発生しました\n詳細: {str(e)}")
    
    # ===== アプリケーション終了処理 =====
    
    def closeEvent(self, event):
        """アプリケーション終了時の処理"""
        try:
            logging.info("アプリケーションを終了しています...")
            
            # 一時画像ファイルを削除
            self._cleanup_temp_images()
            
            # 既存の終了処理があればここに追加
            
            event.accept()
            logging.info("アプリケーションが正常に終了しました")
            
        except Exception as e:
            logging.error(f"終了処理エラー: {e}", exc_info=True)
            event.accept()  # エラーでも終了を許可

# 古いテンプレート管理クラスは削除されました
# 新しいカスタムGPT管理クラスを追加します

class CharacterCreatorDialog(QtWidgets.QDialog):
    """完全自由キャラクター作成ダイアログ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("オリジナルキャラクター作成")
        self.setModal(True)
        self.resize(900, 700)
        
        self.init_ui()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QtWidgets.QVBoxLayout(self)
        font = QtGui.QFont("メイリオ", 10)
        
        # 説明ラベル
        explanation = QtWidgets.QLabel("どんなキャラクターでも自由に作成できます。すべての項目は任意入力です。")
        explanation.setWordWrap(True)
        explanation.setStyleSheet("QLabel { background-color: #e3f2fd; padding: 10px; border-radius: 5px; }")
        layout.addWidget(explanation)
        
        # スクロールエリア
        scroll = QtWidgets.QScrollArea()
        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)
        
        # キャラクター名
        name_group = QtWidgets.QGroupBox("キャラクター名 *")
        name_layout = QtWidgets.QVBoxLayout()
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("例: プログラミング先生、関西弁のお姉さん、ビジネスコンサルタント太郎")
        name_layout.addWidget(self.name_input)
        name_group.setLayout(name_layout)
        scroll_layout.addWidget(name_group)
        
        # 性格・キャラクター設定
        personality_group = QtWidgets.QGroupBox("🎭 性格・キャラクター設定")
        personality_layout = QtWidgets.QVBoxLayout()
        self.personality_input = QtWidgets.QTextEdit()
        self.personality_input.setPlaceholderText(
            "自由に記述してください\n\n"
            "例:\n"
            "• 優しくて知識豊富な先生。厳格だけど面倒見が良い\n"
            "• フレンドリーで何でも相談できる相手\n"
            "• ちょっと毒舌だけど的確なアドバイスをくれる\n"
            "• 明るくて元気。いつも前向きで人を励ますのが上手"
        )
        self.personality_input.setMaximumHeight(120)
        personality_layout.addWidget(self.personality_input)
        personality_group.setLayout(personality_layout)
        scroll_layout.addWidget(personality_group)
        
        # 話し方・口調
        speaking_group = QtWidgets.QGroupBox("💬 話し方・口調")
        speaking_layout = QtWidgets.QVBoxLayout()
        self.speaking_input = QtWidgets.QTextEdit()
        self.speaking_input.setPlaceholderText(
            "例:\n"
            "• 関西弁で親しみやすく話す（「〜やで」「〜やんか」）\n"
            "• 丁寧語で上品に話す（「〜ですね」「〜ましょう」）\n"
            "• ため口でフランクに話す\n"
            "• 敬語だけど親しみやすい口調"
        )
        self.speaking_input.setMaximumHeight(100)
        speaking_layout.addWidget(self.speaking_input)
        speaking_group.setLayout(speaking_layout)
        scroll_layout.addWidget(speaking_group)
        
        # 専門分野・得意なこと
        specialization_group = QtWidgets.QGroupBox("🧠 専門分野・得意なこと")
        specialization_layout = QtWidgets.QVBoxLayout()
        self.specialization_input = QtWidgets.QTextEdit()
        self.specialization_input.setPlaceholderText(
            "例:\n"
            "• Python、JavaScript、データベース設計\n"
            "• ビジネス戦略、財務分析、プレゼンテーション\n"
            "• 小説執筆、創作技法、ストーリー構成\n"
            "• 料理、生活の知恵、家事のコツ"
        )
        self.specialization_input.setMaximumHeight(100)
        specialization_layout.addWidget(self.specialization_input)
        specialization_group.setLayout(specialization_layout)
        scroll_layout.addWidget(specialization_group)
        
        # 応答スタイル
        response_group = QtWidgets.QGroupBox("📝 応答スタイル")
        response_layout = QtWidgets.QVBoxLayout()
        self.response_input = QtWidgets.QTextEdit()
        self.response_input.setPlaceholderText(
            "例:\n"
            "• 必ずサンプルコードを含める\n"
            "• 段階的に分かりやすく説明する\n"
            "• 簡潔で要点を整理した回答\n"
            "• 具体例をたくさん使って説明"
        )
        self.response_input.setMaximumHeight(100)
        response_layout.addWidget(self.response_input)
        response_group.setLayout(response_layout)
        scroll_layout.addWidget(response_group)
        
        # その他の設定（展開可能）
        other_group = QtWidgets.QGroupBox("⚙️ その他の設定（任意）")
        other_layout = QtWidgets.QVBoxLayout()
        
        # 背景・設定
        background_label = QtWidgets.QLabel("背景・設定:")
        self.background_input = QtWidgets.QTextEdit()
        self.background_input.setPlaceholderText("キャラクターの背景や設定を自由に記述...")
        self.background_input.setMaximumHeight(80)
        
        # 決まり文句・口癖
        catchphrase_label = QtWidgets.QLabel("決まり文句・口癖:")
        self.catchphrase_input = QtWidgets.QLineEdit()
        self.catchphrase_input.setPlaceholderText("例: 質問あるかね？、なんでも聞いてや〜、一緒に考えましょう")
        
        # 挨拶の仕方
        greeting_label = QtWidgets.QLabel("挨拶の仕方:")
        self.greeting_input = QtWidgets.QLineEdit()
        self.greeting_input.setPlaceholderText("例: 質問あるかね？、こんにちは！、お疲れ様です")
        
        other_layout.addWidget(background_label)
        other_layout.addWidget(self.background_input)
        other_layout.addWidget(catchphrase_label)
        other_layout.addWidget(self.catchphrase_input)
        other_layout.addWidget(greeting_label)
        other_layout.addWidget(self.greeting_input)
        other_group.setLayout(other_layout)
        scroll_layout.addWidget(other_group)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # ボタン
        button_layout = QtWidgets.QHBoxLayout()
        
        self.preview_button = QtWidgets.QPushButton("プレビュー")
        self.preview_button.clicked.connect(self.show_preview)
        
        self.create_button = QtWidgets.QPushButton("キャラクター作成")
        self.create_button.clicked.connect(self.create_character)
        
        self.cancel_button = QtWidgets.QPushButton("キャンセル")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.preview_button)
        button_layout.addStretch()
        button_layout.addWidget(self.create_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # フォント設定
        for widget in [self.name_input, self.personality_input, self.speaking_input,
                      self.specialization_input, self.response_input, self.background_input,
                      self.catchphrase_input, self.greeting_input, self.preview_button,
                      self.create_button, self.cancel_button]:
            widget.setFont(font)
    
    def show_preview(self):
        """プレビューダイアログを表示"""
        character_data = self.get_character_data()
        if not character_data['name'].strip():
            QtWidgets.QMessageBox.warning(self, "入力エラー", "キャラクター名を入力してください。")
            return
        
        # テンポラリキャラクターを作成
        temp_character = CustomGPT(**character_data)
        system_prompt = temp_character.build_system_prompt()
        
        preview_dialog = CharacterPreviewDialog(self, character_data['name'], system_prompt)
        preview_dialog.exec_()
    
    def create_character(self):
        """キャラクターを作成"""
        character_data = self.get_character_data()
        
        # 入力検証
        if not character_data['name'].strip():
            QtWidgets.QMessageBox.warning(self, "入力エラー", "キャラクター名を入力してください。")
            return
        
        # キャラクター作成
        if custom_gpt_manager.create_character(**character_data):
            QtWidgets.QMessageBox.information(
                self, "成功", 
                f"キャラクター「{character_data['name']}」を作成しました！"
            )
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(
                self, "エラー", 
                "キャラクターの作成に失敗しました。\n同じ名前のキャラクターが既に存在する可能性があります。"
            )
    
    def get_character_data(self):
        """入力されたキャラクターデータを取得"""
        return {
            'name': self.name_input.text().strip(),
            'personality': self.personality_input.toPlainText().strip(),
            'speaking_style': self.speaking_input.toPlainText().strip(),
            'specialization': self.specialization_input.toPlainText().strip(),
            'response_style': self.response_input.toPlainText().strip(),
            'background': self.background_input.toPlainText().strip(),
            'catchphrase': self.catchphrase_input.text().strip(),
            'greeting': self.greeting_input.text().strip()
        }

class CharacterPreviewDialog(QtWidgets.QDialog):
    """キャラクタープレビューダイアログ"""
    
    def __init__(self, parent, character_name, system_prompt):
        super().__init__(parent)
        self.setWindowTitle(f"キャラクタープレビュー - {character_name}")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # 説明
        explanation = QtWidgets.QLabel("以下のシステムプロンプトでAIが動作します：")
        layout.addWidget(explanation)
        
        # システムプロンプト表示
        self.prompt_display = QtWidgets.QTextEdit()
        self.prompt_display.setPlainText(system_prompt)
        self.prompt_display.setReadOnly(True)
        self.prompt_display.setFont(QtGui.QFont("Consolas", 9))
        layout.addWidget(self.prompt_display)
        
        # ボタン
        button_layout = QtWidgets.QHBoxLayout()
        
        self.ok_button = QtWidgets.QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)

class CharacterManagerDialog(QtWidgets.QDialog):
    """キャラクター管理ダイアログ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("キャラクター管理")
        self.setModal(True)
        self.resize(900, 600)
        
        self.init_ui()
        self.load_character_list()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QtWidgets.QVBoxLayout(self)
        font = QtGui.QFont("メイリオ", 10)
        
        # 検索機能
        search_layout = QtWidgets.QHBoxLayout()
        search_label = QtWidgets.QLabel("検索:")
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("キャラクター名、性格、専門分野で検索...")
        self.search_input.textChanged.connect(self.filter_characters)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # キャラクターリスト
        self.character_list = QtWidgets.QListWidget()
        self.character_list.itemSelectionChanged.connect(self.on_character_selection)
        layout.addWidget(self.character_list)
        
        # ボタンレイアウト
        button_layout = QtWidgets.QHBoxLayout()
        
        self.edit_button = QtWidgets.QPushButton("編集")
        self.edit_button.clicked.connect(self.edit_character)
        self.edit_button.setEnabled(False)
        
        self.clone_button = QtWidgets.QPushButton("複製")
        self.clone_button.clicked.connect(self.clone_character)
        self.clone_button.setEnabled(False)
        
        self.delete_button = QtWidgets.QPushButton("削除")
        self.delete_button.clicked.connect(self.delete_character)
        self.delete_button.setEnabled(False)
        
        self.close_button = QtWidgets.QPushButton("閉じる")
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.clone_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        # 統計情報ラベル
        self.stats_label = QtWidgets.QLabel()
        layout.addWidget(self.stats_label)
        
        # フォント設定
        for widget in [self.search_input, self.character_list, self.edit_button,
                      self.clone_button, self.delete_button, self.close_button, self.stats_label]:
            widget.setFont(font)
    
    def load_character_list(self):
        """キャラクターリストを読み込み"""
        self.character_list.clear()
        characters = custom_gpt_manager.get_all_characters()
        
        for character in characters:
            item_text = f"{character.name}"
            if character.specialization:
                spec_short = character.specialization[:30] + "..." if len(character.specialization) > 30 else character.specialization
                item_text += f" ({spec_short})"
            
            if character.is_default:
                item_text += " [デフォルト]"
            
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, character)
            
            # ツールチップに詳細情報を設定
            tooltip = f"名前: {character.name}\n"
            if character.personality:
                tooltip += f"性格: {character.personality[:100]}...\n"
            if character.specialization:
                tooltip += f"専門分野: {character.specialization[:100]}...\n"
            tooltip += f"使用回数: {character.usage_count}回\n"
            tooltip += f"作成日: {character.created_at[:10]}"
            item.setToolTip(tooltip)
            
            self.character_list.addItem(item)
        
        # 統計情報を更新
        self.update_stats()
    
    def filter_characters(self, text):
        """キャラクターをフィルタリング"""
        if not text:
            self.load_character_list()
            return
        
        search_results = custom_gpt_manager.search_characters(text)
        
        self.character_list.clear()
        for character in search_results:
            item_text = f"{character.name}"
            if character.specialization:
                spec_short = character.specialization[:30] + "..." if len(character.specialization) > 30 else character.specialization
                item_text += f" ({spec_short})"
            
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, character)
            self.character_list.addItem(item)
        
        self.update_stats(f"検索結果: {len(search_results)}件")
    
    def update_stats(self, custom_text=None):
        """統計情報を更新"""
        if custom_text:
            self.stats_label.setText(custom_text)
        else:
            total_count = custom_gpt_manager.get_character_count()
            max_count = custom_gpt_manager.max_characters
            self.stats_label.setText(f"キャラクター: {total_count}/{max_count}件")
    
    def on_character_selection(self):
        """キャラクター選択時の処理"""
        has_selection = len(self.character_list.selectedItems()) > 0
        selected_character = None
        
        if has_selection:
            selected_character = self.character_list.selectedItems()[0].data(QtCore.Qt.UserRole)
        
        self.edit_button.setEnabled(has_selection)
        self.clone_button.setEnabled(has_selection)
        # デフォルトキャラクターは削除不可
        self.delete_button.setEnabled(has_selection and selected_character and not selected_character.is_default)
    
    def edit_character(self):
        """キャラクター編集"""
        selected_items = self.character_list.selectedItems()
        if not selected_items:
            return
        
        character = selected_items[0].data(QtCore.Qt.UserRole)
        dialog = CharacterEditDialog(self, character)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.load_character_list()
            QtWidgets.QMessageBox.information(self, "成功", "キャラクターを更新しました。")
    
    def clone_character(self):
        """キャラクター複製"""
        selected_items = self.character_list.selectedItems()
        if not selected_items:
            return
        
        original_character = selected_items[0].data(QtCore.Qt.UserRole)
        
        # 新しい名前を入力
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "キャラクター複製", 
            f"「{original_character.name}」のコピーの名前を入力してください:",
            text=f"{original_character.name}のコピー"
        )
        
        if ok and new_name.strip():
            cloned_character = original_character.clone(new_name.strip())
            if custom_gpt_manager.create_character(**cloned_character.to_dict()):
                self.load_character_list()
                QtWidgets.QMessageBox.information(self, "成功", f"キャラクター「{new_name}」を作成しました。")
            else:
                QtWidgets.QMessageBox.warning(self, "エラー", "キャラクターの複製に失敗しました。")
    
    def delete_character(self):
        """キャラクター削除"""
        selected_items = self.character_list.selectedItems()
        if not selected_items:
            return
        
        character = selected_items[0].data(QtCore.Qt.UserRole)
        
        # 確認ダイアログ
        reply = QtWidgets.QMessageBox.question(
            self, "確認", 
            f"キャラクター「{character.name}」を削除しますか？\n会話履歴も一緒に削除されます。",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            if custom_gpt_manager.delete_character(character.character_id):
                self.load_character_list()
                QtWidgets.QMessageBox.information(self, "成功", "キャラクターを削除しました。")
            else:
                QtWidgets.QMessageBox.warning(self, "エラー", "キャラクターの削除に失敗しました。")

class CharacterEditDialog(QtWidgets.QDialog):
    """キャラクター編集ダイアログ"""
    
    def __init__(self, parent, character):
        super().__init__(parent)
        self.character = character
        self.setWindowTitle(f"キャラクター編集 - {character.name}")
        self.setModal(True)
        self.resize(900, 700)
        
        self.init_ui()
        self.load_character_data()
    
    def init_ui(self):
        """UIを初期化（CharacterCreatorDialogと同様）"""
        layout = QtWidgets.QVBoxLayout(self)
        font = QtGui.QFont("メイリオ", 10)
        
        # 説明ラベル
        explanation = QtWidgets.QLabel(f"「{self.character.name}」の設定を編集します。")
        explanation.setWordWrap(True)
        explanation.setStyleSheet("QLabel { background-color: #fff3e0; padding: 10px; border-radius: 5px; }")
        layout.addWidget(explanation)
        
        # スクロールエリア
        scroll = QtWidgets.QScrollArea()
        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)
        
        # キャラクター名
        name_group = QtWidgets.QGroupBox("キャラクター名 *")
        name_layout = QtWidgets.QVBoxLayout()
        self.name_input = QtWidgets.QLineEdit()
        name_layout.addWidget(self.name_input)
        name_group.setLayout(name_layout)
        scroll_layout.addWidget(name_group)
        
        # 性格・キャラクター設定
        personality_group = QtWidgets.QGroupBox("🎭 性格・キャラクター設定")
        personality_layout = QtWidgets.QVBoxLayout()
        self.personality_input = QtWidgets.QTextEdit()
        self.personality_input.setMaximumHeight(120)
        personality_layout.addWidget(self.personality_input)
        personality_group.setLayout(personality_layout)
        scroll_layout.addWidget(personality_group)
        
        # 話し方・口調
        speaking_group = QtWidgets.QGroupBox("💬 話し方・口調")
        speaking_layout = QtWidgets.QVBoxLayout()
        self.speaking_input = QtWidgets.QTextEdit()
        self.speaking_input.setMaximumHeight(100)
        speaking_layout.addWidget(self.speaking_input)
        speaking_group.setLayout(speaking_layout)
        scroll_layout.addWidget(speaking_group)
        
        # 専門分野・得意なこと
        specialization_group = QtWidgets.QGroupBox("🧠 専門分野・得意なこと")
        specialization_layout = QtWidgets.QVBoxLayout()
        self.specialization_input = QtWidgets.QTextEdit()
        self.specialization_input.setMaximumHeight(100)
        specialization_layout.addWidget(self.specialization_input)
        specialization_group.setLayout(specialization_layout)
        scroll_layout.addWidget(specialization_group)
        
        # 応答スタイル
        response_group = QtWidgets.QGroupBox("📝 応答スタイル")
        response_layout = QtWidgets.QVBoxLayout()
        self.response_input = QtWidgets.QTextEdit()
        self.response_input.setMaximumHeight(100)
        response_layout.addWidget(self.response_input)
        response_group.setLayout(response_layout)
        scroll_layout.addWidget(response_group)
        
        # その他の設定
        other_group = QtWidgets.QGroupBox("⚙️ その他の設定（任意）")
        other_layout = QtWidgets.QVBoxLayout()
        
        # 背景・設定
        background_label = QtWidgets.QLabel("背景・設定:")
        self.background_input = QtWidgets.QTextEdit()
        self.background_input.setMaximumHeight(80)
        
        # 決まり文句・口癖
        catchphrase_label = QtWidgets.QLabel("決まり文句・口癖:")
        self.catchphrase_input = QtWidgets.QLineEdit()
        
        # 挨拶の仕方
        greeting_label = QtWidgets.QLabel("挨拶の仕方:")
        self.greeting_input = QtWidgets.QLineEdit()
        
        other_layout.addWidget(background_label)
        other_layout.addWidget(self.background_input)
        other_layout.addWidget(catchphrase_label)
        other_layout.addWidget(self.catchphrase_input)
        other_layout.addWidget(greeting_label)
        other_layout.addWidget(self.greeting_input)
        other_group.setLayout(other_layout)
        scroll_layout.addWidget(other_group)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # ボタン
        button_layout = QtWidgets.QHBoxLayout()
        
        self.preview_button = QtWidgets.QPushButton("プレビュー")
        self.preview_button.clicked.connect(self.show_preview)
        
        self.save_button = QtWidgets.QPushButton("保存")
        self.save_button.clicked.connect(self.save_character)
        
        self.cancel_button = QtWidgets.QPushButton("キャンセル")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.preview_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # フォント設定
        for widget in [self.name_input, self.personality_input, self.speaking_input,
                      self.specialization_input, self.response_input, self.background_input,
                      self.catchphrase_input, self.greeting_input, self.preview_button,
                      self.save_button, self.cancel_button]:
            widget.setFont(font)
    
    def load_character_data(self):
        """既存キャラクターデータを読み込み"""
        self.name_input.setText(self.character.name)
        self.personality_input.setPlainText(self.character.personality)
        self.speaking_input.setPlainText(self.character.speaking_style)
        self.specialization_input.setPlainText(self.character.specialization)
        self.response_input.setPlainText(self.character.response_style)
        self.background_input.setPlainText(self.character.background)
        self.catchphrase_input.setText(self.character.catchphrase)
        self.greeting_input.setText(self.character.greeting)
    
    def show_preview(self):
        """プレビューダイアログを表示"""
        character_data = self.get_character_data()
        if not character_data['name'].strip():
            QtWidgets.QMessageBox.warning(self, "入力エラー", "キャラクター名を入力してください。")
            return
        
        # テンポラリキャラクターを作成
        temp_character = CustomGPT(**character_data)
        system_prompt = temp_character.build_system_prompt()
        
        preview_dialog = CharacterPreviewDialog(self, character_data['name'], system_prompt)
        preview_dialog.exec_()
    
    def save_character(self):
        """キャラクターを保存"""
        character_data = self.get_character_data()
        
        # 入力検証
        if not character_data['name'].strip():
            QtWidgets.QMessageBox.warning(self, "入力エラー", "キャラクター名を入力してください。")
            return
        
        # キャラクター更新
        if custom_gpt_manager.update_character(self.character.character_id, **character_data):
            QtWidgets.QMessageBox.information(
                self, "成功", 
                f"キャラクター「{character_data['name']}」を更新しました！"
            )
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(
                self, "エラー", 
                "キャラクターの更新に失敗しました。\n同じ名前のキャラクターが既に存在する可能性があります。"
            )
    
    def get_character_data(self):
        """入力されたキャラクターデータを取得"""
        return {
            'name': self.name_input.text().strip(),
            'personality': self.personality_input.toPlainText().strip(),
            'speaking_style': self.speaking_input.toPlainText().strip(),
            'specialization': self.specialization_input.toPlainText().strip(),
            'response_style': self.response_input.toPlainText().strip(),
            'background': self.background_input.toPlainText().strip(),
            'catchphrase': self.catchphrase_input.text().strip(),
            'greeting': self.greeting_input.text().strip()
        }

class CharacterSelectorDialog(QtWidgets.QDialog):
    """キャラクター切替ダイアログ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("キャラクター切替")
        self.setModal(True)
        self.resize(600, 400)
        
        self.init_ui()
        self.load_characters()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QtWidgets.QVBoxLayout(self)
        font = QtGui.QFont("メイリオ", 10)
        
        # 説明
        explanation = QtWidgets.QLabel("使用するキャラクターを選択してください：")
        layout.addWidget(explanation)
        
        # キャラクターリスト
        self.character_list = QtWidgets.QListWidget()
        layout.addWidget(self.character_list)
        
        # ボタン
        button_layout = QtWidgets.QHBoxLayout()
        
        self.select_button = QtWidgets.QPushButton("選択")
        self.select_button.clicked.connect(self.select_character)
        self.select_button.setEnabled(False)
        
        self.cancel_button = QtWidgets.QPushButton("キャンセル")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 選択変更時のイベント
        self.character_list.itemSelectionChanged.connect(
            lambda: self.select_button.setEnabled(len(self.character_list.selectedItems()) > 0)
        )
    
    def load_characters(self):
        """キャラクターを読み込み"""
        characters = custom_gpt_manager.get_all_characters()
        current_active = custom_gpt_manager.get_active_character()
        
        for character in characters:
            item_text = character.name
            if character.specialization:
                spec_short = character.specialization[:40] + "..." if len(character.specialization) > 40 else character.specialization
                item_text += f" ({spec_short})"
            
            if current_active and character.character_id == current_active.character_id:
                item_text += " [現在使用中]"
            
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, character)
            self.character_list.addItem(item)
    
    def select_character(self):
        """キャラクターを選択"""
        selected_items = self.character_list.selectedItems()
        if not selected_items:
            return
        
        character = selected_items[0].data(QtCore.Qt.UserRole)
        custom_gpt_manager.set_active_character(character)
        self.accept()

class ExportDialog(QtWidgets.QDialog):
    """エクスポートダイアログ"""
    
    def __init__(self, parent=None, conversation_history=None):
        super().__init__(parent)
        self.conversation_history = conversation_history or []
        self.setWindowTitle("会話履歴エクスポート")
        self.setModal(True)
        self.resize(500, 400)
        
        self.init_ui()
        self.update_preview()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QtWidgets.QVBoxLayout(self)
        font = QtGui.QFont("メイリオ", 10)
        
        # エクスポート形式選択
        format_group = QtWidgets.QGroupBox("エクスポート形式")
        format_layout = QtWidgets.QVBoxLayout(format_group)
        
        self.txt_radio = QtWidgets.QRadioButton("テキストファイル (.txt)")
        self.txt_radio.setChecked(True)
        
        self.json_radio = QtWidgets.QRadioButton("JSON形式 (.json)")
        
        # PDF出力の可否をチェック
        from export_manager import PDF_AVAILABLE
        self.pdf_radio = QtWidgets.QRadioButton("PDFファイル (.pdf)")
        if not PDF_AVAILABLE:
            self.pdf_radio.setEnabled(False)
            self.pdf_radio.setToolTip("reportlabライブラリが必要です")
        
        format_layout.addWidget(self.txt_radio)
        format_layout.addWidget(self.json_radio)
        format_layout.addWidget(self.pdf_radio)
        
        layout.addWidget(format_group)
        
        # 日付範囲選択
        date_group = QtWidgets.QGroupBox("日付範囲")
        date_layout = QtWidgets.QVBoxLayout(date_group)
        
        self.all_dates_radio = QtWidgets.QRadioButton("全ての会話")
        self.all_dates_radio.setChecked(True)
        self.all_dates_radio.toggled.connect(self.on_date_range_changed)
        
        self.custom_dates_radio = QtWidgets.QRadioButton("期間を指定")
        self.custom_dates_radio.toggled.connect(self.on_date_range_changed)
        
        date_layout.addWidget(self.all_dates_radio)
        date_layout.addWidget(self.custom_dates_radio)
        
        # カスタム日付入力
        custom_date_layout = QtWidgets.QHBoxLayout()
        
        self.start_date = QtWidgets.QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QtCore.QDate.currentDate().addDays(-30))
        self.start_date.setEnabled(False)
        
        self.end_date = QtWidgets.QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QtCore.QDate.currentDate())
        self.end_date.setEnabled(False)
        
        custom_date_layout.addWidget(QtWidgets.QLabel("開始:"))
        custom_date_layout.addWidget(self.start_date)
        custom_date_layout.addWidget(QtWidgets.QLabel("終了:"))
        custom_date_layout.addWidget(self.end_date)
        
        date_layout.addLayout(custom_date_layout)
        layout.addWidget(date_group)
        
        # プレビュー
        preview_group = QtWidgets.QGroupBox("プレビュー")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)
        
        self.preview_label = QtWidgets.QLabel()
        self.preview_label.setFont(font)
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(preview_group)
        
        # ボタン
        button_layout = QtWidgets.QHBoxLayout()
        
        self.export_button = QtWidgets.QPushButton("エクスポート")
        self.export_button.clicked.connect(self.export_conversation)
        
        self.cancel_button = QtWidgets.QPushButton("キャンセル")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # フォント設定
        for widget in [self.txt_radio, self.json_radio, self.pdf_radio,
                      self.all_dates_radio, self.custom_dates_radio,
                      self.start_date, self.end_date, self.export_button, 
                      self.cancel_button]:
            widget.setFont(font)
        
        # 日付変更時の更新
        self.start_date.dateChanged.connect(self.update_preview)
        self.end_date.dateChanged.connect(self.update_preview)
    
    def on_date_range_changed(self):
        """日付範囲選択の変更処理"""
        is_custom = self.custom_dates_radio.isChecked()
        self.start_date.setEnabled(is_custom)
        self.end_date.setEnabled(is_custom)
        self.update_preview()
    
    def update_preview(self):
        """プレビューを更新"""
        # 会話履歴を解析
        entries = export_manager.parse_conversation_history(self.conversation_history)
        
        # 日付フィルタリング
        if self.custom_dates_radio.isChecked():
            start_date = self.start_date.date().toPyDate()
            end_date = self.end_date.date().toPyDate()
            
            # datetimeに変換
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            entries = export_manager.filter_by_date_range(entries, start_datetime, end_datetime)
        
        # 統計情報を取得
        stats = export_manager.get_conversation_stats(entries)
        
        # プレビュー情報を作成
        preview_text = f"対象会話数: {stats['total_conversations']}件\n"
        
        if stats['date_range']:
            start_str = stats['date_range']['start'].strftime('%Y年%m月%d日')
            end_str = stats['date_range']['end'].strftime('%Y年%m月%d日')
            preview_text += f"期間: {start_str} ～ {end_str}\n"
        
        preview_text += f"総文字数: {stats['total_characters']:,}文字\n"
        preview_text += f"平均ユーザー文字数: {stats['avg_user_length']:.1f}文字\n"
        preview_text += f"平均AI文字数: {stats['avg_ai_length']:.1f}文字"
        
        self.preview_label.setText(preview_text)
    
    def export_conversation(self):
        """会話をエクスポート"""
        try:
            # エクスポート形式を取得
            if self.txt_radio.isChecked():
                extension = "txt"
                file_filter = "テキストファイル (*.txt)"
            elif self.json_radio.isChecked():
                extension = "json"
                file_filter = "JSONファイル (*.json)"
            elif self.pdf_radio.isChecked():
                extension = "pdf"
                file_filter = "PDFファイル (*.pdf)"
            else:
                QtWidgets.QMessageBox.warning(self, "エラー", "エクスポート形式を選択してください。")
                return
            
            # 保存先ファイルを選択
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "エクスポート先を選択",
                f"AI_takashi_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}",
                file_filter
            )
            
            if not file_path:
                return
            
            # 会話履歴を解析
            entries = export_manager.parse_conversation_history(self.conversation_history)
            
            # 日付フィルタリング
            if self.custom_dates_radio.isChecked():
                start_date = self.start_date.date().toPyDate()
                end_date = self.end_date.date().toPyDate()
                
                start_datetime = datetime.combine(start_date, datetime.min.time())
                end_datetime = datetime.combine(end_date, datetime.max.time())
                
                entries = export_manager.filter_by_date_range(entries, start_datetime, end_datetime)
            
            # エクスポート実行
            success = False
            if extension == "txt":
                success = export_manager.export_to_txt(entries, file_path)
            elif extension == "json":
                success = export_manager.export_to_json(entries, file_path)
            elif extension == "pdf":
                success = export_manager.export_to_pdf(entries, file_path)
            
            if success:
                QtWidgets.QMessageBox.information(
                    self, "成功", f"エクスポートが完了しました。\n保存先: {file_path}"
                )
                self.accept()
            else:
                QtWidgets.QMessageBox.warning(
                    self, "エラー", "エクスポートに失敗しました。"
                )
                
        except Exception as e:
            logging.error(f"エクスポートエラー: {e}")
            QtWidgets.QMessageBox.critical(
                self, "エラー", f"エクスポート中にエラーが発生しました。\n{str(e)}"
                         )

class BackupManagerDialog(QtWidgets.QDialog):
    """バックアップ管理ダイアログ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("バックアップ管理")
        self.setModal(True)
        self.resize(700, 500)
        
        self.init_ui()
        self.load_backup_list()
        self.load_backup_settings()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QtWidgets.QVBoxLayout(self)
        font = QtGui.QFont("メイリオ", 10)
        
        # タブウィジェット
        self.tab_widget = QtWidgets.QTabWidget()
        
        # バックアップ一覧タブ
        self.backup_list_tab = QtWidgets.QWidget()
        self.init_backup_list_tab()
        self.tab_widget.addTab(self.backup_list_tab, "バックアップ一覧")
        
        # 設定タブ
        self.settings_tab = QtWidgets.QWidget()
        self.init_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "設定")
        
        layout.addWidget(self.tab_widget)
        
        # 閉じるボタン
        button_layout = QtWidgets.QHBoxLayout()
        self.close_button = QtWidgets.QPushButton("閉じる")
        self.close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
        
        # フォント設定
        self.close_button.setFont(font)
    
    def init_backup_list_tab(self):
        """バックアップ一覧タブを初期化"""
        layout = QtWidgets.QVBoxLayout(self.backup_list_tab)
        font = QtGui.QFont("メイリオ", 10)
        
        # 統計情報
        self.stats_label = QtWidgets.QLabel()
        self.stats_label.setFont(font)
        layout.addWidget(self.stats_label)
        
        # バックアップリスト
        self.backup_list = QtWidgets.QListWidget()
        self.backup_list.setFont(font)
        self.backup_list.itemSelectionChanged.connect(self.on_backup_selection_changed)
        layout.addWidget(self.backup_list)
        
        # ボタン
        button_layout = QtWidgets.QHBoxLayout()
        
        self.create_backup_button = QtWidgets.QPushButton("バックアップ作成")
        self.create_backup_button.clicked.connect(self.create_backup)
        
        self.restore_backup_button = QtWidgets.QPushButton("復元")
        self.restore_backup_button.clicked.connect(self.restore_backup)
        self.restore_backup_button.setEnabled(False)
        
        self.delete_backup_button = QtWidgets.QPushButton("削除")
        self.delete_backup_button.clicked.connect(self.delete_backup)
        self.delete_backup_button.setEnabled(False)
        
        self.refresh_button = QtWidgets.QPushButton("更新")
        self.refresh_button.clicked.connect(self.load_backup_list)
        
        button_layout.addWidget(self.create_backup_button)
        button_layout.addWidget(self.restore_backup_button)
        button_layout.addWidget(self.delete_backup_button)
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)
        
        layout.addLayout(button_layout)
        
        # フォント設定
        for widget in [self.create_backup_button, self.restore_backup_button,
                      self.delete_backup_button, self.refresh_button]:
            widget.setFont(font)
    
    def init_settings_tab(self):
        """設定タブを初期化"""
        layout = QtWidgets.QVBoxLayout(self.settings_tab)
        font = QtGui.QFont("メイリオ", 10)
        
        # 自動バックアップ設定
        auto_backup_group = QtWidgets.QGroupBox("自動バックアップ")
        auto_backup_layout = QtWidgets.QVBoxLayout(auto_backup_group)
        
        self.auto_backup_checkbox = QtWidgets.QCheckBox("自動バックアップを有効にする")
        self.auto_backup_checkbox.setFont(font)
        auto_backup_layout.addWidget(self.auto_backup_checkbox)
        
        # バックアップ間隔
        interval_layout = QtWidgets.QHBoxLayout()
        interval_label = QtWidgets.QLabel("バックアップ間隔:")
        interval_label.setFont(font)
        
        self.interval_spinbox = QtWidgets.QSpinBox()
        self.interval_spinbox.setRange(1, 168)  # 1時間〜7日
        self.interval_spinbox.setSuffix(" 時間")
        self.interval_spinbox.setFont(font)
        
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_spinbox)
        interval_layout.addStretch()
        
        auto_backup_layout.addLayout(interval_layout)
        
        # 保持期間
        retention_layout = QtWidgets.QHBoxLayout()
        retention_label = QtWidgets.QLabel("保持期間:")
        retention_label.setFont(font)
        
        self.retention_spinbox = QtWidgets.QSpinBox()
        self.retention_spinbox.setRange(1, 365)  # 1日〜1年
        self.retention_spinbox.setSuffix(" 日")
        self.retention_spinbox.setFont(font)
        
        retention_layout.addWidget(retention_label)
        retention_layout.addWidget(self.retention_spinbox)
        retention_layout.addStretch()
        
        auto_backup_layout.addLayout(retention_layout)
        
        layout.addWidget(auto_backup_group)
        
        # 保存ボタン
        save_settings_layout = QtWidgets.QHBoxLayout()
        self.save_settings_button = QtWidgets.QPushButton("設定を保存")
        self.save_settings_button.clicked.connect(self.save_settings)
        self.save_settings_button.setFont(font)
        
        save_settings_layout.addStretch()
        save_settings_layout.addWidget(self.save_settings_button)
        
        layout.addLayout(save_settings_layout)
        layout.addStretch()
    
    def load_backup_list(self):
        """バックアップ一覧を読み込み"""
        self.backup_list.clear()
        
        try:
            backups = backup_manager.get_backup_list()
            
            for backup in backups:
                # 表示用テキストを作成
                created_str = backup['created_time'].strftime('%Y-%m-%d %H:%M:%S')
                size_mb = backup['size'] / (1024 * 1024)
                backup_type = "自動" if backup['auto_backup'] else "手動"
                
                item_text = f"{backup['filename']} - {backup_type} - {created_str} ({size_mb:.1f}MB)"
                
                item = QtWidgets.QListWidgetItem(item_text)
                item.setData(QtCore.Qt.UserRole, backup)
                
                # ツールチップ
                tooltip = f"ファイル名: {backup['filename']}\n"
                tooltip += f"種類: {backup_type}バックアップ\n"
                tooltip += f"作成日時: {created_str}\n"
                tooltip += f"サイズ: {size_mb:.1f}MB\n"
                tooltip += f"ファイル数: {backup['files_count']}件"
                item.setToolTip(tooltip)
                
                self.backup_list.addItem(item)
            
            # 統計情報を更新
            self.update_stats()
            
        except Exception as e:
            logging.error(f"バックアップ一覧読み込みエラー: {e}")
            QtWidgets.QMessageBox.warning(self, "エラー", "バックアップ一覧の読み込みに失敗しました。")
    
    def update_stats(self):
        """統計情報を更新"""
        try:
            stats = backup_manager.get_backup_stats()
            
            stats_text = f"総バックアップ数: {stats['total_count']}件 "
            stats_text += f"(自動: {stats['auto_count']}件, 手動: {stats['manual_count']}件)\n"
            stats_text += f"総サイズ: {stats['total_size'] / (1024 * 1024):.1f}MB | "
            stats_text += f"保存場所: {stats['backup_dir']}"
            
            self.stats_label.setText(stats_text)
            
        except Exception as e:
            logging.error(f"統計情報更新エラー: {e}")
            self.stats_label.setText("統計情報の取得に失敗しました")
    
    def load_backup_settings(self):
        """バックアップ設定を読み込み"""
        try:
            self.auto_backup_checkbox.setChecked(backup_manager.auto_backup_enabled)
            self.interval_spinbox.setValue(backup_manager.backup_interval_hours)
            self.retention_spinbox.setValue(backup_manager.max_backup_days)
            
        except Exception as e:
            logging.error(f"バックアップ設定読み込みエラー: {e}")
    
    def on_backup_selection_changed(self):
        """バックアップ選択変更時の処理"""
        has_selection = len(self.backup_list.selectedItems()) > 0
        self.restore_backup_button.setEnabled(has_selection)
        self.delete_backup_button.setEnabled(has_selection)
    
    def create_backup(self):
        """バックアップを作成"""
        try:
            backup_path = backup_manager.create_backup(auto_backup=False)
            if backup_path:
                QtWidgets.QMessageBox.information(
                    self, "成功", f"バックアップを作成しました。\n{backup_path}"
                )
                self.load_backup_list()
            else:
                QtWidgets.QMessageBox.warning(
                    self, "エラー", "バックアップの作成に失敗しました。"
                )
        except Exception as e:
            logging.error(f"バックアップ作成エラー: {e}")
            QtWidgets.QMessageBox.critical(
                self, "エラー", f"バックアップ作成中にエラーが発生しました。\n{str(e)}"
            )
    
    def restore_backup(self):
        """バックアップから復元"""
        selected_items = self.backup_list.selectedItems()
        if not selected_items:
            return
        
        backup = selected_items[0].data(QtCore.Qt.UserRole)
        
        # 確認ダイアログ
        reply = QtWidgets.QMessageBox.question(
            self, "確認", 
            f"バックアップ '{backup['filename']}' から復元しますか？\n"
            "現在のデータは自動的にバックアップされます。",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                if backup_manager.restore_backup(backup['filepath']):
                    QtWidgets.QMessageBox.information(
                        self, "成功", 
                        "バックアップから復元しました。\n"
                        "変更を反映するには、アプリケーションを再起動してください。"
                    )
                else:
                    QtWidgets.QMessageBox.warning(
                        self, "エラー", "バックアップの復元に失敗しました。"
                    )
            except Exception as e:
                logging.error(f"バックアップ復元エラー: {e}")
                QtWidgets.QMessageBox.critical(
                    self, "エラー", f"復元中にエラーが発生しました。\n{str(e)}"
                )
    
    def delete_backup(self):
        """バックアップを削除"""
        selected_items = self.backup_list.selectedItems()
        if not selected_items:
            return
        
        backup = selected_items[0].data(QtCore.Qt.UserRole)
        
        # 確認ダイアログ
        reply = QtWidgets.QMessageBox.question(
            self, "確認", 
            f"バックアップ '{backup['filename']}' を削除しますか？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            try:
                import os
                os.remove(backup['filepath'])
                self.load_backup_list()
                QtWidgets.QMessageBox.information(
                    self, "成功", "バックアップを削除しました。"
                )
            except Exception as e:
                logging.error(f"バックアップ削除エラー: {e}")
                QtWidgets.QMessageBox.critical(
                    self, "エラー", f"削除中にエラーが発生しました。\n{str(e)}"
                )
    
    def save_settings(self):
        """設定を保存"""
        try:
            backup_manager.update_settings(
                backup_interval_hours=self.interval_spinbox.value(),
                max_backup_days=self.retention_spinbox.value(),
                auto_backup_enabled=self.auto_backup_checkbox.isChecked()
            )
            
            QtWidgets.QMessageBox.information(
                self, "成功", "設定を保存しました。"
            )
            
        except Exception as e:
            logging.error(f"設定保存エラー: {e}")
            QtWidgets.QMessageBox.critical(
                self, "エラー", f"設定保存中にエラーが発生しました。\n{str(e)}"
                         )

class ResponseTimeStatsDialog(QtWidgets.QDialog):
    """応答時間統計ダイアログ"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("応答時間統計")
        self.setModal(True)
        self.resize(800, 600)
        
        self.init_ui()
        self.load_statistics()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QtWidgets.QVBoxLayout(self)
        font = QtGui.QFont("メイリオ", 10)
        
        # タブウィジェット
        self.tab_widget = QtWidgets.QTabWidget()
        
        # 統計タブ
        self.stats_tab = QtWidgets.QWidget()
        self.init_stats_tab()
        self.tab_widget.addTab(self.stats_tab, "統計情報")
        
        # 履歴タブ
        self.history_tab = QtWidgets.QWidget()
        self.init_history_tab()
        self.tab_widget.addTab(self.history_tab, "履歴")
        
        # グラフタブ
        self.graph_tab = QtWidgets.QWidget()
        self.init_graph_tab()
        self.tab_widget.addTab(self.graph_tab, "グラフ")
        
        # 設定タブ
        self.settings_tab = QtWidgets.QWidget()
        self.init_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "設定")
        
        layout.addWidget(self.tab_widget)
        
        # 閉じるボタン
        button_layout = QtWidgets.QHBoxLayout()
        
        self.refresh_button = QtWidgets.QPushButton("更新")
        self.refresh_button.clicked.connect(self.load_statistics)
        
        self.export_button = QtWidgets.QPushButton("レポート出力")
        self.export_button.clicked.connect(self.export_report)
        
        self.close_button = QtWidgets.QPushButton("閉じる")
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.export_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        # フォント設定
        for widget in [self.refresh_button, self.export_button, self.close_button]:
            widget.setFont(font)
    
    def init_stats_tab(self):
        """統計タブを初期化"""
        layout = QtWidgets.QVBoxLayout(self.stats_tab)
        font = QtGui.QFont("メイリオ", 10)
        
        # 期間選択
        period_layout = QtWidgets.QHBoxLayout()
        period_label = QtWidgets.QLabel("期間:")
        self.period_combo = QtWidgets.QComboBox()
        self.period_combo.addItems(["7日間", "30日間", "90日間"])
        self.period_combo.setCurrentText("30日間")
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        
        period_layout.addWidget(period_label)
        period_layout.addWidget(self.period_combo)
        period_layout.addStretch()
        
        layout.addLayout(period_layout)
        
        # 統計情報表示エリア
        self.stats_text = QtWidgets.QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setFont(QtGui.QFont("Consolas", 9))
        layout.addWidget(self.stats_text)
        
        # フォント設定
        period_label.setFont(font)
        self.period_combo.setFont(font)
    
    def init_history_tab(self):
        """履歴タブを初期化"""
        layout = QtWidgets.QVBoxLayout(self.history_tab)
        font = QtGui.QFont("メイリオ", 10)
        
        # 履歴リスト
        self.history_list = QtWidgets.QTableWidget()
        self.history_list.setColumnCount(4)
        self.history_list.setHorizontalHeaderLabels([
            "日時", "応答時間", "ユーザー文字数", "AI文字数"
        ])
        self.history_list.horizontalHeader().setStretchLastSection(True)
        self.history_list.setFont(font)
        layout.addWidget(self.history_list)
    
    def init_graph_tab(self):
        """グラフタブを初期化"""
        layout = QtWidgets.QVBoxLayout(self.graph_tab)
        
        # グラフタイプ選択
        graph_type_layout = QtWidgets.QHBoxLayout()
        graph_type_label = QtWidgets.QLabel("グラフタイプ:")
        self.graph_type_combo = QtWidgets.QComboBox()
        self.graph_type_combo.addItems([
            "時系列グラフ", "時間帯別平均", "パフォーマンス分布"
        ])
        self.graph_type_combo.currentTextChanged.connect(self.update_graph)
        
        graph_type_layout.addWidget(graph_type_label)
        graph_type_layout.addWidget(self.graph_type_combo)
        graph_type_layout.addStretch()
        
        layout.addLayout(graph_type_layout)
        
        # グラフエリア
        try:
            self.figure = plt.figure(figsize=(10, 6))
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas)
        except Exception as e:
            # matplotlibが利用できない場合
            placeholder = QtWidgets.QLabel("グラフ機能は利用できません（matplotlib未インストール）")
            placeholder.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(placeholder)
    
    def init_settings_tab(self):
        """設定タブを初期化"""
        layout = QtWidgets.QVBoxLayout(self.settings_tab)
        font = QtGui.QFont("メイリオ", 10)
        
        # 警告しきい値設定
        threshold_group = QtWidgets.QGroupBox("警告しきい値")
        threshold_layout = QtWidgets.QVBoxLayout(threshold_group)
        
        # 警告しきい値
        warning_layout = QtWidgets.QHBoxLayout()
        warning_label = QtWidgets.QLabel("警告しきい値:")
        self.warning_spinbox = QtWidgets.QDoubleSpinBox()
        self.warning_spinbox.setRange(1.0, 60.0)
        self.warning_spinbox.setSuffix(" 秒")
        self.warning_spinbox.setValue(response_time_manager.warning_threshold)
        
        warning_layout.addWidget(warning_label)
        warning_layout.addWidget(self.warning_spinbox)
        warning_layout.addStretch()
        
        threshold_layout.addLayout(warning_layout)
        
        # 低速しきい値
        slow_layout = QtWidgets.QHBoxLayout()
        slow_label = QtWidgets.QLabel("低速しきい値:")
        self.slow_spinbox = QtWidgets.QDoubleSpinBox()
        self.slow_spinbox.setRange(1.0, 120.0)
        self.slow_spinbox.setSuffix(" 秒")
        self.slow_spinbox.setValue(response_time_manager.slow_threshold)
        
        slow_layout.addWidget(slow_label)
        slow_layout.addWidget(self.slow_spinbox)
        slow_layout.addStretch()
        
        threshold_layout.addLayout(slow_layout)
        
        layout.addWidget(threshold_group)
        
        # 履歴保持設定
        history_group = QtWidgets.QGroupBox("履歴保持設定")
        history_layout = QtWidgets.QVBoxLayout(history_group)
        
        history_days_layout = QtWidgets.QHBoxLayout()
        history_days_label = QtWidgets.QLabel("保持期間:")
        self.history_days_spinbox = QtWidgets.QSpinBox()
        self.history_days_spinbox.setRange(7, 365)
        self.history_days_spinbox.setSuffix(" 日")
        self.history_days_spinbox.setValue(response_time_manager.max_history_days)
        
        history_days_layout.addWidget(history_days_label)
        history_days_layout.addWidget(self.history_days_spinbox)
        history_days_layout.addStretch()
        
        history_layout.addLayout(history_days_layout)
        layout.addWidget(history_group)
        
        # 設定保存ボタン
        save_settings_layout = QtWidgets.QHBoxLayout()
        self.save_settings_button = QtWidgets.QPushButton("設定を保存")
        self.save_settings_button.clicked.connect(self.save_settings)
        
        save_settings_layout.addStretch()
        save_settings_layout.addWidget(self.save_settings_button)
        
        layout.addLayout(save_settings_layout)
        layout.addStretch()
        
        # フォント設定
        for widget in [warning_label, slow_label, history_days_label,
                      self.warning_spinbox, self.slow_spinbox, 
                      self.history_days_spinbox, self.save_settings_button]:
            widget.setFont(font)
    
    def load_statistics(self):
        """統計情報を読み込み"""
        try:
            # 期間を取得
            period_text = self.period_combo.currentText()
            days = 30  # デフォルト
            if "7日間" in period_text:
                days = 7
            elif "30日間" in period_text:
                days = 30
            elif "90日間" in period_text:
                days = 90
            
            # 統計情報を取得
            stats = response_time_manager.get_statistics(days)
            
            # 統計情報を表示
            self.display_statistics(stats, days)
            
            # 履歴を表示
            self.load_history(days)
            
            # グラフを更新
            self.update_graph()
            
        except Exception as e:
            logging.error(f"統計情報読み込みエラー: {e}")
    
    def display_statistics(self, stats: dict, days: int):
        """統計情報を表示"""
        try:
            if stats.get('total_count', 0) == 0:
                self.stats_text.setPlainText(f"過去{days}日間のデータがありません。")
                return
            
            text = f"応答時間統計 (過去{days}日間)\n"
            text += "=" * 40 + "\n\n"
            
            text += "【基本統計】\n"
            text += f"総応答数: {stats['total_count']}件\n"
            text += f"平均応答時間: {stats['average_time']:.2f}秒\n"
            text += f"中央値応答時間: {stats['median_time']:.2f}秒\n"
            text += f"最短応答時間: {stats['min_time']:.2f}秒\n"
            text += f"最長応答時間: {stats['max_time']:.2f}秒\n"
            text += f"標準偏差: {stats['std_deviation']:.2f}秒\n\n"
            
            text += "【パフォーマンス分析】\n"
            text += f"高速応答 (≤3秒): {stats['fast_responses']}件 ({stats['fast_percentage']:.1f}%)\n"
            text += f"通常応答: {stats['total_count'] - stats['warning_count'] - stats['fast_responses']}件\n"
            text += f"警告レベル (>{response_time_manager.warning_threshold}秒): {stats['warning_count']}件 ({stats['warning_percentage']:.1f}%)\n"
            text += f"低速レベル (>{response_time_manager.slow_threshold}秒): {stats['slow_count']}件 ({stats['slow_percentage']:.1f}%)\n\n"
            
            text += "【パフォーマンス評価】\n"
            if stats['average_time'] <= 3:
                text += "✓ 優秀 - 高速な応答を維持しています\n"
            elif stats['average_time'] <= 5:
                text += "○ 良好 - 良好な応答速度です\n"
            elif stats['average_time'] <= 8:
                text += "△ 普通 - 応答速度は標準的です\n"
            else:
                text += "× 要改善 - 応答速度の改善が必要です\n"
            
            if stats['warning_percentage'] > 20:
                text += "! 警告: 遅い応答が多発しています\n"
            elif stats['warning_percentage'] > 10:
                text += "注意: 遅い応答がやや多めです\n"
            
            self.stats_text.setPlainText(text)
            
        except Exception as e:
            logging.error(f"統計情報表示エラー: {e}")
            self.stats_text.setPlainText("統計情報の表示に失敗しました")
    
    def load_history(self, days: int):
        """履歴を読み込み"""
        try:
            # 指定期間内の履歴を取得
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_history = [
                entry for entry in response_time_manager.history 
                if entry.timestamp > cutoff_date
            ]
            
            # テーブルをクリア
            self.history_list.setRowCount(0)
            
            # データを追加（新しい順）
            recent_history.sort(key=lambda x: x.timestamp, reverse=True)
            
            for i, entry in enumerate(recent_history[:100]):  # 最新100件まで表示
                self.history_list.insertRow(i)
                
                # 日時
                self.history_list.setItem(i, 0, QtWidgets.QTableWidgetItem(
                    entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                ))
                
                # 応答時間
                time_item = QtWidgets.QTableWidgetItem(f"{entry.response_time:.2f}秒")
                # 色分け
                if entry.response_time > response_time_manager.slow_threshold:
                    time_item.setBackground(QtGui.QColor(255, 200, 200))  # 赤
                elif entry.response_time > response_time_manager.warning_threshold:
                    time_item.setBackground(QtGui.QColor(255, 255, 200))  # 黄
                elif entry.response_time <= 3.0:
                    time_item.setBackground(QtGui.QColor(200, 255, 200))  # 緑
                
                self.history_list.setItem(i, 1, time_item)
                
                # ユーザー文字数
                self.history_list.setItem(i, 2, QtWidgets.QTableWidgetItem(
                    f"{entry.user_text_length}文字"
                ))
                
                # AI文字数
                self.history_list.setItem(i, 3, QtWidgets.QTableWidgetItem(
                    f"{entry.ai_text_length}文字"
                ))
            
            # 列幅を調整
            self.history_list.resizeColumnsToContents()
            
        except Exception as e:
            logging.error(f"履歴読み込みエラー: {e}")
    
    def update_graph(self):
        """グラフを更新"""
        try:
            if not hasattr(self, 'figure'):
                return
            
            self.figure.clear()
            
            graph_type = self.graph_type_combo.currentText()
            period_text = self.period_combo.currentText()
            days = 30
            if "7日間" in period_text:
                days = 7
            elif "90日間" in period_text:
                days = 90
            
            if graph_type == "時系列グラフ":
                self.draw_timeline_graph(days)
            elif graph_type == "時間帯別平均":
                self.draw_hourly_graph(days)
            elif graph_type == "パフォーマンス分布":
                self.draw_distribution_graph(days)
            
            self.canvas.draw()
            
        except Exception as e:
            logging.error(f"グラフ更新エラー: {e}")
    
    def draw_timeline_graph(self, days: int):
        """時系列グラフを描画"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_history = [
                entry for entry in response_time_manager.history 
                if entry.timestamp > cutoff_date
            ]
            
            if not recent_history:
                return
            
            # データを準備
            timestamps = [entry.timestamp for entry in recent_history]
            response_times = [entry.response_time for entry in recent_history]
            
            ax = self.figure.add_subplot(111)
            ax.plot(timestamps, response_times, 'b-', alpha=0.7, linewidth=1)
            ax.scatter(timestamps, response_times, c=response_times, cmap='RdYlGn_r', s=20)
            
            # 警告ライン
            ax.axhline(y=response_time_manager.warning_threshold, color='orange', 
                      linestyle='--', alpha=0.7, label=f'警告しきい値 ({response_time_manager.warning_threshold}s)')
            ax.axhline(y=response_time_manager.slow_threshold, color='red', 
                      linestyle='--', alpha=0.7, label=f'低速しきい値 ({response_time_manager.slow_threshold}s)')
            
            ax.set_title(f'応答時間の推移 (過去{days}日間)')
            ax.set_xlabel('日時')
            ax.set_ylabel('応答時間 (秒)')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # 日付フォーマット
            import matplotlib.dates as mdates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            self.figure.autofmt_xdate()
            
        except Exception as e:
            logging.error(f"時系列グラフ描画エラー: {e}")
    
    def draw_hourly_graph(self, days: int):
        """時間帯別平均グラフを描画"""
        try:
            hourly_stats = response_time_manager.get_hourly_statistics(days)
            
            hours = [stat['hour'] for stat in hourly_stats]
            avg_times = [stat['average_time'] for stat in hourly_stats]
            counts = [stat['count'] for stat in hourly_stats]
            
            ax = self.figure.add_subplot(111)
            bars = ax.bar(hours, avg_times, alpha=0.7, color='skyblue', edgecolor='navy')
            
            # カウント数をバーの上に表示
            for i, (bar, count) in enumerate(zip(bars, counts)):
                if count > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                           f'{count}', ha='center', va='bottom', fontsize=8)
            
            ax.set_title(f'時間帯別平均応答時間 (過去{days}日間)')
            ax.set_xlabel('時間')
            ax.set_ylabel('平均応答時間 (秒)')
            ax.set_xticks(range(24))
            ax.grid(True, alpha=0.3)
            
        except Exception as e:
            logging.error(f"時間帯別グラフ描画エラー: {e}")
    
    def draw_distribution_graph(self, days: int):
        """パフォーマンス分布グラフを描画"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_history = [
                entry for entry in response_time_manager.history 
                if entry.timestamp > cutoff_date
            ]
            
            if not recent_history:
                return
            
            response_times = [entry.response_time for entry in recent_history]
            
            ax = self.figure.add_subplot(111)
            ax.hist(response_times, bins=20, alpha=0.7, color='lightblue', edgecolor='navy')
            
            # 統計ライン
            ax.axvline(x=np.mean(response_times), color='green', linestyle='-', 
                      label=f'平均: {np.mean(response_times):.2f}s')
            ax.axvline(x=np.median(response_times), color='blue', linestyle='-', 
                      label=f'中央値: {np.median(response_times):.2f}s')
            ax.axvline(x=response_time_manager.warning_threshold, color='orange', 
                      linestyle='--', label=f'警告しきい値: {response_time_manager.warning_threshold}s')
            
            ax.set_title(f'応答時間分布 (過去{days}日間)')
            ax.set_xlabel('応答時間 (秒)')
            ax.set_ylabel('頻度')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
        except Exception as e:
            logging.error(f"分布グラフ描画エラー: {e}")
    
    def on_period_changed(self):
        """期間変更時の処理"""
        self.load_statistics()
    
    def save_settings(self):
        """設定を保存"""
        try:
            response_time_manager.update_settings(
                warning_threshold=self.warning_spinbox.value(),
                slow_threshold=self.slow_spinbox.value(),
                max_history_days=self.history_days_spinbox.value()
            )
            
            QtWidgets.QMessageBox.information(
                self, "成功", "設定を保存しました。"
            )
            
        except Exception as e:
            logging.error(f"設定保存エラー: {e}")
            QtWidgets.QMessageBox.critical(
                self, "エラー", f"設定保存中にエラーが発生しました。\n{str(e)}"
            )
    
    def export_report(self):
        """レポートを出力"""
        try:
            period_text = self.period_combo.currentText()
            days = 30
            if "7日間" in period_text:
                days = 7
            elif "90日間" in period_text:
                days = 90
            
            report = response_time_manager.get_detailed_report(days)
            
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "レポート保存",
                f"応答時間レポート_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "テキストファイル (*.txt)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                QtWidgets.QMessageBox.information(
                    self, "成功", f"レポートを保存しました。\n{file_path}"
                )
                
        except Exception as e:
            logging.error(f"レポート出力エラー: {e}")
            QtWidgets.QMessageBox.critical(
                self, "エラー", f"レポート出力中にエラーが発生しました。\n{str(e)}"
            )

class MemorySaveDialog(QtWidgets.QDialog):
    """記憶保存ダイアログ"""
    
    def __init__(self, parent, conversation_history, current_character, 
                 manual_mode=False, edit_mode=False, existing_memory=None):
        super().__init__(parent)
        self.conversation_history = conversation_history
        self.current_character = current_character
        self.manual_mode = manual_mode
        self.edit_mode = edit_mode
        self.existing_memory = existing_memory
        
        self.setWindowTitle("記憶を編集" if edit_mode else "会話を記憶")
        self.setModal(True)
        self.resize(700, 600)
        
        self.init_ui()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QtWidgets.QVBoxLayout(self)
        font = QtGui.QFont("メイリオ", 10)
        
        # タイトル
        title_label = QtWidgets.QLabel("タイトル *")
        title_label.setFont(font)
        layout.addWidget(title_label)
        
        self.title_input = QtWidgets.QLineEdit()
        self.title_input.setFont(font)
        self.title_input.setPlaceholderText("記憶のタイトルを入力...")
        if self.existing_memory:
            self.title_input.setText(self.existing_memory.title)
        layout.addWidget(self.title_input)
        
        # 内容
        content_label = QtWidgets.QLabel("内容 *")
        content_label.setFont(font)
        layout.addWidget(content_label)
        
        self.content_input = QtWidgets.QTextEdit()
        self.content_input.setFont(font)
        self.content_input.setPlaceholderText("記憶する内容を入力...")
        if self.existing_memory:
            self.content_input.setPlainText(self.existing_memory.content)
        elif not self.manual_mode and self.conversation_history:
            # 会話履歴から自動生成
            content = "\n".join(self.conversation_history[-5:])  # 最新5件
            self.content_input.setPlainText(content)
        layout.addWidget(self.content_input)
        
        # カテゴリと重要度
        meta_layout = QtWidgets.QHBoxLayout()
        
        # カテゴリ
        category_label = QtWidgets.QLabel("カテゴリ:")
        category_label.setFont(font)
        meta_layout.addWidget(category_label)
        
        self.category_combo = QtWidgets.QComboBox()
        self.category_combo.setFont(font)
        for category in memory_manager.categories:
            self.category_combo.addItem(category)
        if self.existing_memory:
            index = self.category_combo.findText(self.existing_memory.category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
        meta_layout.addWidget(self.category_combo)
        
        # 重要度
        importance_label = QtWidgets.QLabel("重要度:")
        importance_label.setFont(font)
        meta_layout.addWidget(importance_label)
        
        self.importance_combo = QtWidgets.QComboBox()
        self.importance_combo.setFont(font)
        for importance in memory_manager.importance_levels:
            self.importance_combo.addItem(importance)
        if self.existing_memory:
            index = self.importance_combo.findText(self.existing_memory.importance)
            if index >= 0:
                self.importance_combo.setCurrentIndex(index)
        else:
            self.importance_combo.setCurrentText("中")
        meta_layout.addWidget(self.importance_combo)
        
        layout.addLayout(meta_layout)
        
        # タグ
        tags_label = QtWidgets.QLabel("タグ（カンマ区切り）:")
        tags_label.setFont(font)
        layout.addWidget(tags_label)
        
        self.tags_input = QtWidgets.QLineEdit()
        self.tags_input.setFont(font)
        self.tags_input.setPlaceholderText("例: Python, プロジェクト, アイデア")
        if self.existing_memory and self.existing_memory.tags:
            self.tags_input.setText(", ".join(self.existing_memory.tags))
        layout.addWidget(self.tags_input)
        
        # キャラクター情報表示
        if self.current_character:
            char_info = QtWidgets.QLabel(f"👤 キャラクター: {self.current_character.name}")
            char_info.setStyleSheet("color: #666; padding: 5px;")
            layout.addWidget(char_info)
        
        # ボタン
        button_layout = QtWidgets.QHBoxLayout()
        
        self.save_button = QtWidgets.QPushButton("保存")
        self.save_button.setFont(font)
        self.save_button.clicked.connect(self.accept)
        button_layout.addWidget(self.save_button)
        
        self.cancel_button = QtWidgets.QPushButton("キャンセル")
        self.cancel_button.setFont(font)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def get_memory_data(self):
        """入力されたデータを取得"""
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        category = self.category_combo.currentText()
        importance = self.importance_combo.currentText()
        
        tags_text = self.tags_input.text().strip()
        tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()] if tags_text else []
        
        return {
            'title': title,
            'content': content,
            'character_id': self.current_character.character_id if self.current_character else 'AI_takashi',
            'character_name': self.current_character.name if self.current_character else 'AI_takashi',
            'conversation_history': self.conversation_history.copy() if not self.manual_mode else [],
            'category': category,
            'tags': tags,
            'importance': importance
        }

# メイン関数
def main():
    app = QtWidgets.QApplication([])
    ex = App()
    ex.show()
    app.exec_()

if __name__ == "__main__":
    main()

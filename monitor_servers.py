#!/usr/bin/env python3
"""
サーバー監視スクリプト
APIサーバーとWebクライアントの状態を監視し、停止時に自動再起動
"""

import subprocess
import time
import requests
import sys
import os
from threading import Thread

class ServerMonitor:
    def __init__(self):
        self.api_process = None
        self.web_process = None
        self.running = True
        
    def check_server(self, url, name):
        """サーバーの状態をチェック"""
        try:
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def start_api_server(self):
        """APIサーバーを起動"""
        try:
            print("🔄 APIサーバーを起動中...")
            self.api_process = subprocess.Popen(
                [sys.executable, "api_server.py"],
                cwd=os.getcwd(),
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            print("✅ APIサーバーが起動しました")
            return True
        except Exception as e:
            print(f"❌ APIサーバーの起動に失敗: {e}")
            return False
    
    def start_web_client(self):
        """Webクライアントを起動"""
        try:
            print("🔄 Webクライアントを起動中...")
            web_dir = os.path.join(os.getcwd(), "web-client")
            self.web_process = subprocess.Popen(
                [sys.executable, "serve.py"],
                cwd=web_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            print("✅ Webクライアントが起動しました")
            return True
        except Exception as e:
            print(f"❌ Webクライアントの起動に失敗: {e}")
            return False
    
    def monitor_loop(self):
        """監視ループ"""
        print("🚀 サーバー監視を開始します...")
        print("API Server: http://localhost:8000")
        print("Web Client: http://localhost:3000")
        print("終了するには Ctrl+C を押してください")
        print("-" * 50)
        
        # 初期起動
        self.start_api_server()
        time.sleep(3)
        self.start_web_client()
        
        while self.running:
            try:
                # APIサーバーの状態チェック
                if not self.check_server("http://localhost:8000/health", "API Server"):
                    print("⚠️  APIサーバーが停止しています。再起動中...")
                    if self.api_process:
                        self.api_process.terminate()
                    self.start_api_server()
                
                # Webクライアントの状態チェック
                if not self.check_server("http://localhost:3000", "Web Client"):
                    print("⚠️  Webクライアントが停止しています。再起動中...")
                    if self.web_process:
                        self.web_process.terminate()
                    self.start_web_client()
                
                time.sleep(10)  # 10秒間隔でチェック
                
            except KeyboardInterrupt:
                print("\n🛑 監視を停止します...")
                self.running = False
                break
            except Exception as e:
                print(f"❌ 監視エラー: {e}")
                time.sleep(5)
    
    def cleanup(self):
        """プロセスのクリーンアップ"""
        if self.api_process:
            self.api_process.terminate()
        if self.web_process:
            self.web_process.terminate()

if __name__ == "__main__":
    monitor = ServerMonitor()
    try:
        monitor.monitor_loop()
    finally:
        monitor.cleanup()

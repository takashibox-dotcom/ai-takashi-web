#!/usr/bin/env python3
"""
Webクライアント用の簡単なHTTPサーバー
開発・テスト用
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

def main():
    # web-clientディレクトリに移動
    web_client_dir = Path(__file__).parent
    os.chdir(web_client_dir)
    
    # ポート設定
    PORT = 3000
    
    # HTTPサーバー作成
    Handler = http.server.SimpleHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"🌐 Webクライアントサーバーを起動しました")
            print(f"📱 URL: http://localhost:{PORT}")
            print(f"📁 ディレクトリ: {web_client_dir}")
            print(f"⏹️  終了: Ctrl+C")
            print()
            
            # ブラウザで自動オープン
            webbrowser.open(f'http://localhost:{PORT}')
            
            # サーバー開始
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 サーバーを停止しました")
        sys.exit(0)
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"❌ ポート {PORT} は既に使用されています")
            print(f"💡 別のポートを試してください: python serve.py --port 3001")
        else:
            print(f"❌ サーバー起動エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # コマンドライン引数処理
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("AI Takashi Web Client サーバー")
        print("使用方法: python serve.py [--port PORT]")
        print("デフォルトポート: 3000")
        sys.exit(0)
    
    # ポート指定の処理
    if len(sys.argv) > 2 and sys.argv[1] == "--port":
        try:
            PORT = int(sys.argv[2])
        except ValueError:
            print("❌ 無効なポート番号です")
            sys.exit(1)
    
    main()

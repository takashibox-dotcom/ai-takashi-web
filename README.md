# AI Takashi Web Client

## 🌐 GitHub Pages でデプロイされたWebアプリケーション

AI TakashiのWebベースクライアントです。ブラウザからAIとのチャット、キャラクター管理、画像認識などの機能を利用できます。

### 🚀 アクセス方法

**Live Demo**: [https://YOUR_USERNAME.github.io/ai-takashi-web/](https://YOUR_USERNAME.github.io/ai-takashi-web/)

### ✨ 主要機能

- ✅ **チャット機能**: テキスト・画像対応のAIチャット
- ✅ **キャラクター管理**: カスタムキャラクターの作成・選択
- ✅ **トークン管理**: 使用量の表示・リセット
- ✅ **セッション管理**: 会話履歴の管理
- ✅ **レスポンシブデザイン**: PC・スマホ対応
- ✅ **ダークモード**: テーマ切り替え機能
- ✅ **リアルタイム接続**: サーバー状態の監視

### 🛠️ 技術スタック

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Backend**: FastAPI (Python)
- **Hosting**: GitHub Pages (Frontend), Heroku/Railway/Render (Backend)
- **AI**: Google Gemini API

### 📱 対応ブラウザ

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

### 🚀 デプロイ手順

詳細なデプロイ手順は [deploy-to-github.md](deploy-to-github.md) をご覧ください。

#### 簡単デプロイ手順

1. **リポジトリをフォーク**
2. **Settings → Pages** でSourceを `/web-client` に設定
3. **API URLを本番環境用に変更**
4. **完了！**

### 🔧 ローカル開発

```bash
# リポジトリをクローン
git clone https://github.com/YOUR_USERNAME/ai-takashi-web.git
cd ai-takashi-web

# Webクライアントを起動
cd web-client
python serve.py

# ブラウザで http://localhost:3000 にアクセス
```

### 📁 プロジェクト構成

```
ai-takashi-web/
├── web-client/           # Webクライアント
│   ├── index.html       # メインHTML
│   ├── styles.css       # スタイルシート
│   ├── app.js           # JavaScriptアプリ
│   └── serve.py         # 開発サーバー
├── deploy-to-github.md  # デプロイ手順
├── requirements-web.txt # 依存関係
└── README.md           # このファイル
```

### 🔒 セキュリティ

- HTTPS通信の強制
- CORS設定による安全なAPI通信
- 環境変数によるAPIキー管理

### 📊 機能一覧

| 機能 | ステータス | 説明 |
|------|------------|------|
| チャット機能 | ✅ | テキスト・画像対応 |
| キャラクター作成 | ✅ | カスタムキャラクター |
| トークン管理 | ✅ | 使用量表示・リセット |
| セッション管理 | ✅ | 会話履歴管理 |
| レスポンシブUI | ✅ | モバイル対応 |
| ダークモード | ✅ | テーマ切り替え |
| メモリ機能 | 🔄 | 今後実装予定 |
| エクスポート | 🔄 | 今後実装予定 |
| バックアップ | 🔄 | 今後実装予定 |

### 🤝 貢献

1. リポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

### 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

### 🆘 サポート

問題が発生した場合：
1. [Issues](https://github.com/YOUR_USERNAME/ai-takashi-web/issues) で報告
2. [Wiki](https://github.com/YOUR_USERNAME/ai-takashi-web/wiki) でドキュメント確認

### 🎯 今後の予定

- 🔄 PWA対応（オフライン機能）
- 🔄 WebSocket対応（リアルタイム通信）
- 🔄 WebRTC対応（音声チャット）
- 🔄 多言語対応
- 🔄 プラグインシステム

---

**AI Takashi Web Client** - どこからでもアクセス可能なAIチャットアプリ 🚀

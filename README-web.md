# AI Takashi Web Client

## 🌐 新しいWebベースアーキテクチャ

### **概要**
- **APIサーバー**: FastAPIをクラウドにデプロイ
- **Webクライアント**: HTML/CSS/JavaScriptでブラウザから操作
- **軽量**: ブラウザがあればどこからでもアクセス可能

### **アーキテクチャ**

```
┌─────────────────┐    HTTP/HTTPS    ┌─────────────────┐
│   Web Client    │ ───────────────► │   API Server    │
│  (HTML/CSS/JS)  │                  │    (FastAPI)    │
│                 │ ◄─────────────── │                 │
└─────────────────┘                  └─────────────────┘
     │                                        │
     ▼                                        ▼
┌─────────┐                            ┌─────────────┐
│ Browser │                            │ Cloud Host  │
│  User   │                            │ (Heroku/    │
│         │                            │  Railway/    │
└─────────┘                            │  Render)     │
                                       └─────────────┘
```

### **🚀 デプロイ手順**

#### **1. APIサーバーのデプロイ**

**Heroku でのデプロイ:**
```bash
# 1. Heroku CLI をインストール
# https://devcenter.heroku.com/articles/heroku-cli

# 2. ログイン
heroku login

# 3. アプリケーション作成
heroku create ai-takashi-api

# 4. 環境変数設定
heroku config:set GOOGLE_API_KEY=your_api_key_here

# 5. デプロイ
git add .
git commit -m "Deploy API server"
git push heroku main

# 6. API URLを確認
heroku apps:info
```

**Railway でのデプロイ:**
```bash
# 1. Railway CLI をインストール
npm install -g @railway/cli

# 2. ログイン
railway login

# 3. プロジェクト初期化
railway init

# 4. デプロイ
railway up
```

**Render でのデプロイ:**
1. https://render.com にアクセス
2. "New +" → "Web Service" を選択
3. GitHubリポジトリを接続
4. 設定:
   - Build Command: `pip install -r requirements-web.txt`
   - Start Command: `uvicorn api_server:app --host 0.0.0.0 --port $PORT`
   - Environment Variables: `GOOGLE_API_KEY=your_key`

#### **2. Webクライアントのデプロイ**

**Netlify でのデプロイ:**
```bash
# 1. Netlify CLI をインストール
npm install -g netlify-cli

# 2. ログイン
netlify login

# 3. サイト作成
netlify init

# 4. デプロイ
netlify deploy --prod
```

**Vercel でのデプロイ:**
```bash
# 1. Vercel CLI をインストール
npm install -g vercel

# 2. ログイン
vercel login

# 3. デプロイ
vercel --prod
```

**GitHub Pages でのデプロイ:**
1. GitHubリポジトリの Settings → Pages
2. Source: Deploy from a branch
3. Branch: main, Folder: /web-client
4. 保存

### **🔧 設定変更**

デプロイ後、WebクライアントのAPI URLを更新:

**web-client/app.js の 5行目:**
```javascript
// 変更前
this.apiUrl = 'http://localhost:8000';

// 変更後（Herokuの場合）
this.apiUrl = 'https://ai-takashi-api.herokuapp.com';

// 変更後（Railwayの場合）
this.apiUrl = 'https://your-app-name.railway.app';

// 変更後（Renderの場合）
this.apiUrl = 'https://your-app-name.onrender.com';
```

### **📁 ファイル構成**

```
project/
├── api_server.py              # FastAPIサーバー
├── requirements-web.txt       # 本番環境用依存関係
├── web-client/               # Webクライアント
│   ├── index.html            # メインHTML
│   ├── styles.css            # スタイルシート
│   └── app.js                # JavaScriptアプリ
├── netlify.toml              # Netlify設定
├── vercel.json               # Vercel設定
└── README-web.md             # このファイル
```

### **✨ 機能一覧**

#### **✅ 実装済み機能**
- ✅ チャット機能
- ✅ 画像認識
- ✅ キャラクター管理
- ✅ トークン使用量表示
- ✅ セッション管理
- ✅ レスポンシブデザイン
- ✅ ダークモード
- ✅ リアルタイム接続チェック

#### **🔄 今後実装予定**
- 🔄 メモリ管理
- 🔄 エクスポート機能
- 🔄 バックアップ管理
- 🔄 キャラクター編集
- 🔄 会話履歴管理

### **🌍 アクセス方法**

デプロイ後、以下のURLでアクセス可能:
- **Netlify**: `https://your-site-name.netlify.app`
- **Vercel**: `https://your-site-name.vercel.app`
- **GitHub Pages**: `https://username.github.io/repository-name`

### **🔒 セキュリティ考慮事項**

1. **CORS設定**: APIサーバーで適切なCORS設定
2. **API Key**: 環境変数でAPIキーを管理
3. **HTTPS**: 本番環境では必ずHTTPSを使用
4. **Rate Limiting**: APIサーバーにレート制限を実装

### **📱 対応ブラウザ**

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

### **🚀 今後の拡張**

1. **PWA対応**: オフライン機能追加
2. **WebSocket**: リアルタイム通信
3. **WebRTC**: 音声チャット機能
4. **IndexedDB**: ローカルデータ保存
5. **Service Worker**: キャッシュ機能

この新しいアーキテクチャにより、どこからでもアクセス可能な軽量なWebアプリケーションが完成します！

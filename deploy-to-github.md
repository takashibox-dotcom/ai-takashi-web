# GitHub Pages デプロイ手順

## 🚀 完全なデプロイ手順

### **Step 1: GitHubリポジトリの作成**

1. **GitHubにログイン**: https://github.com
2. **新しいリポジトリを作成**:
   - Repository name: `ai-takashi-web`
   - Description: `AI Takashi Web Client - GitHub Pages`
   - Public: ✅ (GitHub Pagesは無料プランでPublicリポジトリのみ)
   - Initialize with README: ❌ (既存ファイルがあるため)

### **Step 2: ローカルでGitリポジトリを初期化**

```bash
# プロジェクトディレクトリで実行
git init
git add .
git commit -m "Initial commit: AI Takashi Web Client"
```

### **Step 3: GitHubリポジトリと接続**

```bash
# リモートリポジトリを追加（YOUR_USERNAMEを実際のユーザー名に変更）
git remote add origin https://github.com/YOUR_USERNAME/ai-takashi-web.git

# メインブランチにプッシュ
git branch -M main
git push -u origin main
```

### **Step 4: GitHub Pagesの設定**

1. **リポジトリページに移動**: `https://github.com/YOUR_USERNAME/ai-takashi-web`
2. **Settings タブをクリック**
3. **左サイドバーで「Pages」を選択**
4. **Source を設定**:
   - Source: `Deploy from a branch`
   - Branch: `main`
   - Folder: `/web-client` ← 重要！
5. **Save をクリック**

### **Step 5: デプロイ完了**

数分後、以下のURLでアクセス可能になります：
`https://YOUR_USERNAME.github.io/ai-takashi-web/`

### **Step 6: API URLの設定**

デプロイ後、WebクライアントのAPI URLを本番環境用に変更する必要があります。

**web-client/app.js の 5行目を変更**:
```javascript
// 変更前（ローカル開発用）
this.apiUrl = 'http://localhost:8000';

// 変更後（本番環境用）
this.apiUrl = 'https://YOUR_API_SERVER.herokuapp.com';
// または
this.apiUrl = 'https://YOUR_API_SERVER.railway.app';
// または
this.apiUrl = 'https://YOUR_API_SERVER.onrender.com';
```

変更後、再度コミット・プッシュ：
```bash
git add web-client/app.js
git commit -m "Update API URL for production"
git push origin main
```

## 🔧 カスタムドメインの設定（オプション）

独自ドメインを使用したい場合：

1. **カスタムドメインを購入**（例: `aitakashi.com`）
2. **DNS設定**:
   ```
   Type: CNAME
   Name: www
   Value: YOUR_USERNAME.github.io
   ```
3. **GitHub Pages設定**:
   - Custom domain: `www.aitakashi.com`
   - Enforce HTTPS: ✅

## 📁 最終的なファイル構成

```
ai-takashi-web/
├── .gitignore
├── README.md
├── requirements-web.txt
├── netlify.toml
├── vercel.json
├── deploy-to-github.md
└── web-client/
    ├── index.html
    ├── styles.css
    ├── app.js
    ├── serve.py
    └── start.bat
```

## 🚨 重要な注意点

### **CORS設定**
APIサーバーでCORSを適切に設定する必要があります：

```python
# api_server.py に追加
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://YOUR_USERNAME.github.io",
        "http://localhost:3000"  # 開発用
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### **HTTPS対応**
GitHub Pagesは自動的にHTTPSを提供します。APIサーバーもHTTPS対応が必要です。

### **APIサーバーのデプロイ**
APIサーバーは別途以下のいずれかにデプロイ：
- **Heroku**: `heroku create ai-takashi-api`
- **Railway**: `railway up`
- **Render**: Webサービスとして新規作成

## 🔄 更新手順

コードを更新した場合：

```bash
# 変更をコミット
git add .
git commit -m "Update feature description"
git push origin main

# GitHub Pagesが自動的に再デプロイされます（数分かかります）
```

## 📊 デプロイ状況の確認

1. **Actions タブ**: デプロイの進行状況を確認
2. **Settings → Pages**: デプロイの状態を確認
3. **URL**: `https://YOUR_USERNAME.github.io/ai-takashi-web/`

## 🎯 成功の確認

デプロイが成功すると：
- ✅ Webサイトが表示される
- ✅ APIとの通信が可能
- ✅ レスポンシブデザインが動作
- ✅ ダークモードが切り替わる
- ✅ チャット機能が動作

これで、GitHub Pagesでの完全なデプロイが完了します！🎉

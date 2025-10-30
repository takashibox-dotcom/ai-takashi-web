// AI Takashi Web Client Configuration
const CONFIG = {
    // API設定
    API_URLS: {
        // 開発環境
        development: 'http://localhost:8000',
        
        // 本番環境の例（実際のデプロイ時に変更してください）
        production: 'https://your-api-server.herokuapp.com', // APIサーバーのURLに変更してください
        
        // その他のホスティングサービス例
        railway: 'https://your-app-name.railway.app',
        render: 'https://your-app-name.onrender.com',
        vercel: 'https://your-api.vercel.app'
    },
    
    // 環境設定
    ENVIRONMENT: 'development', // 'development' または 'production'
    
    // アプリケーション設定
    APP: {
        name: 'AI Takashi Web Client',
        version: '1.0.0',
        description: 'AI Takashi Web-based Client Application'
    },
    
    // UI設定
    UI: {
        defaultTheme: 'light', // 'light' または 'dark'
        autoSave: true,
        connectionCheckInterval: 5000, // ミリ秒
        messageHistoryLimit: 100
    },
    
    // デバッグ設定
    DEBUG: {
        enabled: false,
        logLevel: 'info' // 'debug', 'info', 'warn', 'error'
    }
};

// 現在の環境に応じてAPI URLを取得
function getApiUrl() {
    const env = CONFIG.ENVIRONMENT;
    return CONFIG.API_URLS[env] || CONFIG.API_URLS.development;
}

// 設定をエクスポート
if (typeof module !== 'undefined' && module.exports) {
    // Node.js環境
    module.exports = { CONFIG, getApiUrl };
} else {
    // ブラウザ環境
    window.CONFIG = CONFIG;
    window.getApiUrl = getApiUrl;
}

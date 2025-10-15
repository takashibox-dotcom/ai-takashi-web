// AI Takashi Web Client
class AITakashiWebClient {
    constructor() {
        // 設定ファイルからAPI URLを取得
        this.apiUrl = window.getApiUrl ? window.getApiUrl() : 'http://localhost:8000';
        this.sessionId = this.generateSessionId();
        this.selectedImage = null;
        this.isDarkMode = false;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkConnection();
        this.loadCharacters();
        this.updateSessionDisplay();
        this.setupConnectionCheck();
    }

    generateSessionId() {
        const timestamp = new Date().toISOString().replace(/[-:T]/g, '').split('.')[0];
        const random = Math.random().toString(36).substr(2, 4);
        return `session_${timestamp}_${random}`;
    }

    setupEventListeners() {
        // タブ切り替え
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // チャット関連
        document.getElementById('sendBtn').addEventListener('click', () => this.sendMessage());
        document.getElementById('userInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // キャラクター関連
        document.getElementById('createCharacterBtn').addEventListener('click', () => this.showCharacterModal());
        document.getElementById('manageCharacterBtn').addEventListener('click', () => this.showCharacterSelector());
        document.getElementById('characterSelect').addEventListener('change', (e) => this.selectCharacter(e.target.value));

        // 画像関連
        document.getElementById('selectImageBtn').addEventListener('click', () => this.selectImage());
        document.getElementById('clearImageBtn').addEventListener('click', () => this.clearImage());

        // セッション管理
        document.getElementById('newSessionBtn').addEventListener('click', () => this.newSession());
        document.getElementById('clearChatBtn').addEventListener('click', () => this.clearChat());

        // トークン管理
        document.getElementById('resetTokenBtn').addEventListener('click', () => this.resetTokenUsage());

        // メモリ管理
        document.getElementById('createMemoryBtn').addEventListener('click', () => this.createMemory());
        document.getElementById('saveMemoryBtn').addEventListener('click', () => this.saveMemory());
        document.getElementById('refreshMemoryBtn').addEventListener('click', () => this.refreshMemories());

        // フッターボタン
        document.getElementById('exportBtn').addEventListener('click', () => this.exportConversation());
        document.getElementById('backupBtn').addEventListener('click', () => this.showBackupManager());
        document.getElementById('aboutBtn').addEventListener('click', () => this.showAbout());
        document.getElementById('themeBtn').addEventListener('click', () => this.toggleTheme());

        // キャラクター作成フォーム
        document.getElementById('characterForm').addEventListener('submit', (e) => this.createCharacter(e));
        document.getElementById('previewCharBtn').addEventListener('click', () => this.previewCharacter());
        document.getElementById('cancelCharBtn').addEventListener('click', () => this.closeCharacterModal());

        // モーダル
        document.querySelectorAll('.close').forEach(closeBtn => {
            closeBtn.addEventListener('click', (e) => this.closeModal(e.target.closest('.modal')));
        });

        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal(e.target);
            }
        });
    }

    async checkConnection() {
        try {
            const response = await fetch(`${this.apiUrl}/health`);
            if (response.ok) {
                this.updateConnectionStatus(true);
                return true;
            }
        } catch (error) {
            console.error('Connection check failed:', error);
        }
        this.updateConnectionStatus(false);
        return false;
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('statusIndicator');
        const text = document.getElementById('statusText');
        
        if (connected) {
            indicator.className = 'status-indicator connected';
            text.textContent = 'サーバー接続中';
        } else {
            indicator.className = 'status-indicator disconnected';
            text.textContent = 'サーバー未接続';
        }
    }

    setupConnectionCheck() {
        setInterval(() => this.checkConnection(), 5000);
    }

    updateSessionDisplay() {
        document.getElementById('sessionId').textContent = this.sessionId;
    }

    switchTab(tabName) {
        // タブボタンの状態更新
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // タブコンテンツの表示切り替え
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        document.getElementById(`${tabName}-tab`).classList.add('active');

        // タブ固有の処理
        if (tabName === 'tokens') {
            this.loadTokenUsage();
        } else if (tabName === 'memory') {
            this.refreshMemories();
        }
    }

    async loadCharacters() {
        try {
            const response = await fetch(`${this.apiUrl}/api/characters`);
            if (response.ok) {
                const data = await response.json();
                const select = document.getElementById('characterSelect');
                select.innerHTML = '<option value="">デフォルト</option>';
                
                data.characters.forEach(character => {
                    const option = document.createElement('option');
                    option.value = character.id;
                    option.textContent = character.name;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to load characters:', error);
        }
    }

    selectCharacter(characterId) {
        const characterSelect = document.getElementById('characterSelect');
        const selectedOption = characterSelect.options[characterSelect.selectedIndex];
        document.getElementById('characterDisplay').textContent = selectedOption.textContent;
    }

    async sendMessage() {
        const input = document.getElementById('userInput');
        const message = input.value.trim();
        
        if (!message) return;

        const sendBtn = document.getElementById('sendBtn');
        const progressBar = document.getElementById('progressBar');
        
        // UI状態更新
        this.addMessage('user', message);
        input.value = '';
        sendBtn.disabled = true;
        sendBtn.textContent = '送信中...';
        progressBar.style.display = 'block';

        try {
            const requestData = {
                message: message,
                session_id: this.sessionId,
                character_id: document.getElementById('characterSelect').value || null
            };

            // 画像がある場合はマルチパートフォームで送信
            let response;
            if (this.selectedImage) {
                const formData = new FormData();
                formData.append('message', message);
                formData.append('session_id', this.sessionId);
                formData.append('character_id', requestData.character_id || '');
                formData.append('image', this.selectedImage);

                response = await fetch(`${this.apiUrl}/api/chat/image`, {
                    method: 'POST',
                    body: formData
                });
            } else {
                response = await fetch(`${this.apiUrl}/api/chat`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
            }

            if (response.ok) {
                const data = await response.json();
                this.addMessage('assistant', data.response);
                
                // トークン使用量更新
                this.loadTokenUsage();
            } else {
                this.addMessage('assistant', 'エラーが発生しました。もう一度お試しください。');
            }
        } catch (error) {
            console.error('Failed to send message:', error);
            this.addMessage('assistant', '接続エラーが発生しました。サーバーの状態を確認してください。');
        } finally {
            // UI状態復元
            sendBtn.disabled = false;
            sendBtn.textContent = '送信';
            progressBar.style.display = 'none';
        }
    }

    addMessage(type, content) {
        const chatHistory = document.getElementById('chatHistory');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const headerDiv = document.createElement('div');
        headerDiv.className = 'message-header';
        headerDiv.textContent = `${type === 'user' ? 'あなた' : 'AI Takashi'} - ${new Date().toLocaleString()}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;
        
        messageDiv.appendChild(headerDiv);
        messageDiv.appendChild(contentDiv);
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    selectImage() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                this.selectedImage = file;
                document.getElementById('imageDisplay').textContent = file.name;
            }
        };
        input.click();
    }

    clearImage() {
        this.selectedImage = null;
        document.getElementById('imageDisplay').textContent = '画像が選択されていません';
    }

    newSession() {
        this.sessionId = this.generateSessionId();
        this.updateSessionDisplay();
        this.clearChat();
    }

    clearChat() {
        document.getElementById('chatHistory').innerHTML = '';
    }

    async loadTokenUsage() {
        try {
            const response = await fetch(`${this.apiUrl}/api/tokens/usage`);
            if (response.ok) {
                const data = await response.json();
                const tokenDisplay = document.getElementById('tokenDisplay');
                const tokenDisplayLarge = document.getElementById('tokenDisplayLarge');
                
                const tokenText = `総トークン数: ${data.total_tokens.toLocaleString()}`;
                tokenDisplay.textContent = tokenText;
                tokenDisplayLarge.textContent = tokenText;
            }
        } catch (error) {
            console.error('Failed to load token usage:', error);
        }
    }

    async resetTokenUsage() {
        if (confirm('トークン使用量をリセットしますか？')) {
            try {
                const response = await fetch(`${this.apiUrl}/api/tokens/reset`, {
                    method: 'POST'
                });
                if (response.ok) {
                    this.loadTokenUsage();
                    alert('トークン使用量をリセットしました。');
                }
            } catch (error) {
                console.error('Failed to reset token usage:', error);
                alert('リセットに失敗しました。');
            }
        }
    }

    async refreshMemories() {
        try {
            const response = await fetch(`${this.apiUrl}/api/memories`);
            if (response.ok) {
                const data = await response.json();
                const memoryList = document.getElementById('memoryList');
                memoryList.innerHTML = '';
                
                data.memories.forEach(memory => {
                    const memoryDiv = document.createElement('div');
                    memoryDiv.className = 'memory-item';
                    memoryDiv.innerHTML = `
                        <div class="memory-title">${memory.title}</div>
                        <div class="memory-content">${memory.content.substring(0, 100)}...</div>
                        <div class="memory-meta">作成日: ${new Date(memory.created_at).toLocaleString()}</div>
                    `;
                    memoryList.appendChild(memoryDiv);
                });
            }
        } catch (error) {
            console.error('Failed to load memories:', error);
        }
    }

    createMemory() {
        alert('メモリ作成機能は今後実装予定です。');
    }

    saveMemory() {
        alert('メモリ保存機能は今後実装予定です。');
    }

    showCharacterModal() {
        document.getElementById('characterModal').style.display = 'block';
    }

    closeCharacterModal() {
        document.getElementById('characterModal').style.display = 'none';
        document.getElementById('characterForm').reset();
    }

    async createCharacter(e) {
        e.preventDefault();
        
        const formData = {
            name: document.getElementById('charName').value,
            personality: document.getElementById('charPersonality').value,
            speaking_style: document.getElementById('charSpeaking').value,
            specialization: document.getElementById('charSpecialization').value,
            response_style: document.getElementById('charResponse').value,
            background: document.getElementById('charBackground').value,
            catchphrase: document.getElementById('charCatchphrase').value,
            greeting: document.getElementById('charGreeting').value
        };

        try {
            const response = await fetch(`${this.apiUrl}/api/characters`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                alert(`キャラクター「${formData.name}」を作成しました！`);
                this.closeCharacterModal();
                this.loadCharacters();
            } else {
                alert('キャラクターの作成に失敗しました。');
            }
        } catch (error) {
            console.error('Failed to create character:', error);
            alert('キャラクターの作成に失敗しました。');
        }
    }

    previewCharacter() {
        alert('プレビュー機能は今後実装予定です。');
    }

    showCharacterSelector() {
        alert('キャラクター管理機能は今後実装予定です。');
    }

    exportConversation() {
        alert('エクスポート機能は今後実装予定です。');
    }

    showBackupManager() {
        alert('バックアップ管理機能は今後実装予定です。');
    }

    showAbout() {
        alert(`AI Takashi Web Client v1.0.0

APIサーバーと通信するWebベースのクライアントです。
既存のGUIと同等の機能を提供します。

主要機能:
• チャット機能
• 画像認識
• キャラクター管理
• トークン管理
• メモリ機能
• エクスポート機能
• バックアップ管理`);
    }

    toggleTheme() {
        this.isDarkMode = !this.isDarkMode;
        document.body.classList.toggle('dark-mode', this.isDarkMode);
        
        const themeBtn = document.getElementById('themeBtn');
        themeBtn.textContent = this.isDarkMode ? '☀️' : '🌙';
    }

    closeModal(modal) {
        modal.style.display = 'none';
    }
}

// アプリケーション初期化
document.addEventListener('DOMContentLoaded', () => {
    new AITakashiWebClient();
});

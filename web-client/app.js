// AI Takashi Web Client - Updated 2025-01-21 12:34:56
class AITakashiWebClient {
    constructor() {
        // 設定ファイルからAPI URLを取得
        this.apiUrl = window.getApiUrl ? window.getApiUrl() : 'http://localhost:8000';
        this.sessionId = this.generateSessionId();
        // ユーザー管理（簡易版：ローカルストレージを使用）
        this.userId = this.getOrCreateUserId();
        this.selectedImage = null;
        this.isDarkMode = false;
        // アカウント管理
        this.authSessionId = null;
        this.currentUser = null;
        
        // エラーハンドリング用
        this.retryCount = 0;
        this.maxRetries = 3;
        this.retryDelay = 1000; // 1秒
        
        // ログイン状態追跡用
        this.wasLoggedIn = false;
        
        // 会話履歴管理
        this.conversationHistory = [];
        this.autoSaveInterval = null;
        
        // イベントリスナー管理用
        this.eventListeners = new Map();
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.checkConnection();
        this.updateSessionDisplay();
        this.setupConnectionCheck();
        await this.loadAuthSession();
        this.updateAccountDisplay();
        // ログイン状態に応じてキャラクター機能を制御
        this.loadCharacters();
        
        // 会話履歴の自動保存を開始
        this.startAutoSave();
    }

    generateSessionId() {
        const timestamp = new Date().toISOString().replace(/[-:T]/g, '').split('.')[0];
        const random = Math.random().toString(36).substr(2, 4);
        return `session_${timestamp}_${random}`;
    }

    // イベントリスナーのクリーンアップ
    cleanupEventListeners() {
        this.eventListeners.forEach((listener, element) => {
            element.removeEventListener(listener.event, listener.handler);
        });
        this.eventListeners.clear();
    }

    // 特定の要素のイベントリスナーを削除
    removeEventListener(element, event, handler) {
        element.removeEventListener(event, handler);
        this.eventListeners.delete(element);
    }

    // 会話履歴ボタンの表示制御を復元
    showConversationHistoryButtons() {
        const historyButtons = ['refreshHistoryBtn', 'saveConversationBtn', 'clearHistoryBtn', 'exportBtn'];
        historyButtons.forEach(buttonId => {
            const button = document.getElementById(buttonId);
            if (button) {
                // インラインスタイルを削除してCSSに委ねる
                button.style.display = '';
                button.style.visibility = '';
                button.style.opacity = '';
            }
        });
    }

    getOrCreateUserId() {
        // ログイン済みの場合は実際のユーザーIDを使用
        if (this.currentUser) {
            return this.currentUser.user_id;
        }
        
        // 未ログインの場合は一時的なユーザーIDを作成
        const timestamp = new Date().toISOString().replace(/[-:T]/g, '').split('.')[0];
        const random = Math.random().toString(36).substr(2, 8);
        return `temp_user_${timestamp}_${random}`;
    }

    setupEventListeners() {
        // タブ切り替え
        document.querySelectorAll('.tab-button').forEach(button => {
            const handler = (e) => this.switchTab(e.target.dataset.tab);
            button.addEventListener('click', handler);
            this.eventListeners.set(button, { event: 'click', handler });
        });

        // チャット関連
        const sendBtn = document.getElementById('sendBtn');
        const sendHandler = () => {
            this.sendMessage();
        };
        sendBtn.addEventListener('click', sendHandler);
        this.eventListeners.set(sendBtn, { event: 'click', handler: sendHandler });
        document.getElementById('userInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // キャラクター関連
        document.getElementById('createCharacterBtn').addEventListener('click', () => this.showCharacterModal());
        document.getElementById('manageCharacterBtn').addEventListener('click', () => {
            this.showCharacterSelector();
        });
        document.getElementById('characterSelect').addEventListener('change', (e) => this.selectCharacter(e.target.value));

        // 画像関連
        document.getElementById('selectImageBtn').addEventListener('click', () => this.selectImage());
        document.getElementById('clearImageBtn').addEventListener('click', () => this.clearImage());

        // セッション管理
        document.getElementById('newSessionBtn').addEventListener('click', () => this.newSession());
        document.getElementById('clearChatBtn').addEventListener('click', () => this.clearChat());

        // トークン管理
        document.getElementById('resetTokenBtn').addEventListener('click', () => this.resetTokenUsage());

        // メモリ関連のイベントリスナーは削除（機能を会話履歴に統合）
        
        // 会話履歴管理
        const refreshBtn = document.getElementById('refreshHistoryBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshConversationHistory());
        } else {
            console.error('refreshHistoryBtn 要素が見つかりません');
        }
        
        const clearBtn = document.getElementById('clearHistoryBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearConversationHistory());
        }
        
        // 検索機能
        const searchBtn = document.getElementById('historySearchBtn');
        if (searchBtn) {
            searchBtn.addEventListener('click', () => this.searchConversationHistory());
        }
        
        const clearSearchBtn = document.getElementById('clearSearchBtn');
        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', () => this.clearSearch());
        }
        document.getElementById('historySearchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchConversationHistory();
            }
        });
        
        // 手動保存ボタン
        document.getElementById('saveConversationBtn').addEventListener('click', () => this.manualSaveConversation());
        
        // 自動保存制御
        document.getElementById('autoSaveToggle').addEventListener('change', (e) => this.toggleAutoSave(e.target.checked));
        
        // 緊急ログイン（デバッグ用）
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'L') {
                this.emergencyLogin();
            }
        });
        
        // 管理タブ切り替え（今後実装予定）
        // setupManagementTabsメソッドは未実装のため削除

        // フッターボタン
        document.getElementById('exportBtn').addEventListener('click', () => this.exportConversation());
        document.getElementById('backupBtn').addEventListener('click', () => this.showBackupManager());
        document.getElementById('aboutBtn').addEventListener('click', () => this.showAbout());
        document.getElementById('themeBtn').addEventListener('click', () => this.toggleTheme());

        // アカウント管理
        document.getElementById('loginBtn').addEventListener('click', () => this.login());
        document.getElementById('registerBtn').addEventListener('click', () => this.register());
        document.getElementById('showRegisterBtn').addEventListener('click', () => this.showRegisterForm());
        document.getElementById('showResetPasswordBtn').addEventListener('click', () => this.showResetPasswordForm());
        document.getElementById('backToLoginBtn').addEventListener('click', () => this.backToLoginForm());
        document.getElementById('resetPasswordBtn').addEventListener('click', () => this.resetPassword());
        document.getElementById('showLoginBtn').addEventListener('click', () => this.showLoginForm());
        document.getElementById('logoutBtn').addEventListener('click', () => this.logout());
        document.getElementById('editProfileBtn').addEventListener('click', () => this.showProfileModal());
        document.getElementById('changePasswordBtn').addEventListener('click', () => this.showPasswordModal());
        
        // モーダル管理
        document.getElementById('closeProfileModal').addEventListener('click', () => this.closeModal('profileModal'));
        document.getElementById('closePasswordModal').addEventListener('click', () => this.closeModal('passwordModal'));
        document.getElementById('saveProfileBtn').addEventListener('click', () => this.saveProfile());
        document.getElementById('savePasswordBtn').addEventListener('click', () => this.changePassword());
        document.getElementById('cancelProfileBtn').addEventListener('click', () => this.closeModal('profileModal'));
        document.getElementById('cancelPasswordBtn').addEventListener('click', () => this.closeModal('passwordModal'));

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
        document.getElementById('sessionId').textContent = `${this.sessionId} (ユーザー: ${this.userId.substring(0, 12)}...)`;
    }


    switchTab(tabName) {
        // タブボタンの状態更新
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
            btn.setAttribute('aria-selected', 'false');
        });
        const activeButton = document.querySelector(`[data-tab="${tabName}"]`);
        activeButton.classList.add('active');
        activeButton.setAttribute('aria-selected', 'true');

        // タブコンテンツの表示切り替え
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
            content.setAttribute('aria-hidden', 'true');
        });
        const activeContent = document.getElementById(tabName);
        activeContent.classList.add('active');
        activeContent.setAttribute('aria-hidden', 'false');

        // タブ固有の処理
        if (tabName === 'tokens-tab') {
            this.loadTokenUsage();
        } else if (tabName === 'memory-tab') {
            this.refreshConversationHistory();
            this.updateAutoSaveStatus(this.autoSaveInterval !== null);
            // 会話履歴ボタンの表示制御を復元
            this.showConversationHistoryButtons();
        }
    }

    async loadCharacters() {
        const select = document.getElementById('characterSelect');
        
        // ログインしていない場合はデフォルトのみ表示
        if (!this.currentUser) {
            select.innerHTML = '<option value="default">デフォルト（ログインが必要）</option>';
            return;
        }
        
        // ログイン済みの場合は常にデフォルトオプションを表示
        select.innerHTML = '<option value="default">デフォルト</option>';
        
        try {
            const response = await fetch(`${this.apiUrl}/api/characters?user_id=${this.userId}`);
            if (response.ok) {
                const data = await response.json();
                
                // ユーザーのキャラクターを追加（重複チェック付き）
                data.characters.forEach(character => {
                    // 既に同じIDのオプションが存在しないかチェック
                    const existingOption = select.querySelector(`option[value="${character.id}"]`);
                    if (!existingOption) {
                    const option = document.createElement('option');
                    option.value = character.id;
                    option.textContent = character.name;
                    select.appendChild(option);
                    }
                });
            }
        } catch (error) {
            console.error('Failed to load characters:', error);
            // エラーが発生してもデフォルトオプションは表示されたまま
        }
    }

    selectCharacter(characterId) {
        // ログイン状態をチェック
        if (!this.currentUser) {
            alert('キャラクター選択にはログインが必要です。アカウントタブでログインしてください。');
            return;
        }
        
        const characterSelect = document.getElementById('characterSelect');
        const selectedOption = characterSelect.options[characterSelect.selectedIndex];
        document.getElementById('characterDisplay').textContent = selectedOption.textContent;
    }

    async sendMessage() {
        console.log('sendMessage が呼ばれました');
        const input = document.getElementById('userInput');
        const message = input.value.trim();
        
        console.log('入力メッセージ:', message);
        if (!message) {
            console.log('メッセージが空のため送信をキャンセル');
            return;
        }

        const sendBtn = document.getElementById('sendBtn');
        const progressBar = document.getElementById('progressBar');
        const responseTimeElement = document.getElementById('responseTime');
        
        // UI状態更新
        this.addMessage('user', message);
        input.value = '';
        sendBtn.disabled = true;
        sendBtn.textContent = '送信中...';
        progressBar.style.display = 'block';
        
        // 応答時間の計測開始
        const startTime = Date.now();
        responseTimeElement.textContent = '送信中...';

        try {
            const result = await this.retryWithBackoff(async () => {
            const requestData = {
                message: message,
                session_id: this.sessionId,
                character_id: document.getElementById('characterSelect').value || 'default',
                user_id: this.userId
            };
            
            console.log('Sending request:', requestData);

            // 画像がある場合はマルチパートフォームで送信
            let response;
            if (this.selectedImage) {
                const formData = new FormData();
                formData.append('message', message);
                formData.append('session_id', this.sessionId);
                formData.append('character_id', requestData.character_id || 'default');
                formData.append('user_id', this.userId);
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

            console.log('Response status:', response.status, response.statusText);
            
            if (response.ok) {
                const data = await response.json();
                console.log('Response data:', data);
                this.addMessage('assistant', data.response);
                
                // トークン使用量更新
                this.loadTokenUsage();
                
                return data; // 成功時はデータを返す
            } else {
                    // APIエラーの詳細処理
                    this.handleApiError(response, 'チャット送信');
                    throw new Error(`API Error: ${response.status}`);
                }
            }, 'チャット送信');
            
            // 応答時間の計算と表示（成功時のみ）
            const endTime = Date.now();
            const responseTimeMs = endTime - startTime;
            const responseTimeSec = (responseTimeMs / 1000).toFixed(2);
            console.log('応答時間計算:', { startTime, endTime, responseTimeMs, responseTimeSec });
            responseTimeElement.textContent = `${responseTimeSec}秒`;
            console.log('応答時間表示を更新しました:', `${responseTimeSec}秒`);

        } catch (error) {
            console.error('Failed to send message:', error);
            this.handleNetworkError(error, 'チャット送信');
            
            // エラー時の応答時間表示
            responseTimeElement.textContent = 'エラー';
            
            // エラー時のメッセージ表示（簡易版）
            this.addMessage('assistant', 'メッセージの送信に失敗しました。再試行してください。');
        } finally {
            // UI状態復元
            console.log('Restoring UI state...');
            sendBtn.disabled = false;
            sendBtn.textContent = '送信';
            progressBar.style.display = 'none';
            
            // 応答時間を待機中に戻す（エラー時のみ）
            console.log('finallyブロック実行:', responseTimeElement.textContent);
            if (responseTimeElement.textContent === 'エラー' || responseTimeElement.textContent === '送信中...') {
                responseTimeElement.textContent = '待機中';
                console.log('応答時間を「待機中」にリセットしました');
            }
            
            console.log('UI state restored');
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
                if (tokenDisplay) {
                    tokenDisplay.textContent = tokenText;
                }
                if (tokenDisplayLarge) {
                    tokenDisplayLarge.textContent = tokenText;
                }
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
        console.log('refreshMemories が呼ばれました');
        try {
            // ユーザーIDを含めてAPIを呼び出し
            const url = this.userId ? `${this.apiUrl}/api/memories?user_id=${this.userId}` : `${this.apiUrl}/api/memories`;
            const response = await fetch(url);
            if (response.ok) {
                const memories = await response.json();
                console.log('メモリ一覧を取得:', memories);
                this.displayMemories(memories);
            } else {
                console.error('Failed to load memories:', response.statusText);
                this.displayMemories([]);
            }
        } catch (error) {
            console.error('Failed to load memories:', error);
            this.displayMemories([]);
        }
    }
    
    displayMemories(memories) {
        console.log('displayMemories が呼ばれました:', memories);
                const memoryList = document.getElementById('memoryList');
                
        if (!memories || memories.length === 0) {
                    memoryList.innerHTML = '<div class="no-memories">記憶された会話はありません。</div>';
                    return;
                }
                
        memoryList.innerHTML = memories.map(memory => `
            <div class="memory-item" data-memory-id="${memory.id}">
                <div class="memory-header">
                    <h4 class="memory-title">${memory.title}</h4>
                    <span class="memory-category">${memory.category}</span>
                    <span class="memory-importance importance-${memory.importance}">${memory.importance}</span>
                </div>
                <div class="memory-content">${memory.content.substring(0, 100)}${memory.content.length > 100 ? '...' : ''}</div>
                <div class="memory-meta">
                    <span class="memory-date">${new Date(memory.created_at).toLocaleDateString('ja-JP')}</span>
                    <span class="memory-character">${memory.character_id}</span>
                </div>
                <div class="memory-actions">
                    <button class="btn btn-small btn-primary" onclick="app.viewMemory('${memory.id}')">詳細</button>
                    <button class="btn btn-small btn-secondary" onclick="app.editMemory('${memory.id}')">編集</button>
                    <button class="btn btn-small btn-danger" onclick="app.deleteMemory('${memory.id}')">削除</button>
                </div>
            </div>
        `).join('');
    }

    async createMemory() {
        console.log('createMemory が呼ばれました');
        
        // 現在の会話履歴を取得
        const chatHistory = document.getElementById('chatHistory');
        const messages = chatHistory.querySelectorAll('.message');
        
        if (messages.length === 0) {
            alert('保存する会話がありません。');
            return;
        }
        
        // 会話履歴をテキストに変換
        let conversationText = '';
        messages.forEach(message => {
            const type = message.classList.contains('user-message') ? 'ユーザー' : 'AI';
            const content = message.querySelector('.message-content').textContent;
            conversationText += `${type}: ${content}\n`;
        });
        
        // メモリタイトルを入力
        const title = prompt('メモリのタイトルを入力してください:', '会話メモリ');
        if (!title) return;
        
        try {
            const memoryData = {
                title: title,
                content: conversationText,
                character_id: document.getElementById('characterSelect').value || 'default',
                character_name: 'AI_takashi',
                conversation_history: Array.from(messages).map(msg => ({
                    type: msg.classList.contains('user-message') ? 'user' : 'assistant',
                    content: msg.querySelector('.message-content').textContent
                })),
                category: 'その他',
                tags: [],
                importance: '中'
            };
            
            console.log('メモリデータを作成:', memoryData);
            
            // ユーザーIDを含めてAPIを呼び出し
            const url = this.userId ? `${this.apiUrl}/api/memories?user_id=${this.userId}` : `${this.apiUrl}/api/memories`;
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(memoryData)
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('メモリ作成成功:', result);
                alert('メモリを作成しました！');
                this.refreshMemories(); // メモリ一覧を更新
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
        } catch (error) {
            console.error('メモリ作成エラー:', error);
            alert('メモリの作成に失敗しました。');
        }
    }
    
    async viewMemory(memoryId) {
        console.log('viewMemory が呼ばれました:', memoryId);
        
        try {
            // ユーザーIDを含めてAPIを呼び出し
            const url = this.userId ? `${this.apiUrl}/api/memories/${memoryId}?user_id=${this.userId}` : `${this.apiUrl}/api/memories/${memoryId}`;
            const response = await fetch(url);
            
            if (response.ok) {
                const memory = await response.json();
                console.log('メモリ詳細を取得:', memory);
                this.showMemoryDetailModal(memory);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
        } catch (error) {
            console.error('メモリ詳細取得エラー:', error);
            console.error('エラーの詳細:', {
                message: error.message,
                stack: error.stack,
                memoryId: memoryId,
                userId: this.userId,
                url: this.userId ? `${this.apiUrl}/api/memories/${memoryId}?user_id=${this.userId}` : `${this.apiUrl}/api/memories/${memoryId}`
            });
            alert(`メモリの詳細取得に失敗しました: ${error.message}`);
        }
    }
    
    showMemoryDetailModal(memory) {
        console.log('showMemoryDetailModal が呼ばれました:', memory);
        
        // モーダルの内容を設定
        document.getElementById('memoryDetailTitle').textContent = memory.title;
        document.getElementById('memoryDetailCategory').textContent = memory.category;
        document.getElementById('memoryDetailImportance').textContent = memory.importance;
        document.getElementById('memoryDetailImportance').className = `memory-importance importance-${memory.importance}`;
        document.getElementById('memoryDetailDate').textContent = new Date(memory.created_at).toLocaleString('ja-JP');
        document.getElementById('memoryDetailCharacter').textContent = memory.character_id;
        document.getElementById('memoryDetailText').textContent = memory.content;
        
        // タグの表示
        if (memory.tags && memory.tags.length > 0) {
            document.getElementById('memoryDetailTags').style.display = 'block';
            const tagsList = document.getElementById('memoryDetailTagsList');
            tagsList.innerHTML = memory.tags.map(tag => `<span class="tag">${tag}</span>`).join('');
        } else {
            document.getElementById('memoryDetailTags').style.display = 'none';
        }
        
        // モーダルを表示
        const modal = document.getElementById('memoryDetailModal');
        modal.style.display = 'block';
        
        // 現在のメモリIDを保存（編集・削除用）
        this.currentMemoryId = memory.id;
    }
    
    closeMemoryDetailModal() {
        console.log('closeMemoryDetailModal が呼ばれました');
        const modal = document.getElementById('memoryDetailModal');
        modal.style.display = 'none';
        this.currentMemoryId = null;
    }
    
    async editMemoryFromDetail() {
        console.log('editMemoryFromDetail が呼ばれました');
        if (this.currentMemoryId) {
            this.closeMemoryDetailModal();
            this.editMemory(this.currentMemoryId);
        }
    }
    
    async deleteMemoryFromDetail() {
        console.log('deleteMemoryFromDetail が呼ばれました');
        if (this.currentMemoryId) {
            this.closeMemoryDetailModal();
            this.deleteMemory(this.currentMemoryId);
        }
    }
    
    async editMemory(memoryId) {
        console.log('editMemory が呼ばれました:', memoryId);
        // 編集機能は後で実装
        alert('メモリ編集機能は今後実装予定です。');
    }
    
    async deleteMemory(memoryId) {
        console.log('deleteMemory が呼ばれました:', memoryId);
        
        if (!confirm('このメモリを削除しますか？')) {
            return;
        }
        
        try {
            // ユーザーIDを含めてAPIを呼び出し
            const url = this.userId ? `${this.apiUrl}/api/memories/${memoryId}?user_id=${this.userId}` : `${this.apiUrl}/api/memories/${memoryId}`;
            const response = await fetch(url, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                console.log('メモリ削除成功');
                alert('メモリを削除しました。');
                this.refreshMemories(); // メモリ一覧を更新
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
        } catch (error) {
            console.error('メモリ削除エラー:', error);
            alert('メモリの削除に失敗しました。');
        }
    }
    
    startAutoSave() {
        console.log('会話履歴の自動保存を開始しました');
        // 既存のタイマーをクリア
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
        // 5分ごとに会話履歴を自動保存
        this.autoSaveInterval = setInterval(() => {
            this.autoSaveConversation();
            this.updateLastSaveTime();
        }, 5 * 60 * 1000); // 5分
        this.updateAutoSaveStatus(true);
    }
    
    stopAutoSave() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = null;
            console.log('会話履歴の自動保存を停止しました');
        }
        this.updateAutoSaveStatus(false);
    }
    
    autoSaveConversation() {
        try {
            const chatHistory = document.getElementById('chatHistory');
            const messages = chatHistory.querySelectorAll('.message');
            
            if (messages.length === 0) {
                return; // 保存する会話がない場合は何もしない
            }
            
            // 会話履歴を更新
            this.conversationHistory = Array.from(messages).map(message => {
                const type = message.classList.contains('user-message') ? 'user' : 'assistant';
                const content = message.querySelector('.message-content').textContent;
                return { type, content };
            });
            
            // ローカルストレージに保存
            const saveData = {
                sessionId: this.sessionId,
                userId: this.userId,
                timestamp: new Date().toISOString(),
                conversation: this.conversationHistory
            };
            
            localStorage.setItem(`conversation_${this.sessionId}`, JSON.stringify(saveData));
            console.log('会話履歴を自動保存しました');
            
        } catch (error) {
            console.error('会話履歴の自動保存エラー:', error);
        }
    }
    
    loadConversationHistory(sessionId) {
        try {
            const savedData = localStorage.getItem(`conversation_${sessionId}`);
            if (savedData) {
                const data = JSON.parse(savedData);
                this.conversationHistory = data.conversation || [];
                
                // 会話履歴をチャット画面に復元
                this.restoreConversationToChat();
                console.log('会話履歴を復元しました:', data);
                return true;
            }
        } catch (error) {
            console.error('会話履歴の読み込みエラー:', error);
        }
        return false;
    }
    
    restoreConversationToChat() {
        const chatHistory = document.getElementById('chatHistory');
        chatHistory.innerHTML = ''; // 既存の会話をクリア
        
        this.conversationHistory.forEach(messageData => {
            this.addMessage(messageData.type, messageData.content);
        });
        
        console.log('会話履歴をチャット画面に復元しました');
    }
    
    getSavedConversations() {
        console.log('getSavedConversations が呼ばれました');
        const conversations = [];
        
        // localStorageの内容をデバッグ出力
        console.log('localStorage keys:', Object.keys(localStorage));
        
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            console.log('Checking key:', key);
            if (key && key.startsWith('conversation_')) {
                try {
                    const data = JSON.parse(localStorage.getItem(key));
                    console.log('Found conversation data:', data);
                    conversations.push({
                        sessionId: data.sessionId,
                        userId: data.userId,
                        timestamp: data.timestamp,
                        messageCount: data.conversation ? data.conversation.length : 0
                    });
                } catch (error) {
                    console.error('会話履歴の解析エラー:', error);
                }
            }
        }
        
        console.log('Found conversations:', conversations);
        
        // タイムスタンプでソート（新しい順）
        return conversations.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    }
    
    refreshConversationHistory() {
        console.log('refreshConversationHistory が呼ばれました');
        const conversations = this.getSavedConversations();
        
        // テスト用：会話データがない場合はサンプルデータを追加
        if (conversations.length === 0) {
            console.log('会話データがないため、サンプルデータを追加します');
            this.addSampleConversation();
            const updatedConversations = this.getSavedConversations();
            this.displayConversationHistory(updatedConversations);
        } else {
            this.displayConversationHistory(conversations);
        }
    }
    
    addSampleConversation() {
        const sampleData = {
            sessionId: 'sample_session_' + Date.now(),
            userId: 'test_user',
            timestamp: new Date().toISOString(),
            conversation: [
                { role: 'user', content: 'こんにちは！', timestamp: new Date().toISOString() },
                { role: 'assistant', content: 'こんにちは！お声がけいただきありがとうございます。', timestamp: new Date().toISOString() }
            ]
        };
        
        localStorage.setItem(`conversation_${sampleData.sessionId}`, JSON.stringify(sampleData));
        console.log('サンプル会話データを追加しました:', sampleData);
    }
    
    displayConversationHistory(conversations) {
        console.log('displayConversationHistory が呼ばれました:', conversations);
        const historyList = document.getElementById('conversationHistoryList');
        
        if (!historyList) {
            console.error('conversationHistoryList element not found');
            return;
        }
        
        // 強制的に表示を確保
        historyList.style.display = 'block';
        historyList.style.visibility = 'visible';
        historyList.style.opacity = '1';
        
        if (!conversations || conversations.length === 0) {
            historyList.innerHTML = '<div class="no-history" style="padding: 2rem; text-align: center; color: #666;">保存された会話履歴がありません<br><br>チャットタブで会話を開始すると、ここに履歴が表示されます。</div>';
            return;
        }
        
        console.log('会話履歴を表示します:', conversations.length, '件');
        
        historyList.innerHTML = conversations.map(conv => `
            <div class="conversation-item" data-session-id="${conv.sessionId}" style="padding: 1rem; border: 1px solid #ddd; margin-bottom: 0.5rem; border-radius: 5px; background: white;">
                <div class="conversation-header">
                    <h4 class="conversation-title" style="margin: 0 0 0.5rem 0; color: #333;">セッション: ${conv.sessionId.substring(0, 20)}...</h4>
                    <span class="conversation-message-count" style="color: #666; font-size: 0.9rem;">${conv.messageCount}件のメッセージ</span>
                </div>
                <div class="conversation-meta" style="margin: 0.5rem 0; font-size: 0.8rem; color: #666;">
                    <span class="conversation-date">${new Date(conv.timestamp).toLocaleString('ja-JP')}</span>
                    <span class="conversation-user">ユーザー: ${conv.userId ? conv.userId.substring(0, 12) + '...' : '未ログイン'}</span>
                </div>
                <div class="conversation-actions" style="margin-top: 0.5rem;">
                    <button class="btn btn-small btn-primary" onclick="app.continueConversation('${conv.sessionId}')" style="margin-right: 0.5rem;">続きから</button>
                    <button class="btn btn-small btn-secondary" onclick="app.viewConversationHistory('${conv.sessionId}')" style="margin-right: 0.5rem;">詳細</button>
                    <button class="btn btn-small btn-danger" onclick="app.deleteConversationHistory('${conv.sessionId}')">削除</button>
                </div>
            </div>
        `).join('');
        
        console.log('会話履歴の表示完了');
    }
    
    continueConversation(sessionId) {
        console.log('continueConversation が呼ばれました:', sessionId);
        
        if (confirm('この会話を続行しますか？現在の会話はクリアされます。')) {
            // 現在のセッションIDを変更
            this.sessionId = sessionId;
            this.updateSessionDisplay();
            
            // 会話履歴を復元
            if (this.loadConversationHistory(sessionId)) {
                alert('会話を復元しました。続きから会話を開始できます。');
                // チャットタブに切り替え
                this.switchTab('chat');
            } else {
                alert('会話履歴の復元に失敗しました。');
            }
        }
    }
    
    viewConversationHistory(sessionId) {
        console.log('viewConversationHistory が呼ばれました:', sessionId);
        // 会話履歴の詳細表示（今後実装）
        alert('会話履歴の詳細表示機能は今後実装予定です。');
    }
    
    deleteConversationHistory(sessionId) {
        console.log('deleteConversationHistory が呼ばれました:', sessionId);
        
        if (confirm('この会話履歴を削除しますか？')) {
            localStorage.removeItem(`conversation_${sessionId}`);
            this.refreshConversationHistory();
            alert('会話履歴を削除しました。');
        }
    }
    
    clearConversationHistory() {
        console.log('clearConversationHistory が呼ばれました');
        
        if (confirm('全ての会話履歴を削除しますか？この操作は取り消せません。')) {
            // conversation_で始まるキーを全て削除
            for (let i = localStorage.length - 1; i >= 0; i--) {
                const key = localStorage.key(i);
                if (key && key.startsWith('conversation_')) {
                    localStorage.removeItem(key);
                }
            }
            
            this.refreshConversationHistory();
            alert('全ての会話履歴を削除しました。');
        }
    }
    
    manualSaveConversation() {
        console.log('manualSaveConversation が呼ばれました');
        this.autoSaveConversation();
        this.updateLastSaveTime();
        alert('会話履歴を手動保存しました！');
    }
    
    toggleAutoSave(enabled) {
        console.log('自動保存設定変更:', enabled);
        if (enabled) {
            this.startAutoSave();
            this.updateAutoSaveStatus(true);
        } else {
            this.stopAutoSave();
            this.updateAutoSaveStatus(false);
        }
    }
    
    updateAutoSaveStatus(isActive) {
        const statusElement = document.getElementById('autoSaveStatus');
        if (statusElement) {
            if (isActive) {
                statusElement.textContent = '● 自動保存中';
                statusElement.style.color = '#28a745';
            } else {
                statusElement.textContent = '● 自動保存停止';
                statusElement.style.color = '#dc3545';
            }
        }
    }
    
    updateLastSaveTime() {
        const lastSaveElement = document.getElementById('lastSaveTime');
        if (lastSaveElement) {
            const now = new Date();
            lastSaveElement.textContent = `最終保存: ${now.toLocaleTimeString()}`;
        }
    }
    
    searchConversationHistory() {
        const searchTerm = document.getElementById('historySearchInput').value.trim();
        console.log('会話履歴検索:', searchTerm);
        
        if (!searchTerm) {
            this.refreshConversationHistory();
            return;
        }
        
        const conversations = this.getSavedConversations();
        const filteredConversations = conversations.filter(conversation => {
            // セッションID、ユーザーID、メッセージ内容で検索
            const sessionIdMatch = conversation.sessionId.toLowerCase().includes(searchTerm.toLowerCase());
            const userIdMatch = conversation.userId.toLowerCase().includes(searchTerm.toLowerCase());
            const messageMatch = conversation.conversation.some(msg => 
                msg.content.toLowerCase().includes(searchTerm.toLowerCase())
            );
            
            return sessionIdMatch || userIdMatch || messageMatch;
        });
        
        this.displayConversationHistory(filteredConversations);
        
        if (filteredConversations.length === 0) {
            alert(`"${searchTerm}" に一致する会話が見つかりませんでした。`);
        }
    }
    
    clearSearch() {
        document.getElementById('historySearchInput').value = '';
        this.refreshConversationHistory();
    }
    
    emergencyLogin() {
        console.log('緊急ログインを実行します');
        // 最初のユーザーでログイン
        this.authSessionId = 'emergency_session_' + Date.now();
        this.currentUser = {
            user_id: 'user_20251015165136_978c2322',
            username: 'ｔｋｔｋｔｋ',
            email: 'u041122n@kajiwara.jp'
        };
        localStorage.setItem('auth_session_id', this.authSessionId);
        this.userId = this.getOrCreateUserId();
        this.updateAccountDisplay();
        alert('緊急ログインが完了しました（Ctrl+Shift+L）');
    }

    async saveMemory() {
        try {
            // 現在の会話履歴を取得
            const chatHistory = document.getElementById('chatHistory');
            const messages = chatHistory.querySelectorAll('.message');
            
            if (messages.length === 0) {
                alert('保存する会話がありません。');
                return;
            }

            // 会話内容を収集
            const conversation = [];
            messages.forEach(message => {
                const content = message.querySelector('.message-content');
                if (content) {
                    conversation.push(content.textContent.trim());
                }
            });

            if (conversation.length === 0) {
                alert('保存する会話内容がありません。');
                return;
            }

            // 記憶のタイトルを入力
            const title = prompt('記憶のタイトルを入力してください:', `会話記録 ${new Date().toLocaleString()}`);
            if (!title) return;

            // 記憶データを作成
            const memoryData = {
                title: title,
                content: conversation.join('\n'),
                category: '会話記録',
                tags: ['会話', 'チャット'],
                importance: '中',
                character_id: document.getElementById('characterSelect').value || 'default',
                character_name: document.getElementById('characterSelect').selectedOptions[0]?.text || 'デフォルト',
                conversation_history: conversation
            };

            // APIに送信
            const url = this.userId ? `${this.apiUrl}/api/memories?user_id=${this.userId}` : `${this.apiUrl}/api/memories`;
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(memoryData)
            });

            if (response.ok) {
                alert('会話を記憶しました！');
                // 記憶一覧を更新
                this.refreshMemories();
            } else {
                alert('記憶の保存に失敗しました。');
            }
        } catch (error) {
            console.error('Failed to save memory:', error);
            alert('記憶の保存に失敗しました。');
        }
    }


    showCharacterModal() {
        // ログイン状態をチェック
        if (!this.currentUser) {
            alert('キャラクター作成にはログインが必要です。アカウントタブでログインしてください。');
            return;
        }
        
        document.getElementById('characterModal').style.display = 'block';
    }

    closeCharacterModal() {
        document.getElementById('characterModal').style.display = 'none';
        document.getElementById('characterForm').reset();
    }

    async createCharacter(e) {
        e.preventDefault();
        
        // ログイン状態をチェック
        if (!this.currentUser) {
            alert('キャラクター作成にはログインが必要です。アカウントタブでログインしてください。');
            return;
        }
        
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
            const response = await fetch(`${this.apiUrl}/api/characters?user_id=${this.userId}`, {
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

    async previewCharacter(characterId) {
        console.log(`previewCharacter が呼ばれました: ${characterId}`);
        try {
            console.log(`キャラクター情報を取得中: ${characterId}`);
            const response = await fetch(`${this.apiUrl}/api/characters/${characterId}?user_id=${this.userId}`);
            if (response.ok) {
                const character = await response.json();
                console.log('キャラクター情報取得成功:', character);
                this.showCharacterPreview(character);
            } else {
                console.error('キャラクター情報取得エラー:', response.status);
                this.handleApiError(response, 'キャラクター情報取得');
            }
        } catch (error) {
            console.error('キャラクター情報取得ネットワークエラー:', error);
            this.handleNetworkError(error, 'キャラクター情報取得');
        }
    }

    showCharacterPreview(character) {
        console.log('showCharacterPreview が呼ばれました:', character);
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content character-preview">
                <span class="close">&times;</span>
                <h3>キャラクター詳細: ${character.name}</h3>
                <div class="character-preview-content">
                    <div class="preview-section">
                        <h4>基本情報</h4>
                        <p><strong>名前:</strong> ${character.name}</p>
                        <p><strong>説明:</strong> ${character.description}</p>
                        <p><strong>性格:</strong> ${character.personality || '未設定'}</p>
                        <p><strong>話し方:</strong> ${character.speaking_style || '未設定'}</p>
                        <p><strong>専門分野:</strong> ${character.specialization || '未設定'}</p>
                    </div>
                    <div class="preview-section">
                        <h4>システムプロンプト</h4>
                        <div class="system-prompt">${character.system_prompt}</div>
                    </div>
                    <div class="preview-section">
                        <h4>追加設定</h4>
                        <p><strong>応答スタイル:</strong> ${character.response_style || '未設定'}</p>
                        <p><strong>背景:</strong> ${character.background || '未設定'}</p>
                        <p><strong>キャッチフレーズ:</strong> ${character.catchphrase || '未設定'}</p>
                        <p><strong>挨拶:</strong> ${character.greeting || '未設定'}</p>
                    </div>
                </div>
                <div class="preview-actions">
                    <button class="btn btn-primary" onclick="this.closest('.modal').remove()">閉じる</button>
                    <button class="btn btn-warning" onclick="app.editCharacter('${character.id}'); this.closest('.modal').remove();">編集</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        modal.style.display = 'block';
        console.log('プレビューモーダルを表示しました');
        
        // イベントリスナー設定
        modal.querySelector('.close').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    async editCharacter(characterId) {
        console.log(`editCharacter が呼ばれました: ${characterId}`);
        try {
            console.log(`キャラクター情報を取得中: ${characterId}`);
            const response = await fetch(`${this.apiUrl}/api/characters/${characterId}?user_id=${this.userId}`);
            if (response.ok) {
                const character = await response.json();
                console.log('キャラクター情報取得成功:', character);
                this.showCharacterEditModal(character);
            } else {
                console.error('キャラクター情報取得エラー:', response.status);
                this.handleApiError(response, 'キャラクター情報取得');
            }
        } catch (error) {
            console.error('キャラクター情報取得ネットワークエラー:', error);
            this.handleNetworkError(error, 'キャラクター情報取得');
        }
    }

    showCharacterEditModal(character) {
        console.log('showCharacterEditModal が呼ばれました:', character);
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content character-edit">
                <span class="close">&times;</span>
                <h3>キャラクター編集: ${character.name}</h3>
                <form id="editCharacterForm">
                    <div class="form-group">
                        <label for="editCharName">キャラクター名 *</label>
                        <input type="text" id="editCharName" value="${character.name}" required>
                    </div>
                    <div class="form-group">
                        <label for="editCharPersonality">性格</label>
                        <textarea id="editCharPersonality" rows="3">${character.personality || ''}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="editCharSpeaking">話し方</label>
                        <textarea id="editCharSpeaking" rows="3">${character.speaking_style || ''}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="editCharSpecialization">専門分野</label>
                        <input type="text" id="editCharSpecialization" value="${character.specialization || ''}">
                    </div>
                    <div class="form-group">
                        <label for="editCharResponse">応答スタイル</label>
                        <textarea id="editCharResponse" rows="3">${character.response_style || ''}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="editCharBackground">背景</label>
                        <textarea id="editCharBackground" rows="3">${character.background || ''}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="editCharCatchphrase">キャッチフレーズ</label>
                        <input type="text" id="editCharCatchphrase" value="${character.catchphrase || ''}">
                    </div>
                    <div class="form-group">
                        <label for="editCharGreeting">挨拶</label>
                        <textarea id="editCharGreeting" rows="2">${character.greeting || ''}</textarea>
                    </div>
                    <div class="form-actions">
                        <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">キャンセル</button>
                        <button type="submit" class="btn btn-primary">更新</button>
                    </div>
                </form>
            </div>
        `;
        
        document.body.appendChild(modal);
        modal.style.display = 'block';
        console.log('編集モーダルを表示しました');
        
        // フォーム送信イベント
        modal.querySelector('#editCharacterForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.updateCharacter(character.id, modal);
        });
        
        // 閉じるイベント
        modal.querySelector('.close').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    async updateCharacter(characterId, modal) {
        const formData = {
            name: modal.querySelector('#editCharName').value,
            personality: modal.querySelector('#editCharPersonality').value,
            speaking_style: modal.querySelector('#editCharSpeaking').value,
            specialization: modal.querySelector('#editCharSpecialization').value,
            response_style: modal.querySelector('#editCharResponse').value,
            background: modal.querySelector('#editCharBackground').value,
            catchphrase: modal.querySelector('#editCharCatchphrase').value,
            greeting: modal.querySelector('#editCharGreeting').value
        };

        try {
            const response = await fetch(`${this.apiUrl}/api/characters/${characterId}?user_id=${this.userId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                alert(`キャラクター「${formData.name}」を更新しました！`);
                modal.remove();
                this.loadCharacterList(); // 一覧を更新
                this.loadCharacters(); // 選択肢も更新
            } else {
                this.handleApiError(response, 'キャラクター更新');
            }
        } catch (error) {
            this.handleNetworkError(error, 'キャラクター更新');
        }
    }

    async deleteCharacter(characterId) {
        const characterName = document.querySelector(`[data-character-id="${characterId}"] .character-name`).textContent;
        
        if (!confirm(`キャラクター「${characterName}」を削除しますか？\nこの操作は取り消せません。`)) {
            return;
        }

        try {
            const response = await fetch(`${this.apiUrl}/api/characters/${characterId}?user_id=${this.userId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                alert(`キャラクター「${characterName}」を削除しました。`);
                this.loadCharacterList(); // 一覧を更新
                this.loadCharacters(); // 選択肢も更新
            } else {
                this.handleApiError(response, 'キャラクター削除');
            }
        } catch (error) {
            this.handleNetworkError(error, 'キャラクター削除');
        }
    }

    showCharacterSelector() {
        console.log('管理ボタンがクリックされました');
        console.log('現在のユーザー:', this.currentUser);
        
        // ログイン状態をチェック
        if (!this.currentUser) {
            alert('キャラクター管理にはログインが必要です。アカウントタブでログインしてください。');
            return;
        }
        
        console.log('ログイン済み、管理モーダルを表示します');
        this.showCharacterManagementModal();
    }

    showCharacterManagementModal() {
        console.log('showCharacterManagementModal が呼ばれました');
        
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content character-management">
                <span class="close">&times;</span>
                <h3>キャラクター管理</h3>
                <div class="character-list-container">
                    <div class="character-actions">
                        <button id="refreshCharacterList" class="btn btn-primary">更新</button>
                        <button id="createNewCharacter" class="btn btn-success">新規作成</button>
                    </div>
                    <div id="characterList" class="character-list">
                        <div class="loading">読み込み中...</div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        console.log('モーダルをDOMに追加しました');
        
        // モーダルを表示
        modal.style.display = 'block';
        console.log('モーダルの表示スタイルを設定しました');
        
        // イベントリスナー設定
        modal.querySelector('.close').addEventListener('click', () => modal.remove());
        modal.querySelector('#refreshCharacterList').addEventListener('click', () => this.loadCharacterList());
        modal.querySelector('#createNewCharacter').addEventListener('click', () => {
            modal.remove();
            this.showCharacterModal();
        });
        
        // モーダル外クリックで閉じる
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        // キャラクター一覧を読み込み
        console.log('キャラクター一覧の読み込みを開始します');
        this.loadCharacterList();
    }

    async loadCharacterList() {
        const characterList = document.getElementById('characterList');
        if (!characterList) return;
        
        characterList.innerHTML = '<div class="loading">読み込み中...</div>';
        
        try {
            const response = await fetch(`${this.apiUrl}/api/characters?user_id=${this.userId}`);
            if (response.ok) {
                const data = await response.json();
                this.renderCharacterList(data.characters);
            } else {
                this.handleApiError(response, 'キャラクター一覧取得');
            }
        } catch (error) {
            this.handleNetworkError(error, 'キャラクター一覧取得');
        }
    }

    renderCharacterList(characters) {
        const characterList = document.getElementById('characterList');
        if (!characterList) return;
        
        if (characters.length === 0) {
            characterList.innerHTML = '<div class="no-characters">キャラクターがありません。<br>「新規作成」ボタンからキャラクターを作成してください。</div>';
            return;
        }
        
        characterList.innerHTML = characters.map(character => `
            <div class="character-item" data-character-id="${character.id}">
                <div class="character-info">
                    <h4 class="character-name">${character.name}</h4>
                    <p class="character-description">${character.description}</p>
                    <div class="character-details">
                        <span class="character-personality">性格: ${character.personality || '未設定'}</span>
                        <span class="character-specialization">専門: ${character.specialization || '未設定'}</span>
                    </div>
                </div>
                <div class="character-actions">
                    <button class="btn btn-sm btn-info" data-action="preview" data-character-id="${character.id}">プレビュー</button>
                    <button class="btn btn-sm btn-warning" data-action="edit" data-character-id="${character.id}">編集</button>
                    <button class="btn btn-sm btn-danger" data-action="delete" data-character-id="${character.id}">削除</button>
                </div>
            </div>
        `).join('');
        
        // イベントリスナーを設定
        this.setupCharacterActionListeners();
    }

    setupCharacterActionListeners() {
        console.log('setupCharacterActionListeners が呼ばれました');
        const characterList = document.getElementById('characterList');
        if (!characterList) {
            console.error('characterList 要素が見つかりません');
            return;
        }

        console.log('characterList 要素が見つかりました:', characterList);

        // 既存のイベントリスナーを削除（重複防止）
        characterList.removeEventListener('click', this.characterActionHandler);
        
        // イベント委譲を使用してボタンクリックを処理
        this.characterActionHandler = (e) => {
            console.log('キャラクターリストでクリックイベントが発生しました:', e.target);
            const button = e.target.closest('button[data-action]');
            if (!button) {
                console.log('data-action属性を持つボタンではありません');
                return;
            }

            const action = button.dataset.action;
            const characterId = button.dataset.characterId;

            console.log(`キャラクターアクション: ${action}, ID: ${characterId}`);

            switch (action) {
                case 'preview':
                    this.previewCharacter(characterId);
                    break;
                case 'edit':
                    this.editCharacter(characterId);
                    break;
                case 'delete':
                    this.deleteCharacter(characterId);
                    break;
            }
        };

        characterList.addEventListener('click', this.characterActionHandler);
        console.log('キャラクターアクションのイベントリスナーを設定しました');
    }

    exportConversation() {
        const chatHistory = document.getElementById('chatHistory');
        const messages = chatHistory.querySelectorAll('.message');
        
        if (messages.length === 0) {
            alert('エクスポートする会話がありません。');
            return;
        }

        // エクスポート形式を選択
        const format = prompt('エクスポート形式を選択してください:\n1. TXT形式\n2. JSON形式\n3. HTML形式\n\n番号を入力してください (1-3):');
        
        if (!format || !['1', '2', '3'].includes(format)) {
            alert('無効な選択です。');
            return;
        }

        switch(format) {
            case '1':
                this.exportAsTXT(messages);
                break;
            case '2':
                this.exportAsJSON(messages);
                break;
            case '3':
                this.exportAsHTML(messages);
                break;
        }
    }

    exportAsTXT(messages) {
        let content = `AI Takashi 会話履歴\n`;
        content += `エクスポート日時: ${new Date().toLocaleString()}\n`;
        content += `セッションID: ${this.sessionId}\n`;
        content += `ユーザーID: ${this.userId}\n`;
        content += `${'='.repeat(50)}\n\n`;

        messages.forEach(message => {
            const header = message.querySelector('.message-header');
            const messageContent = message.querySelector('.message-content');
            
            if (header && messageContent) {
                content += `${header.textContent}\n`;
                content += `${messageContent.textContent}\n\n`;
            }
        });

        this.downloadFile(content, 'ai_takashi_conversation.txt', 'text/plain');
    }

    exportAsJSON(messages) {
        const conversation = {
            metadata: {
                exportDate: new Date().toISOString(),
                sessionId: this.sessionId,
                userId: this.userId,
                messageCount: messages.length
            },
            messages: []
        };

        messages.forEach(message => {
            const header = message.querySelector('.message-header');
            const messageContent = message.querySelector('.message-content');
            
            if (header && messageContent) {
                const isUser = message.classList.contains('user');
                conversation.messages.push({
                    type: isUser ? 'user' : 'assistant',
                    timestamp: header.textContent.split(' - ')[1],
                    content: messageContent.textContent
                });
            }
        });

        this.downloadFile(
            JSON.stringify(conversation, null, 2), 
            'ai_takashi_conversation.json', 
            'application/json'
        );
    }

    exportAsHTML(messages) {
        let html = `<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Takashi 会話履歴</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .message { margin-bottom: 15px; padding: 10px; border-radius: 5px; }
        .message.user { background: #e3f2fd; border-left: 4px solid #2196f3; }
        .message.assistant { background: #f3e5f5; border-left: 4px solid #9c27b0; }
        .message-header { font-weight: bold; margin-bottom: 5px; color: #666; }
        .message-content { white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="header">
        <h1>AI Takashi 会話履歴</h1>
        <p><strong>エクスポート日時:</strong> ${new Date().toLocaleString()}</p>
        <p><strong>セッションID:</strong> ${this.sessionId}</p>
        <p><strong>ユーザーID:</strong> ${this.userId}</p>
        <p><strong>メッセージ数:</strong> ${messages.length}</p>
    </div>`;

        messages.forEach(message => {
            const header = message.querySelector('.message-header');
            const messageContent = message.querySelector('.message-content');
            
            if (header && messageContent) {
                html += `
    <div class="message ${message.classList.contains('user') ? 'user' : 'assistant'}">
        <div class="message-header">${header.textContent}</div>
        <div class="message-content">${messageContent.textContent}</div>
    </div>`;
            }
        });

        html += `
</body>
</html>`;

        this.downloadFile(html, 'ai_takashi_conversation.html', 'text/html');
    }

    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);
        alert(`${filename} をダウンロードしました。`);
    }

    // エラーハンドリング関連のメソッド
    showErrorMessage(title, message, error = null) {
        // 詳細なエラー情報を含むモーダルを表示
        const errorModal = document.createElement('div');
        errorModal.className = 'modal error-modal';
        errorModal.innerHTML = `
            <div class="modal-content error-content">
                <span class="close">&times;</span>
                <h3>❌ ${title}</h3>
                <p class="error-message">${message}</p>
                ${error ? `<details class="error-details">
                    <summary>技術的詳細</summary>
                    <pre>${error.stack || error.toString()}</pre>
                </details>` : ''}
                <div class="error-actions">
                    <button onclick="this.closest('.modal').remove()" class="btn btn-primary">閉じる</button>
                    ${this.retryCount < this.maxRetries ? '<button onclick="this.retryLastAction()" class="btn btn-secondary">再試行</button>' : ''}
                </div>
            </div>
        `;
        
        document.body.appendChild(errorModal);
        
        // 閉じるボタンのイベント
        errorModal.querySelector('.close').addEventListener('click', () => {
            errorModal.remove();
        });
        
        // モーダル外クリックで閉じる
        errorModal.addEventListener('click', (e) => {
            if (e.target === errorModal) {
                errorModal.remove();
            }
        });
    }

    async retryWithBackoff(operation, context = '') {
        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                this.retryCount = attempt;
                const result = await operation();
                this.retryCount = 0; // 成功したらリセット
                return result;
            } catch (error) {
                console.error(`${context} - 試行 ${attempt}/${this.maxRetries} 失敗:`, error);
                
                if (attempt === this.maxRetries) {
                    // 最後の試行でも失敗
                    this.retryCount = 0;
                    throw error;
                }
                
                // 指数バックオフで待機
                const delay = this.retryDelay * Math.pow(2, attempt - 1);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }

    handleApiError(response, context = 'API呼び出し') {
        const statusCode = response.status;
        let title, message;
        
        switch (statusCode) {
            case 400:
                title = 'リクエストエラー';
                message = '送信されたデータに問題があります。入力内容を確認してください。';
                break;
            case 401:
                title = '認証エラー';
                message = 'ログインが必要です。アカウントタブでログインしてください。';
                break;
            case 403:
                title = 'アクセス拒否';
                message = 'この操作を実行する権限がありません。';
                break;
            case 404:
                title = 'リソースが見つかりません';
                message = '要求されたデータが見つかりません。';
                break;
            case 429:
                title = 'レート制限';
                message = 'リクエストが多すぎます。しばらく待ってから再試行してください。';
                break;
            case 500:
                title = 'サーバーエラー';
                message = 'サーバーでエラーが発生しました。しばらく待ってから再試行してください。';
                break;
            case 503:
                title = 'サービス利用不可';
                message = 'サービスが一時的に利用できません。しばらく待ってから再試行してください。';
                break;
            default:
                title = '通信エラー';
                message = `予期しないエラーが発生しました (${statusCode})。`;
        }
        
        this.showErrorMessage(title, message, new Error(`${context}: ${statusCode}`));
    }

    handleNetworkError(error, context = 'ネットワーク通信') {
        let title, message;
        
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            title = '接続エラー';
            message = 'サーバーに接続できません。ネットワーク接続を確認してください。';
        } else if (error.name === 'AbortError') {
            title = 'タイムアウト';
            message = 'リクエストがタイムアウトしました。再試行してください。';
        } else {
            title = '通信エラー';
            message = 'ネットワーク通信中にエラーが発生しました。';
        }
        
        this.showErrorMessage(title, message, error);
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
        if (modal) {
            modal.style.display = 'none';
        } else {
            console.warn('closeModal: modal element not found');
        }
    }

    // アカウント管理メソッド
    async loadAuthSession() {
        this.authSessionId = localStorage.getItem('auth_session_id');
        if (this.authSessionId) {
            await this.getCurrentUser();
        }
    }

    async getCurrentUser() {
        if (!this.authSessionId) return;
        
        try {
            const response = await fetch(`${this.apiUrl}/api/auth/me?session_id=${this.authSessionId}`);
            if (response.ok) {
                const data = await response.json();
                this.currentUser = data.user;
                this.updateAccountDisplay();
            } else {
                this.authSessionId = null;
                localStorage.removeItem('auth_session_id');
            }
        } catch (error) {
            console.error('ユーザー情報取得エラー:', error);
        }
    }

    updateAccountDisplay() {
        const loginSection = document.getElementById('loginSection');
        const registerSection = document.getElementById('registerSection');
        const userProfile = document.getElementById('userProfile');
        const profileInfo = document.getElementById('profileInfo');

        // 前回のログイン状態を記録
        const wasLoggedIn = this.wasLoggedIn;

        if (this.currentUser) {
            // ログイン済み
            loginSection.style.display = 'none';
            registerSection.style.display = 'none';
            userProfile.style.display = 'block';
            
            const profile = this.currentUser.profile || {};
            profileInfo.innerHTML = `
                <div class="profile-item">
                    <strong>ユーザー名:</strong> ${this.currentUser.username}
                </div>
                <div class="profile-item">
                    <strong>メールアドレス:</strong> ${this.currentUser.email}
                </div>
                <div class="profile-item">
                    <strong>表示名:</strong> ${profile.display_name || '未設定'}
                </div>
                <div class="profile-item">
                    <strong>自己紹介:</strong> ${profile.bio || '未設定'}
                </div>
                <div class="profile-item">
                    <strong>登録日:</strong> ${new Date(this.currentUser.created_at).toLocaleDateString()}
                </div>
            `;
            
            // ユーザーIDを更新
            this.userId = this.getOrCreateUserId();
            // キャラクター作成ボタンを有効化
            this.updateCharacterButtons(true);
            
            // ログイン状態が変更された場合のみキャラクター一覧を再読み込み
            if (!wasLoggedIn) {
                this.loadCharacters();
            }
            // ログイン状態を更新
            this.wasLoggedIn = true;
        } else {
            // 未ログイン
            loginSection.style.display = 'block';
            registerSection.style.display = 'none';
            userProfile.style.display = 'none';
            
            // ユーザーIDを更新
            this.userId = this.getOrCreateUserId();
            // キャラクター作成ボタンを無効化
            this.updateCharacterButtons(false);
            
            // ログイン状態が変更された場合のみキャラクター一覧を再読み込み
            if (wasLoggedIn) {
                this.loadCharacters();
            }
            // ログイン状態を更新
            this.wasLoggedIn = false;
        }
    }

    updateCharacterButtons(isLoggedIn) {
        const createCharacterBtn = document.getElementById('createCharacterBtn');
        const characterSelect = document.getElementById('characterSelect');
        
        if (createCharacterBtn) {
            if (isLoggedIn) {
                createCharacterBtn.disabled = false;
                createCharacterBtn.textContent = 'キャラクター作成';
                createCharacterBtn.style.opacity = '1';
                createCharacterBtn.style.cursor = 'pointer';
            } else {
                createCharacterBtn.disabled = true;
                createCharacterBtn.textContent = 'ログインが必要です';
                createCharacterBtn.style.opacity = '0.5';
                createCharacterBtn.style.cursor = 'not-allowed';
            }
        }
        
        if (characterSelect) {
            if (isLoggedIn) {
                characterSelect.disabled = false;
                characterSelect.style.opacity = '1';
            } else {
                characterSelect.disabled = true;
                characterSelect.style.opacity = '0.5';
                // 選択肢をクリア
                characterSelect.innerHTML = '<option value="default">デフォルト（ログインが必要）</option>';
            }
        }
    }

    showLoginForm() {
        document.getElementById('loginSection').style.display = 'block';
        document.getElementById('registerSection').style.display = 'none';
    }

    showRegisterForm() {
        document.getElementById('loginSection').style.display = 'none';
        document.getElementById('registerSection').style.display = 'block';
    }

    async login() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        
        console.log('ログイン試行:', { username, password: '***' });

        if (!username || !password) {
            alert('ユーザー名とパスワードを入力してください');
            return;
        }

        try {
            console.log('API URL:', `${this.apiUrl}/api/auth/login`);
            const response = await fetch(`${this.apiUrl}/api/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username_or_email: username,
                    password: password
                })
            });

            console.log('レスポンス状態:', response.status);
            const data = await response.json();
            console.log('レスポンスデータ:', data);

               if (response.ok) {
                   this.authSessionId = data.session_id;
                   this.currentUser = data.user;
                   localStorage.setItem('auth_session_id', this.authSessionId);
                   // ユーザーIDを更新
                   this.userId = this.getOrCreateUserId();
                   this.updateAccountDisplay();
                   alert(data.message);
                   // フォームをクリア
                   document.getElementById('loginUsername').value = '';
                   document.getElementById('loginPassword').value = '';
               } else {
                console.error('ログインエラー:', data);
                alert(data.detail || 'ログインに失敗しました');
            }
        } catch (error) {
            console.error('ログインエラー:', error);
            alert('ログインに失敗しました');
        }
    }

    async register() {
        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        const passwordConfirm = document.getElementById('registerPasswordConfirm').value;

        if (!username || !email || !password || !passwordConfirm) {
            alert('すべての項目を入力してください');
            return;
        }

        if (password !== passwordConfirm) {
            alert('パスワードが一致しません');
            return;
        }

        if (password.length < 6) {
            alert('パスワードは6文字以上で入力してください');
            return;
        }

        try {
            const response = await fetch(`${this.apiUrl}/api/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: username,
                    email: email,
                    password: password
                })
            });

            const data = await response.json();

            if (response.ok) {
                alert(data.message);
                this.showLoginForm();
                // フォームをクリア
                document.getElementById('registerUsername').value = '';
                document.getElementById('registerEmail').value = '';
                document.getElementById('registerPassword').value = '';
                document.getElementById('registerPasswordConfirm').value = '';
            } else {
                alert(data.detail || '登録に失敗しました');
            }
        } catch (error) {
            console.error('登録エラー:', error);
            alert('登録に失敗しました');
        }
    }

    async logout() {
        if (!this.authSessionId) return;

        try {
            await fetch(`${this.apiUrl}/api/auth/logout?session_id=${this.authSessionId}`, {
                method: 'POST'
            });
        } catch (error) {
            console.error('ログアウトエラー:', error);
        }

           this.authSessionId = null;
           this.currentUser = null;
           localStorage.removeItem('auth_session_id');
           // ユーザーIDを更新
           this.userId = this.getOrCreateUserId();
           this.updateAccountDisplay();
           alert('ログアウトしました');
    }

    showProfileModal() {
        if (!this.currentUser) return;

        const profile = this.currentUser.profile || {};
        document.getElementById('editDisplayName').value = profile.display_name || '';
        document.getElementById('editBio').value = profile.bio || '';
        document.getElementById('editAvatar').value = profile.avatar || '';
        
        document.getElementById('profileModal').style.display = 'block';
    }

    showPasswordModal() {
        // パスワードフィールドをクリア
        document.getElementById('currentPassword').value = '';
        document.getElementById('newPassword').value = '';
        document.getElementById('confirmNewPassword').value = '';
        
        document.getElementById('passwordModal').style.display = 'block';
    }

    async saveProfile() {
        if (!this.currentUser || !this.authSessionId) return;

        const displayName = document.getElementById('editDisplayName').value;
        const bio = document.getElementById('editBio').value;
        const avatar = document.getElementById('editAvatar').value;

        try {
            const response = await fetch(`${this.apiUrl}/api/auth/profile?session_id=${this.authSessionId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    display_name: displayName,
                    bio: bio,
                    avatar: avatar
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.currentUser.profile = {
                    ...this.currentUser.profile,
                    display_name: displayName,
                    bio: bio,
                    avatar: avatar
                };
                this.updateAccountDisplay();
                this.closeModal(document.getElementById('profileModal'));
                alert(data.message);
            } else {
                alert(data.detail || 'プロフィール更新に失敗しました');
            }
        } catch (error) {
            console.error('プロフィール更新エラー:', error);
            alert('プロフィール更新に失敗しました');
        }
    }

    async changePassword() {
        if (!this.currentUser || !this.authSessionId) return;

        const currentPassword = document.getElementById('currentPassword').value;
        const newPassword = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmNewPassword').value;

        if (!currentPassword || !newPassword || !confirmPassword) {
            alert('すべての項目を入力してください');
            return;
        }

        if (newPassword !== confirmPassword) {
            alert('新しいパスワードが一致しません');
            return;
        }

        if (newPassword.length < 6) {
            alert('新しいパスワードは6文字以上で入力してください');
            return;
        }

        try {
            const response = await fetch(`${this.apiUrl}/api/auth/change-password?session_id=${this.authSessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.closeModal(document.getElementById('passwordModal'));
                alert(data.message);
            } else {
                alert(data.detail || 'パスワード変更に失敗しました');
            }
        } catch (error) {
            console.error('パスワード変更エラー:', error);
            alert('パスワード変更に失敗しました');
        }
    }

    // パスワードリセット機能
    showResetPasswordForm() {
        document.getElementById('loginSection').style.display = 'none';
        document.getElementById('registerSection').style.display = 'none';
        document.getElementById('resetPasswordSection').style.display = 'block';
    }

    backToLoginForm() {
        // 既存のフォームを非表示にする
        document.getElementById('loginSection').style.display = 'block';
        document.getElementById('registerSection').style.display = 'none';
        document.getElementById('resetPasswordSection').style.display = 'none';
        
        // 既存の再登録フォームや成功セクションを削除
        const reRegisterSection = document.getElementById('reRegisterSection');
        if (reRegisterSection) {
            reRegisterSection.remove();
        }
        
        const successSection = document.getElementById('passwordResetSuccessSection');
        if (successSection) {
            successSection.remove();
        }
        
        // ログインフォームをクリア
        document.getElementById('loginUsername').value = '';
        document.getElementById('loginPassword').value = '';
        
        // エラー状態をクリア（もしあれば）
        this.clearLoginErrors();
    }

    clearLoginErrors() {
        // ログインフォームのエラー状態をクリア
        const usernameInput = document.getElementById('loginUsername');
        const passwordInput = document.getElementById('loginPassword');
        
        if (usernameInput) {
            usernameInput.style.borderColor = '';
            usernameInput.classList.remove('error');
        }
        
        if (passwordInput) {
            passwordInput.style.borderColor = '';
            passwordInput.classList.remove('error');
        }
        
        // エラーメッセージを削除
        const existingErrors = document.querySelectorAll('.login-error');
        existingErrors.forEach(error => error.remove());
    }

    async resetPassword() {
        const email = document.getElementById('resetEmail').value;

        if (!email) {
            alert('メールアドレスを入力してください');
            return;
        }

        if (!this.isValidEmail(email)) {
            alert('有効なメールアドレスを入力してください');
            return;
        }

        try {
            const response = await fetch(`${this.apiUrl}/api/auth/reset-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: email
                })
            });

            const data = await response.json();

            if (response.ok) {
                alert('パスワードをリセットしました。新しいパスワードを設定してください。');
                this.showReRegisterForm(email);
            } else {
                alert(data.detail || 'パスワードリセットに失敗しました');
            }
        } catch (error) {
            console.error('パスワードリセットエラー:', error);
            alert('パスワードリセットに失敗しました');
        }
    }

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    showReRegisterForm(email) {
        // パスワードリセット後の再登録フォームを表示
        document.getElementById('loginSection').style.display = 'none';
        document.getElementById('registerSection').style.display = 'none';
        document.getElementById('resetPasswordSection').style.display = 'none';
        
        // 再登録フォームを作成・表示
        this.createReRegisterForm(email);
    }

    createReRegisterForm(email) {
        // 既存の再登録フォームがあれば削除
        const existingForm = document.getElementById('reRegisterSection');
        if (existingForm) {
            existingForm.remove();
        }

        // 再登録フォームを作成
        const reRegisterSection = document.createElement('div');
        reRegisterSection.id = 'reRegisterSection';
        reRegisterSection.className = 're-register-section';
        reRegisterSection.style.display = 'block';
        
        reRegisterSection.innerHTML = `
            <h3>パスワード再設定</h3>
            <div class="re-register-form">
                <div class="form-group">
                    <label for="reRegisterEmail">メールアドレス:</label>
                    <input type="email" id="reRegisterEmail" value="${email}" readonly>
                </div>
                <div class="form-group">
                    <label for="reRegisterPassword">新しいパスワード:</label>
                    <input type="password" id="reRegisterPassword" placeholder="新しいパスワード（6文字以上）">
                </div>
                <div class="form-group">
                    <label for="reRegisterPasswordConfirm">パスワード確認:</label>
                    <input type="password" id="reRegisterPasswordConfirm" placeholder="新しいパスワード確認">
                </div>
                <div class="form-buttons">
                    <button id="reRegisterBtn" class="btn btn-primary">パスワード再設定</button>
                    <button id="backToLoginFromReRegisterBtn" class="btn btn-secondary">ログインに戻る</button>
                </div>
            </div>
        `;

        // アカウント管理セクションに追加
        const accountStatus = document.getElementById('accountStatus');
        accountStatus.appendChild(reRegisterSection);

        // イベントリスナーを追加
        document.getElementById('reRegisterBtn').addEventListener('click', () => this.reRegister());
        document.getElementById('backToLoginFromReRegisterBtn').addEventListener('click', () => this.backToLoginForm());
    }

    async reRegister() {
        const email = document.getElementById('reRegisterEmail').value;
        const newPassword = document.getElementById('reRegisterPassword').value;
        const confirmPassword = document.getElementById('reRegisterPasswordConfirm').value;

        if (!newPassword || !confirmPassword) {
            alert('すべての項目を入力してください');
            return;
        }

        if (newPassword !== confirmPassword) {
            alert('新しいパスワードが一致しません');
            return;
        }

        if (newPassword.length < 6) {
            alert('新しいパスワードは6文字以上で入力してください');
            return;
        }

        try {
            const response = await fetch(`${this.apiUrl}/api/auth/re-register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: email,
                    new_password: newPassword
                })
            });

            const data = await response.json();

            if (response.ok) {
                // パスワード再設定成功
                this.showPasswordResetSuccess(email);
            } else {
                alert(data.detail || 'パスワード再設定に失敗しました');
            }
        } catch (error) {
            console.error('パスワード再設定エラー:', error);
            alert('パスワード再設定に失敗しました');
        }
    }

    showPasswordResetSuccess(email) {
        // 既存のフォームを非表示にする
        document.getElementById('loginSection').style.display = 'none';
        document.getElementById('registerSection').style.display = 'none';
        document.getElementById('resetPasswordSection').style.display = 'none';
        
        // 既存の再登録フォームを削除
        const existingForm = document.getElementById('reRegisterSection');
        if (existingForm) {
            existingForm.remove();
        }

        // 成功メッセージセクションを作成
        const successSection = document.createElement('div');
        successSection.id = 'passwordResetSuccessSection';
        successSection.className = 'password-reset-success-section';
        successSection.style.display = 'block';
        
        successSection.innerHTML = `
            <div class="success-message">
                <div class="success-icon">✅</div>
                <h3>パスワード再設定完了</h3>
                <p class="success-text">パスワードが正常に再設定されました。</p>
                <p class="email-info">メールアドレス: <strong>${email}</strong></p>
                <div class="success-actions">
                    <button id="loginWithNewPasswordBtn" class="btn btn-primary">新しいパスワードでログイン</button>
                    <button id="backToHomeBtn" class="btn btn-secondary">ホームに戻る</button>
                </div>
            </div>
        `;

        // アカウント管理セクションに追加
        const accountStatus = document.getElementById('accountStatus');
        accountStatus.appendChild(successSection);

        // イベントリスナーを追加
        document.getElementById('loginWithNewPasswordBtn').addEventListener('click', () => {
            this.showLoginFormWithEmail(email);
        });
        document.getElementById('backToHomeBtn').addEventListener('click', () => {
            this.backToLoginForm();
        });
    }

    showLoginFormWithEmail(email) {
        // 成功セクションを削除
        const successSection = document.getElementById('passwordResetSuccessSection');
        if (successSection) {
            successSection.remove();
        }

        // ログインフォームを表示
        document.getElementById('loginSection').style.display = 'block';
        document.getElementById('registerSection').style.display = 'none';
        document.getElementById('resetPasswordSection').style.display = 'none';

        // メールアドレスを自動入力
        document.getElementById('loginUsername').value = email;
        
        // パスワードフィールドにフォーカス
        document.getElementById('loginPassword').focus();

        // 成功メッセージを表示
        this.showSuccessMessage('新しいパスワードでログインしてください。');
    }

    showSuccessMessage(message) {
        // 成功メッセージを一時的に表示
        const successDiv = document.createElement('div');
        successDiv.className = 'success-notification';
        successDiv.textContent = message;
        successDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 10000;
            font-weight: 500;
        `;

        document.body.appendChild(successDiv);

        // 3秒後に自動削除
        setTimeout(() => {
            if (successDiv.parentNode) {
                successDiv.parentNode.removeChild(successDiv);
            }
        }, 3000);
    }
}

// アプリケーション初期化
let app; // グローバル変数として定義
document.addEventListener('DOMContentLoaded', () => {
    app = new AITakashiWebClient();
});

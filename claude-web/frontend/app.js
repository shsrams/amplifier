// Simple Alpine.js app for Claude Web - FIXED VERSION
function chatApp() {
    return {
        // Auth state
        token: localStorage.getItem('token'),
        user: null,
        isRegistering: false,
        loginForm: {
            username: '',
            email: '',
            password: ''
        },
        error: '',
        
        // Chat state
        conversations: [],
        currentConversationId: null,
        messages: [],
        currentMessage: '',
        isStreaming: false,
        streamingMessage: '',
        streamingMessages: [],
        currentStreamingIndex: null,
        useStreamingMode: true,
        
        // API base URL - same origin since backend serves frontend
        apiUrl: '',
        
        async init() {
            if (this.token) {
                await this.loadUser();
                await this.loadConversations();
            }
        },
        
        // Auth methods
        async login() {
            try {
                const formData = new FormData();
                formData.append('username', this.loginForm.username);
                formData.append('password', this.loginForm.password);
                
                const response = await fetch(`${this.apiUrl}/token`, {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('Invalid credentials');
                }
                
                const data = await response.json();
                this.token = data.access_token;
                localStorage.setItem('token', this.token);
                
                await this.loadUser();
                await this.loadConversations();
                this.error = '';
            } catch (e) {
                this.error = e.message;
            }
        },
        
        async register() {
            try {
                const response = await fetch(`${this.apiUrl}/register`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: this.loginForm.username,
                        email: this.loginForm.email,
                        password: this.loginForm.password
                    })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Registration failed');
                }
                
                // Auto-login after registration
                await this.login();
            } catch (e) {
                this.error = e.message;
            }
        },
        
        async loadUser() {
            try {
                const response = await fetch(`${this.apiUrl}/me`, {
                    headers: {
                        'Authorization': `Bearer ${this.token}`
                    }
                });
                
                if (!response.ok) {
                    throw new Error('Failed to load user');
                }
                
                this.user = await response.json();
            } catch (e) {
                this.logout();
            }
        },
        
        logout() {
            this.token = null;
            this.user = null;
            localStorage.removeItem('token');
            this.conversations = [];
            this.messages = [];
            this.currentConversationId = null;
        },
        
        // Conversation methods
        async loadConversations() {
            try {
                const response = await fetch(`${this.apiUrl}/conversations`, {
                    headers: {
                        'Authorization': `Bearer ${this.token}`
                    }
                });
                
                if (!response.ok) {
                    throw new Error('Failed to load conversations');
                }
                
                this.conversations = await response.json();
            } catch (e) {
                console.error('Error loading conversations:', e);
            }
        },
        
        async newConversation() {
            try {
                const response = await fetch(`${this.apiUrl}/conversations`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({})
                });
                
                if (!response.ok) {
                    throw new Error('Failed to create conversation');
                }
                
                const conv = await response.json();
                await this.loadConversations();
                this.selectConversation(conv.id);
            } catch (e) {
                console.error('Error creating conversation:', e);
            }
        },
        
        async selectConversation(conversationId) {
            this.currentConversationId = conversationId;
            await this.loadMessages(conversationId);
        },
        
        async loadMessages(conversationId) {
            try {
                const response = await fetch(`${this.apiUrl}/conversations/${conversationId}/messages`, {
                    headers: {
                        'Authorization': `Bearer ${this.token}`
                    }
                });
                
                if (!response.ok) {
                    throw new Error('Failed to load messages');
                }
                
                this.messages = await response.json();
                this.scrollToBottom();
            } catch (e) {
                console.error('Error loading messages:', e);
            }
        },
        
        // Chat methods
        async sendMessage() {
            if (!this.currentMessage.trim() || this.isStreaming) {
                return;
            }
            
            const message = this.currentMessage;
            this.currentMessage = '';
            
            if (this.useStreamingMode) {
                await this.sendStreamingMessage(message);
            } else {
                await this.sendNonStreamingMessage(message);
            }
        },
        
        async sendStreamingMessage(message) {
            this.isStreaming = true;
            this.streamingMessage = '';
            this.streamingMessages = [];
            this.currentStreamingIndex = null;
            
            // Add user message to UI immediately
            this.messages.push({
                id: Date.now(),
                role: 'user',
                content: message,
                created_at: new Date().toISOString()
            });
            
            try {
                const response = await fetch(`${this.apiUrl}/chat/stream`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message,
                        conversation_id: this.currentConversationId
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Failed to send message');
                }
                
                // Handle SSE stream
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                
                                if (data.id) {
                                    // Update conversation ID if new
                                    if (!this.currentConversationId) {
                                        this.currentConversationId = data.id;
                                    }
                                } else if (data.content) {
                                    // EACH message event should be its own bubble
                                    // Create a new bubble for this message event
                                    const messageContent = data.content.trim();
                                    
                                    if (messageContent) {
                                        // Add as a new streaming message bubble
                                        this.streamingMessages.push(messageContent);
                                        this.currentStreamingIndex = this.streamingMessages.length - 1;
                                        
                                        // Update for compatibility
                                        this.streamingMessage = messageContent;
                                        
                                        // Force Alpine to update
                                        this.streamingMessages = [...this.streamingMessages];
                                        
                                        console.log(`[NEW MESSAGE BUBBLE] Bubble ${this.streamingMessages.length}: ${messageContent.substring(0, 50)}...`);
                                        
                                        this.scrollToBottom();
                                    }
                                }
                            } catch (e) {
                                // Ignore JSON parse errors
                            }
                        }
                    }
                }
                
                // Convert all streaming messages to permanent messages
                // Each streaming message becomes its own bubble
                if (this.streamingMessages.length > 0) {
                    this.streamingMessages.forEach((content, index) => {
                        if (content && content.trim()) {
                            this.messages.push({
                                id: Date.now() + index + 1,
                                role: 'assistant',
                                content: content.trim(),
                                created_at: new Date().toISOString()
                            });
                        }
                    });
                }
                
                // Refresh conversations to update title and count
                await this.loadConversations();
                
            } catch (e) {
                console.error('Error:', e);
                this.messages.push({
                    id: Date.now() + 1,
                    role: 'assistant',
                    content: 'Sorry, I encountered an error. Please try again.',
                    created_at: new Date().toISOString()
                });
            } finally {
                this.isStreaming = false;
                this.streamingMessage = '';
                this.streamingMessages = [];
                this.currentStreamingIndex = null;
                this.scrollToBottom();
            }
        },
        
        findSplitPoint(text) {
            // Find the best split point in the text
            // Returns the index where to split, or -1 if no split needed
            
            // Don't split if text is too short
            if (text.length < 50) return -1;
            
            // Don't split inside code blocks
            const codeBlocks = (text.match(/```/g) || []).length;
            if (codeBlocks % 2 !== 0) return -1;
            
            // First priority: Look for markdown headers (##, ###)
            const headerPattern = /\n#{2,3}\s+/g;
            const headerMatches = [...text.matchAll(headerPattern)];
            if (headerMatches.length > 0) {
                // Find a header that's not too close to the start
                for (const match of headerMatches) {
                    if (match.index > 50) {
                        console.log(`[SPLIT] Found header at position ${match.index}`);
                        return match.index; // Split before the header
                    }
                }
            }
            
            // Second priority: Look for numbered lists after some content
            const numberedListPattern = /\n\d+\.\s+\*\*/g;
            const listMatches = [...text.matchAll(numberedListPattern)];
            if (listMatches.length > 0) {
                for (const match of listMatches) {
                    if (match.index > 100) {
                        console.log(`[SPLIT] Found numbered list at position ${match.index}`);
                        return match.index;
                    }
                }
            }
            
            // Third priority: Look for sentence endings followed by action words
            const patterns = [
                /\.Let me/g,
                /\.Now let me/g,
                /\.Now I/g,
                /\.I'll/g,
                /\.I will/g,
                /\.I've/g,
                /\.Looking at/g,
                /\.Based on/g,
                /:Let me/g,
                /:Now let me/g,
            ];
            
            for (const pattern of patterns) {
                const matches = [...text.matchAll(pattern)];
                if (matches.length > 0) {
                    const lastMatch = matches[matches.length - 1];
                    if (lastMatch.index > 30) {
                        console.log(`[SPLIT] Found action pattern at position ${lastMatch.index}`);
                        return lastMatch.index + 1;
                    }
                }
            }
            
            // Fourth priority: Split on major markdown sections
            const sectionPattern = /\n### /g;
            const sectionMatches = [...text.matchAll(sectionPattern)];
            for (const match of sectionMatches) {
                if (match.index > 100) {
                    console.log(`[SPLIT] Found section at position ${match.index}`);
                    return match.index;
                }
            }
            
            // Last resort: Look for double newlines (paragraph breaks)
            const doubleNewline = text.lastIndexOf('\n\n');
            if (doubleNewline > 200 && doubleNewline < text.length - 50) {
                console.log(`[SPLIT] Found paragraph break at position ${doubleNewline}`);
                return doubleNewline + 2;
            }
            
            return -1; // No good split point found
        },
        
        async sendNonStreamingMessage(message) {
            this.isStreaming = true;
            
            // Add user message to UI
            this.messages.push({
                id: Date.now(),
                role: 'user',
                content: message,
                created_at: new Date().toISOString()
            });
            
            try {
                const response = await fetch(`${this.apiUrl}/chat`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message,
                        conversation_id: this.currentConversationId
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Failed to send message');
                }
                
                const data = await response.json();
                
                if (!this.currentConversationId && data.conversation_id) {
                    this.currentConversationId = data.conversation_id;
                }
                
                // Split the response into parts
                const parts = this.splitResponseIntoParts(data.response);
                
                // Add each part as a separate message
                parts.forEach((part, index) => {
                    this.messages.push({
                        id: Date.now() + index + 1,
                        role: 'assistant',
                        content: part,
                        created_at: new Date().toISOString()
                    });
                });
                
                // Refresh conversations
                await this.loadConversations();
                
            } catch (e) {
                console.error('Error:', e);
                this.messages.push({
                    id: Date.now() + 1,
                    role: 'assistant',
                    content: 'Sorry, I encountered an error. Please try again.',
                    created_at: new Date().toISOString()
                });
            } finally {
                this.isStreaming = false;
                this.scrollToBottom();
            }
        },
        
        splitResponseIntoParts(response) {
            // Split response into logical parts
            const parts = [];
            let remaining = response;
            let iterations = 0;
            const maxIterations = 20; // Prevent infinite loops
            
            while (remaining && iterations < maxIterations) {
                iterations++;
                const splitPoint = this.findSplitPoint(remaining);
                
                if (splitPoint > 0) {
                    const part = remaining.substring(0, splitPoint).trim();
                    if (part) {
                        parts.push(part);
                        console.log(`[SPLIT] Part ${parts.length}: ${part.substring(0, 50)}...`);
                    }
                    remaining = remaining.substring(splitPoint).trim();
                } else {
                    // No more split points found
                    if (remaining.trim()) {
                        parts.push(remaining.trim());
                        console.log(`[SPLIT] Final part ${parts.length}: ${remaining.substring(0, 50)}...`);
                    }
                    break;
                }
            }
            
            // If no splits were made and response is long, try to split on headers
            if (parts.length === 0 && response.length > 500) {
                // Force split on any markdown headers
                const forcedParts = response.split(/(?=\n#{2,3}\s+)/);
                forcedParts.forEach(part => {
                    if (part.trim()) {
                        parts.push(part.trim());
                    }
                });
                console.log(`[SPLIT] Forced split into ${parts.length} parts`);
            }
            
            return parts.filter(p => p.length > 0);
        },
        
        // Utility methods
        formatMessage(content) {
            // Simple markdown-like formatting
            return content
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/\n/g, '<br>')
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        },
        
        scrollToBottom() {
            setTimeout(() => {
                const container = document.getElementById('messagesContainer');
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
            }, 50);
        }
    };
}
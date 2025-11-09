// Chatbot Functionality
class Chatbot {
    constructor() {
        this.isOpen = false;
        this.isTyping = false;
        this.messages = [];
        
        if (this.initializeElements()) {
            this.bindEvents();
            this.addWelcomeMessage();
        }
    }
    
    initializeElements() {
        this.container = document.getElementById('chatbotContainer');
        this.toggle = document.getElementById('chatbotToggle');
        this.window = document.getElementById('chatbotWindow');
        this.closeBtn = document.getElementById('chatbotClose');
        this.messagesArea = document.getElementById('chatbotMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        
        // Check if all elements are found
        if (!this.container || !this.toggle || !this.window) {
            console.error('Chatbot: Required elements not found');
            return false;
        }
        return true;
    }
    
    bindEvents() {
        // Toggle chatbot with null checks
        if (this.toggle) {
            this.toggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleChatbot();
            });
        }
        
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.closeChatbot();
            });
        }
        
        // Send message events
        if (this.sendButton) {
            this.sendButton.addEventListener('click', () => this.sendMessage());
        }
        
        if (this.messageInput) {
            this.messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            
            // Auto-resize textarea
            this.messageInput.addEventListener('input', () => this.adjustTextareaHeight());
        }
        
        // Close on outside click
        document.addEventListener('click', (e) => {
            if (this.isOpen && this.container && !this.container.contains(e.target)) {
                this.closeChatbot();
            }
        });
    }
    
    toggleChatbot() {
        console.log('Toggle chatbot called, isOpen:', this.isOpen);
        if (this.isOpen) {
            this.closeChatbot();
        } else {
            this.openChatbot();
        }
    }
    
    openChatbot() {
        console.log('Opening chatbot');
        this.isOpen = true;
        if (this.window) {
            this.window.classList.add('show');
        }
        if (this.toggle) {
            this.toggle.innerHTML = '<i class="bi bi-x"></i>';
        }
        if (this.messageInput) {
            setTimeout(() => this.messageInput.focus(), 300);
        }
        this.scrollToBottom();
    }
    
    closeChatbot() {
        console.log('Closing chatbot');
        this.isOpen = false;
        if (this.window) {
            this.window.classList.remove('show');
        }
        if (this.toggle) {
            this.toggle.innerHTML = '<i class="bi bi-chat-dots"></i>';
        }
    }
    
    adjustTextareaHeight() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 100) + 'px';
    }
    
    sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;
        
        // Add user message
        this.addMessage('user', message);
        this.messageInput.value = '';
        this.adjustTextareaHeight();
        
        // Show typing indicator
        this.showTypingIndicator();
        
        // Send message to backend
        this.sendMessageToBackend(message);
    }
    
    addMessage(type, content, timestamp = null) {
        const messageTime = timestamp || new Date();
        const messageId = 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        const messageElement = this.createMessageElement(type, content, messageTime, messageId);
        
        // Insert before typing indicator
        this.messagesArea.insertBefore(messageElement, this.typingIndicator);
        
        this.messages.push({
            id: messageId,
            type,
            content,
            timestamp: messageTime
        });
        
        this.scrollToBottom();
    }
    
    createMessageElement(type, content, timestamp, id) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.id = id;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = type === 'bot' ? '<i class="bi bi-robot"></i>' : '<i class="bi bi-person"></i>';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.textContent = content;
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        return messageDiv;
    }
    
    showTypingIndicator() {
        this.isTyping = true;
        this.typingIndicator.classList.add('show');
        this.sendButton.disabled = true;
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        this.isTyping = false;
        this.typingIndicator.classList.remove('show');
        this.sendButton.disabled = false;
    }
    
    async sendMessageToBackend(userMessage) {
        try {
            const response = await fetch('/resident/chatbot/response/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    message: userMessage
                })
            });
            
            const data = await response.json();
            
            this.hideTypingIndicator();
            
            if (data.success) {
                this.addMessage('bot', data.response);
            } else {
                this.addMessage('bot', 'Sorry, I encountered an error. Please try again.');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTypingIndicator();
            this.addMessage('bot', 'Sorry, I\'m having trouble connecting. Please try again later.');
        }
    }
    
    getCSRFToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            return csrfToken.value;
        }
        
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }
    
    addBotResponse(userMessage) {
        // Fallback method - now only used if backend fails
        const responses = this.generateBotResponse(userMessage);
        const randomResponse = responses[Math.floor(Math.random() * responses.length)];
        this.addMessage('bot', randomResponse);
    }
    
    generateBotResponse(userMessage) {
        const lowerMessage = userMessage.toLowerCase();
        
        // Barangay-specific responses
        if (lowerMessage.includes('complaint') || lowerMessage.includes('report')) {
            return [
                "I can help you file a complaint. You can use the 'File Complaint' option in the sidebar to submit your concern.",
                "To file a complaint, please go to the File Complaint section where you can provide details about your concern.",
                "I understand you want to report something. The complaint system is available in the main navigation menu."
            ];
        }
        
        if (lowerMessage.includes('assistance') || lowerMessage.includes('help') || lowerMessage.includes('support')) {
            return [
                "You can request assistance through the 'Request Assistance' feature. What type of assistance do you need?",
                "I'm here to help! You can submit an assistance request using the form in the assistance section.",
                "For assistance requests, please use the Request Assistance option in the sidebar to get the help you need."
            ];
        }
        
        if (lowerMessage.includes('status') || lowerMessage.includes('track')) {
            return [
                "You can check the status of your complaints and assistance requests in the 'My Complaints' and 'My Assistance' sections.",
                "To track your submissions, visit the respective sections in the sidebar for real-time updates.",
                "Your complaint and assistance request statuses are available in their dedicated sections in the main menu."
            ];
        }
        
        if (lowerMessage.includes('profile') || lowerMessage.includes('account')) {
            return [
                "You can update your profile information in the Profile section of your account.",
                "To modify your account details, please visit the Profile page accessible from the sidebar.",
                "Your account settings and profile information can be managed in the Profile section."
            ];
        }
        
        if (lowerMessage.includes('notification')) {
            return [
                "You can view all your notifications in the Notifications section of your account.",
                "Check the Notifications page to see updates about your complaints and assistance requests.",
                "All system notifications and updates are available in the Notifications section."
            ];
        }
        
        if (lowerMessage.includes('hello') || lowerMessage.includes('hi') || lowerMessage.includes('hey')) {
            return [
                "Hello! I'm here to help you navigate the Barangay CMS. What can I assist you with today?",
                "Hi there! How can I help you with your barangay services today?",
                "Hello! Welcome to the Barangay CMS assistant. What would you like to know?"
            ];
        }
        
        if (lowerMessage.includes('thank') || lowerMessage.includes('thanks')) {
            return [
                "You're welcome! Feel free to ask if you need any other assistance.",
                "Happy to help! Let me know if you have any other questions.",
                "Glad I could assist you! Is there anything else you'd like to know?"
            ];
        }
        
        // Default responses
        return [
            "I'm here to help you with barangay services. You can file complaints, request assistance, check your submissions, and manage your profile.",
            "I can assist you with navigating the system. What specific information are you looking for?",
            "Feel free to ask me about filing complaints, requesting assistance, checking status updates, or managing your account.",
            "I'm your barangay assistant! I can help you understand how to use the different features of this system."
        ];
    }
    
    addWelcomeMessage() {
        setTimeout(() => {
            this.addMessage('bot', "Hello! I'm your Barangay CMS assistant. I can help you navigate the system, file complaints, request assistance, and answer questions about barangay services. How can I help you today?");
        }, 500);
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.messagesArea.scrollTop = this.messagesArea.scrollHeight;
        }, 100);
    }
    
    clearChat() {
        this.messages = [];
        this.messagesArea.innerHTML = '';
        
        // Re-add typing indicator
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'typing-indicator';
        typingIndicator.id = 'typingIndicator';
        typingIndicator.innerHTML = `
            <div class="message-avatar">
                <i class="bi bi-robot"></i>
            </div>
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        this.messagesArea.appendChild(typingIndicator);
        this.typingIndicator = typingIndicator;
        
        this.addWelcomeMessage();
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit to ensure all styles are loaded
    setTimeout(() => {
        const chatbot = new Chatbot();
        
        // Make chatbot globally accessible for potential external integrations
        window.barangayChatbot = chatbot;
        
        // Additional debug logging
        console.log('Chatbot initialized:', chatbot);
    }, 100);
});
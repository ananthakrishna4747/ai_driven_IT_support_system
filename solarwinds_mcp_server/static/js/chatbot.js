// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const clearButton = document.getElementById('clearButton');
    const docsButton = document.getElementById('docsButton');
    const typingIndicator = document.getElementById('typingIndicator');
    
    // Check server connection status
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            if (data.status !== 'connected') {
                appendBotMessage("I'm having trouble connecting to the server. Please try again later or contact support.");
            }
        })
        .catch(error => {
            console.error('Error checking server status:', error);
            appendBotMessage("I'm having trouble connecting to the server. Please try again later or contact support.");
        });
    
    // Send message function
    function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        appendUserMessage(message);
        userInput.value = '';
        
        // Show typing indicator
        typingIndicator.classList.add('active');
        
        // Send message to API
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message }),
        })
        .then(response => response.json())
        .then(data => {
            // Hide typing indicator
            typingIndicator.classList.remove('active');
            
            if (data.error) {
                appendBotMessage("I'm sorry, I encountered an error: " + data.error);
            } else {
                // Process and add bot response
                appendBotMessage(data.response);
            }
            
            // Scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;
        })
        .catch(error => {
            // Hide typing indicator
            typingIndicator.classList.remove('active');
            
            console.error('Error sending message:', error);
            appendBotMessage("I'm sorry, there was an error communicating with the server.");
            
            // Scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }
    
    // Append user message to chat
    function appendUserMessage(message) {
        const messageTime = getCurrentTime();
        
        const messageHTML = `
            <div class="message user-message">
                <div class="message-content">
                    <p>${escapeHTML(message)}</p>
                </div>
                <div class="message-avatar">
                    <div>U</div>
                </div>
                <div class="message-time">${messageTime}</div>
            </div>
        `;
        
        chatMessages.insertAdjacentHTML('beforeend', messageHTML);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Append bot message to chat
    function appendBotMessage(message) {
        const messageTime = getCurrentTime();
        
        // Process markdown-like formatting
        const formattedMessage = formatMessage(message);
        
        const messageHTML = `
            <div class="message bot-message">
                <div class="message-avatar">
                    <img src="/static/img/chatbot-icon.png" alt="Bot">
                </div>
                <div class="message-content">
                    <p>${formattedMessage}</p>
                </div>
                <div class="message-time">${messageTime}</div>
            </div>
        `;
        
        chatMessages.insertAdjacentHTML('beforeend', messageHTML);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Format message with enhanced markdown-like styling
    function formatMessage(message) {
        // Escape HTML to prevent XSS
        let escaped = escapeHTML(message);
        
        // Bold formatting
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Italic formatting
        escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Code formatting
        escaped = escaped.replace(/`(.*?)`/g, '<code>$1</code>');
        
        // Line breaks
        escaped = escaped.replace(/\n/g, '<br>');
        
        // Handle the formatted response pattern (Response X:)
        escaped = escaped.replace(/\*\*Response (\d+):\*\*/g, '<h3 class="response-header">Response $1:</h3>');
        
        return escaped;
    }
    
    // Escape HTML to prevent XSS
    function escapeHTML(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Get current time for message timestamp
    function getCurrentTime() {
        const now = new Date();
        let hours = now.getHours();
        let minutes = now.getMinutes();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        
        hours = hours % 12;
        hours = hours ? hours : 12; // Convert 0 to 12
        minutes = minutes < 10 ? '0' + minutes : minutes;
        
        return `${hours}:${minutes} ${ampm}`;
    }
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    clearButton.addEventListener('click', function() {
        // Clear all messages except the first bot greeting
        const messages = chatMessages.querySelectorAll('.message');
        for (let i = 1; i < messages.length; i++) {
            messages[i].remove();
        }
    });
    
    docsButton.addEventListener('click', function() {
        window.open('/docs', '_blank');
    });
});
class AzureMapsAgent {
    constructor() {
        this.chatId = null;
    }

    async startChat(file, description = '') {
        const fileContent = await this.readFile(file);
        const response = await fetch('/api/start-chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                fileContent,
                fileName: file.name,
                userInput: description
            })
        });

        const result = await response.json();
        this.chatId = result.chatId;
        return result.response;
    }

    async chat(userInput) {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chatId: this.chatId,
                userInput
            })
        });

        return await response.json();
    }

    async readFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = async (e) => {
                try {
                    resolve(e.target.result);
                } catch (error) {
                    reject(error);
                }
            };
            reader.readAsText(file);
        });
    }

    reset() {
        this.chatId = null;
    }
}

// Initialize agent and add event listeners when document is loaded
document.addEventListener('DOMContentLoaded', async () => {
    const agent = new AzureMapsAgent();

    const fileInput = document.getElementById('fileInput');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const newChatButton = document.getElementById('newChatButton');
    const chatHistory = document.getElementById('chatHistory');
    const mapContainer = document.getElementById('mapContainer');
    let currentMapFrame = null;

    function appendLoadingIndicator() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message loading-message';
        loadingDiv.innerHTML = '<div class="loading-dots"><span>.</span><span>.</span><span>.</span></div>';
        chatHistory.appendChild(loadingDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return loadingDiv;
    }

    function removeLoadingIndicator(loadingDiv) {
        if (loadingDiv && loadingDiv.parentNode) {
            loadingDiv.parentNode.removeChild(loadingDiv);
        }
    }

    fileInput.addEventListener('change', async (e) => {
        if (e.target.files[0]) {
            const description = document.getElementById('fileDescription').value;
            const loadingDiv = appendLoadingIndicator();
            try {
                const response = await agent.startChat(e.target.files[0], description);
                document.getElementById('fileStatus').textContent = 'File loaded successfully!';
                userInput.disabled = false;
                sendButton.disabled = false;
                
                // Remove loading indicator and handle response
                removeLoadingIndicator(loadingDiv);
                appendMessage('agent', response.text);
                if (response.mapHtml) {
                    updateMap(response.mapHtml);
                }
            } catch (error) {
                removeLoadingIndicator(loadingDiv);
                document.getElementById('fileStatus').textContent = 'Error loading file: ' + error.message;
            }
        }
    });

    const handleUserInput = async () => {
        const message = userInput.value.trim();
        if (!message) return;

        // Add user message to chat
        appendMessage('user', message);
        userInput.value = '';

        // Add loading indicator
        const loadingDiv = appendLoadingIndicator();

        try {
            // Get agent response
            const response = await agent.chat(message);
            removeLoadingIndicator(loadingDiv);
            appendMessage('agent', response.text);

            // Handle map if present
            if (response.mapHtml) {
                updateMap(response.mapHtml);
            }
        } catch (error) {
            removeLoadingIndicator(loadingDiv);
            appendMessage('agent', 'Error: Failed to get response');
        }
    };

    sendButton.addEventListener('click', handleUserInput);
    
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleUserInput();
        }
    });

    newChatButton.addEventListener('click', () => {
        agent.reset();
        chatHistory.innerHTML = '';
        userInput.disabled = true;
        sendButton.disabled = true;
        fileInput.value = '';
        document.getElementById('fileDescription').value = '';
        document.getElementById('fileStatus').textContent = '';
        if (currentMapFrame) {
            mapContainer.removeChild(currentMapFrame);
            currentMapFrame = null;
        }
        mapContainer.innerHTML = '<p class="initial-message">Generated maps will appear here</p>';
    });

    function appendMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        messageDiv.textContent = content;
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function updateMap(mapHtml) {
        const blob = new Blob([mapHtml], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        
        if (currentMapFrame) {
            mapContainer.removeChild(currentMapFrame);
        }
        
        currentMapFrame = document.createElement('iframe');
        currentMapFrame.src = url;
        currentMapFrame.style.width = '100%';
        currentMapFrame.style.height = '100%';
        mapContainer.appendChild(currentMapFrame);
    }
});

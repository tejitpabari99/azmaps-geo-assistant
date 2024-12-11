class AzureMapsAgent {
    constructor() {
        this.isFirstMessage = true;
    }

    async chat(userInput, fileContent = null, fileName = null, useAiSearch = false) {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                userInput,
                fileContent: this.isFirstMessage ? fileContent : undefined,
                fileName: this.isFirstMessage ? fileName : undefined,
                useAiSearch: this.isFirstMessage ? useAiSearch : undefined
            })
        });

        if (this.isFirstMessage) {
            this.isFirstMessage = false;
        }

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
        this.isFirstMessage = true;
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
    const aiSearchCheckbox = document.getElementById('aiSearchIndex');
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

    // Enable user input when file is selected
    fileInput.addEventListener('change', (e) => {
        if (e.target.files[0]) {
            userInput.disabled = false;
            sendButton.disabled = false;
            document.getElementById('fileStatus').textContent = 'File ready to be processed';
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
            let response;
            if (agent.isFirstMessage) {
                // For first message, include file content and AI search preference
                const file = fileInput.files[0];
                if (!file) {
                    throw new Error('Please select a file first');
                }
                const fileContent = await agent.readFile(file);
                response = await agent.chat(message, fileContent, file.name, aiSearchCheckbox.checked);

                // Disable file input and AI search checkbox after first message
                fileInput.disabled = true;
                aiSearchCheckbox.disabled = true;
            } else {
                response = await agent.chat(message);
            }

            removeLoadingIndicator(loadingDiv);
            
            // Handle main response text
            if (response.text) {
                appendMessage('agent', response.text);
            }

            // Handle additional text if present
            if (response.additionalText) {
                appendMessage('agent', response.additionalText);
            }

            // Handle follow-up if present
            if (response.followup) {
                appendMessage('agent', response.followup, true);
            }

            // Handle map if present
            if (response.mapHtml) {
                updateMap(response.mapHtml);
            }
        } catch (error) {
            removeLoadingIndicator(loadingDiv);
            appendMessage('agent', 'Error: ' + error.message);
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
        fileInput.disabled = false;
        aiSearchCheckbox.checked = true;
        aiSearchCheckbox.disabled = false;
        document.getElementById('fileDescription').value = '';
        document.getElementById('fileStatus').textContent = '';
        if (currentMapFrame) {
            mapContainer.removeChild(currentMapFrame);
            currentMapFrame = null;
        }
        mapContainer.innerHTML = '<p class="initial-message">Generated maps will appear here</p>';
    });

    function appendMessage(role, content, isFollowup = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        if (isFollowup && content.includes('\n')) {
            // If it's a followup message with line breaks, replace them with <br/> tags
            messageDiv.innerHTML = content.split('\n').join('<br/>');
        } else {
            messageDiv.textContent = content;
        }
        
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

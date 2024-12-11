class AzureMapsAgent {
    constructor() {
        this.isFirstMessage = true;
    }

    async chat(userInput, fileContents = null, fileNames = null, useAiSearch = false) {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                userInput,
                fileContents: this.isFirstMessage ? fileContents : undefined,
                fileNames: this.isFirstMessage ? fileNames : undefined,
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

    const fileInputs = [
        document.getElementById('file1'),
        document.getElementById('file2'),
        document.getElementById('file3')
    ];
    const fileList = document.getElementById('fileList');
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

    function updateFileList() {
        fileList.innerHTML = '';
        const files = fileInputs
            .map(input => input.files[0])
            .filter(file => file !== undefined);
        
        files.forEach((file, index) => {
            const fileDiv = document.createElement('div');
            fileDiv.className = 'file-item';
            fileDiv.textContent = `${index + 1}. ${file.name}`;
            fileList.appendChild(fileDiv);
        });

        // Update file input states
        fileInputs.forEach((input, index) => {
            if (index > 0) {
                input.disabled = !fileInputs[index - 1].files.length;
            }
        });

        // Enable/disable chat input based on whether at least one file is selected
        const hasFiles = files.length > 0;
        userInput.disabled = !hasFiles;
        sendButton.disabled = !hasFiles;
        
        // Update status
        document.getElementById('fileStatus').textContent = hasFiles 
            ? `${files.length} file(s) ready to be processed`
            : '';
    }

    // Add change event listeners to all file inputs
    fileInputs.forEach(input => {
        input.addEventListener('change', updateFileList);
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
                // Get all files that have been selected
                const files = fileInputs
                    .map(input => input.files[0])
                    .filter(file => file !== undefined);

                if (!files.length) {
                    throw new Error('Please select at least one file first');
                }

                // Read all files
                const fileContents = await Promise.all(files.map(file => agent.readFile(file)));
                const fileNames = files.map(file => file.name);

                response = await agent.chat(message, fileContents, fileNames, aiSearchCheckbox.checked);

                // Disable file inputs and AI search checkbox after first message
                fileInputs.forEach(input => input.disabled = true);
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
        fileInputs.forEach((input, index) => {
            input.value = '';
            input.disabled = index > 0; // Only first input enabled initially
        });
        fileList.innerHTML = '';
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

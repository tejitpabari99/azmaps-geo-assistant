from pydantic import BaseModel
from azure.identity import AzureCliCredential, get_bearer_token_provider
from openai import AzureOpenAI
import os, re
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv
load_dotenv()

class ChatMessage(BaseModel):
    userInput: str
    fileContents: Optional[List[str]] = None
    fileNames: Optional[List[str]] = None
    useAiSearch: Optional[bool] = False

class ChatAssistant:
    def __init__(self):
        """Initialize the ChatAssistant with necessary configurations and setup."""
        self._create_directories()
        self._setup_logging()
        self._setup_response_blocks()
        self.client = self._initialize_azure_openai()
        self.current_conversation = None
        self.conversation_id = None  # For storage/logging only
        self.logger.info("Chat Assistant initialized successfully")

    def _setup_logging(self) -> None:
        """Configure logging with appropriate format and file handling."""
        today_date = datetime.now().strftime("%Y%m%d")
        
        logging.basicConfig(
            filename=f"logs/{today_date}.log",
            encoding='utf-8',
            level=logging.DEBUG if os.getenv("DEBUG") == "True" else logging.INFO,
            format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d - %(funcName)s()] - %(message)s'
        )
        self.logger = logging.getLogger("azmaps-geo-assistant")
        self.logger.info("Initialized logging")

    def _setup_response_blocks(self) -> None:
        """Initialize the response blocks dictionary with None values."""
        self.response_blocks = {
            'html': None,
            'followup': None,
            'explanation': None
        }

    def _create_directories(self) -> None:
        """Create necessary directories for storing generated files and logs."""
        directories = ["generated_maps", "chat_histories", "logs"]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def _initialize_azure_openai(self) -> AzureOpenAI:
        """Initialize and return Azure OpenAI client with appropriate credentials."""
        try:
            token_provider = get_bearer_token_provider(
                AzureCliCredential(),
                "https://cognitiveservices.azure.com/.default"
            )
            client = AzureOpenAI(
                api_version=os.getenv("AZURE_OPENAI_VERSION"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                azure_ad_token_provider=token_provider
            )
            self.logger.debug("Successfully initialized Azure OpenAI client")
            return client
        except Exception as e:
            self.logger.error(f"Failed to initialize Azure OpenAI client: {str(e)}")
            raise

    def _sample_data(self, file_content: str) -> str:
        """Sample the first 5 items from different file types."""
        try:
            data = json.loads(file_content)
            
            # Handle GeoJSON
            if isinstance(data, dict) and data.get('type') == 'FeatureCollection':
                if 'features' in data:
                    data['features'] = data['features'][:5]
                return json.dumps(data, indent=2)
            
            # Handle regular JSON array of objects
            elif isinstance(data, list):
                return json.dumps(data[:5], indent=2)
            
            # Handle CSV-like content
            elif isinstance(file_content, str) and '\n' in file_content:
                lines = file_content.split('\n')
                # Keep header + first 5 data lines
                sampled_lines = lines[:6] if len(lines) > 6 else lines
                return '\n'.join(sampled_lines)
            
            # Return as is if none of the above
            return file_content
            
        except json.JSONDecodeError:
            # If not valid JSON, treat as CSV/text
            lines = file_content.split('\n')
            sampled_lines = lines[:6] if len(lines) > 6 else lines
            return '\n'.join(sampled_lines)
        except Exception as e:
            self.logger.error(f"Error sampling data: {str(e)}")
            return file_content

    async def process_message(self, request: ChatMessage) -> Dict[str, Any]:
        """Process incoming chat messages and manage conversation flow."""
        # If this is the first message (with file content)
        if request.fileContents and request.fileNames:
            self.conversation_id = str(uuid.uuid4())  # Generate ID for storage only
            self.logger.info(f"{self.conversation_id}: Starting new conversation")
            
            # Process each file content
            file_contents_str = ""
            for i, (content, name) in enumerate(zip(request.fileContents, request.fileNames), 1):
                sampled_content = self._sample_data(content)
                file_contents_str += f"\nFile {i} ({name}):\n{sampled_content}\n"
            
            self.current_conversation = {
                "chatId": self.conversation_id,
                "history": [
                    {
                        "role": "system",
                        "content": self._get_system_prompt(request.useAiSearch)
                    },
                    {
                        "role": "user",
                        "content": f"File contents:{file_contents_str}\n\nUser query: {request.userInput}"
                    }
                ],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fileNames": request.fileNames,
                "useAiSearch": request.useAiSearch
            }
        else:
            if not self.current_conversation:
                self.logger.error("No active conversation")
                raise ValueError("No active conversation")
            
            self.current_conversation["history"].append({
                "role": "user",
                "content": request.userInput
            })
        
        try:
            response = await self._process_chat(request.useAiSearch)
            self._save_chat_history()  # Save after each message for analysis
            return response
        except Exception as e:
            self.logger.error(f"{self.conversation_id}: Error: {str(e)}")
            raise

    def _extract_response_blocks(self, response: str) -> None:
        """Extract different blocks from the model's response."""
        # Extract complete HTML
        html_match = re.search(r'```(.*?)```', response, re.DOTALL)
        if html_match:
            self.response_blocks['html'] = html_match.group(1).strip()
        
        # Extract Follow-up
        followup_match = re.search(r'<follow-up>(.*?)</follow-up>', response, re.DOTALL)
        if followup_match:
            self.response_blocks['followup'] = followup_match.group(1).strip()
            
        # Extract explanation (everything outside the blocks)
        explanation = response
        # Remove all tagged blocks
        explanation = re.sub(r'```.*?```', '', explanation, flags=re.DOTALL)
        explanation = re.sub(r'<follow-up>.*?</follow-up>', '', explanation, flags=re.DOTALL)
        self.response_blocks['explanation'] = explanation.strip()

    async def _process_chat(self, use_ai_search: bool = False) -> Dict[str, Any]:
        """Process chat messages through Azure OpenAI and handle the response."""
        try:
            if use_ai_search:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    temperature=0.2,
                    presence_penalty= 0.1,
                    frequency_penalty= 0.1,
                    max_tokens=3000,
                    top_p=1.0,
                    extra_body={  
                        "data_sources": [  
                            {  
                                "type": "azure_search",  
                                "parameters": {  
                                    "endpoint": os.getenv("AZURE_AI_SEARCH_ENDPOINT"),  
                                    "index_name": os.getenv("AZURE_AI_SEARCH_INDEX")
                                }  
                            }  
                        ]  
                    },
                    messages=self.current_conversation["history"]
                )
            else:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    temperature=0.2,
                    presence_penalty= 0.1,
                    frequency_penalty= 0.1,
                    max_tokens=3000,
                    top_p=1.0,
                    messages=self.current_conversation["history"]
                )
            
            assistant_response = response.choices[0].message.content
            self._update_conversation_history(assistant_response)
            
            # Extract response blocks
            self._extract_response_blocks(assistant_response)
            
            if self.response_blocks['html']:
                # Process and save the HTML response
                return self._handle_html_response(self.response_blocks['html'])
            
            return {
                "text": "No code returned",
                "additionalText": self.response_blocks['explanation'],
                "followup": self.response_blocks['followup'],
                "mapHtml": None
            }
        except Exception as e:
            self.logger.error(f"{self.conversation_id}: Processing error: {str(e)}")
            raise

    def _update_conversation_history(self, response: str) -> None:
        """Update the conversation history with the assistant's response."""
        self.current_conversation["history"].append({
            "role": "assistant",
            "content": response
        })

    def _handle_html_response(self, html_content: str) -> Dict[str, Any]:
        """Process and save the generated HTML content with necessary replacements."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"generated_maps/map_{self.conversation_id}_{timestamp}"
        
        # Replace placeholder with Azure Maps subscription key
        processed_html = html_content.replace(
            "AZURE_MAPS_SUBSCRIPTION_KEY",
            os.getenv("AZURE_MAPS_SUB_KEY")
        )

        # Replace placeholder USER_FILE_NAME_X with user file names
        for i, filename in enumerate(self.current_conversation["fileNames"], 1):
            processed_html = processed_html.replace(
                f"USER_FILE_NAME_{i}",
                f"http://127.0.0.1:8000/data/data_sample/{filename}"
            )
        
        # Save HTML
        with open(f"{base_filename}.html", "w") as f:
            f.write(processed_html)
            
        return {
            "text": "I've generated a map visualization. You can see it on the right panel.",
            "additionalText": self.response_blocks['explanation'],
            "followup": self.response_blocks['followup'],
            "mapHtml": processed_html
        }

    def _save_chat_history(self) -> None:
        """Save the current conversation history to a JSON file."""
        if self.conversation_id:
            filepath = f"chat_histories/chat_{self.conversation_id}.json"
            with open(filepath, "w") as f:
                json.dump(self.current_conversation, f)

    def _get_system_prompt(self, use_ai_search: bool = False) -> str:
        """Get the appropriate system prompt based on AI search usage."""
        if use_ai_search:
            return open('./templates/system_prompt_with_index.txt', 'r').read()
        else:
            return open('./templates/system_prompt.txt', 'r').read()

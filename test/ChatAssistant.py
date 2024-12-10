from pydantic import BaseModel
from azure.identity import AzureCliCredential, get_bearer_token_provider
from openai import AzureOpenAI
import os, re
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from dotenv import load_dotenv
load_dotenv()

class ChatRequest(BaseModel):
    fileContent: str
    fileName: str
    userInput: str

class ChatMessage(BaseModel):
    chatId: str
    userInput: str

class ChatAssistant:
    def __init__(self):
        self._create_directories()
        self._setup_logging()
        self.client = self._initialize_azure_openai()
        self.conversations: Dict[str, Dict[str, Any]] = {}
        self.logger.info("Chat Assistant initialized successfully")

    def _setup_logging(self) -> None:
        today_date = datetime.now().strftime("%Y%m%d")
        
        logging.basicConfig(
            filename=f"logs/{today_date}.log",
            encoding='utf-8',
            level=logging.DEBUG if os.getenv("DEBUG") == "True" else logging.INFO,
            format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d - %(funcName)s()] - %(message)s'
        )
        self.logger = logging.getLogger("azmaps-geo-assistant")
        self.logger.info("Initialized logging")

    def _setup_code_blocks(self) -> None:
        self.code_blocks = {
            'html': None,
            'css': None,
            'js': None,
            'title': None,
            'description': None,
            'explanation': None
        }

    def _create_directories(self) -> None:
        directories = ["generated_maps", "chat_histories", "logs"]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
    def _get_html_template(self) -> str:
        return open('./templates/html_template.txt', 'r').read()

    def _get_css_template(self) -> str:
        return open('./templates/css_template.txt', 'r').read()

    def _initialize_azure_openai(self) -> AzureOpenAI:
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
        """Sample the first 5 items from different file types"""
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

    async def start_new_chat(self, file_content: str, file_name: str, user_input: str) -> Dict[str, Any]:
        chat_id = str(uuid.uuid4())
        try:
            self.logger.info(f"{chat_id}: New chat session started")
            
            # Sample the data before sending to the model
            sampled_content = self._sample_data(file_content)
            
            self.conversations[chat_id] = {
                "history": [
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": f"File name:{file_name}\nFile content:\n{sampled_content}\n\nUser query: {user_input}"
                    }
                ],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "chatId": chat_id,
                "fileName": file_name,
            }
            
            # response = await self._process_chat(chat_id)
            # self._save_chat_history(chat_id)
            
            self._setup_code_blocks()
            return {
                "chatId": chat_id,
                "response": "OK"
            }
        except Exception as e:
            self.logger.error(f"{chat_id}: Error: {str(e)}")
            raise

    async def process_message(self, chat_id: str, user_input: str) -> Dict[str, Any]:
        if chat_id not in self.conversations:
            self.logger.error(f"Chat session not found: {chat_id}")
            raise ValueError("Chat session not found")
        
        try:
            self.conversations[chat_id]["history"].append({
                "role": "user",
                "content": user_input
            })
            
            response = await self._process_chat(chat_id)
            self._save_chat_history(chat_id)
            
            return response
        except Exception as e:
            self.logger.error(f"{chat_id}: Error: {str(e)}")
            raise

    def _extract_code_blocks(self, response: str) -> Dict[str, Optional[str]]:
        """Extract different code blocks from the response"""
        
        # Extract HTML
        html_match = re.search(r'<code-html>(.*?)</code-html>', response, re.DOTALL)
        if html_match:
            self.code_blocks['html'] = html_match.group(1).strip()
            
        # Extract CSS
        css_match = re.search(r'<code-css>(.*?)</code-css>', response, re.DOTALL)
        if css_match:
            self.code_blocks['css'] = css_match.group(1).strip()
            
        # Extract JavaScript
        js_match = re.search(r'<code-js>(.*?)</code-js>', response, re.DOTALL)
        if js_match:
            self.code_blocks['js'] = js_match.group(1).strip()

        # Extract title
        title_match = re.search(r'<sample-title>(.*?)</sample-title>', response, re.DOTALL)
        if title_match:
            self.code_blocks['title'] = title_match.group(1).strip()
        
        # Extract Description
        description_match = re.search(r'<sample-description>(.*?)</sample-description>', response, re.DOTALL)
        if description_match:
            self.code_blocks['description'] = description_match.group(1).strip()
            
        # Extract explanation (everything outside code blocks)
        explanation = response
        for tag in ['code-html', 'code-css', 'code-js', 'sample-title', 'sample-description']:
            explanation = re.sub(f'<{tag}>.*?</{tag}>', '', explanation, flags=re.DOTALL)
        self.code_blocks['explanation'] = explanation.strip()
    
    def _combine_code_blocks(self) -> str:
        """Combine code blocks into a single HTML file"""
        html_template = self._get_html_template()
        css_template = self._get_css_template()
        
        css = f"<style>\n{self.blocks['css']}\n{css_template}\n</style>" if self.blocks['css'] else f"{css_template}"
        js = f"<script>\n{self.blocks['js']}\n</script>" if self.blocks['js'] else ""
        
        return html_template.format(
            css=css,
            js=js,
            html=self.blocks['html'] or "",
            title=self.blocks['title'] or "Azure Maps Sample",
            description=self.blocks['description'] or "Azure Maps Sample Description",
            explaination=self.blocks['explanation'] or ""
        )

    async def _process_chat(self, chat_id: str) -> Dict[str, Any]:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                temperature=0.2,
                max_tokens=3000,
                messages=self.conversations[chat_id]["history"]
            )
            
            assistant_response = response.choices[0].message.content
            self._update_conversation_history(chat_id, assistant_response)
            
            # Extract code blocks
            self._extract_code_blocks(assistant_response)
            
            if self.code_blocks['html'] or self.code_blocks['css'] or self.code_blocks['js']:
                # Combine into single HTML file
                combined_html = self._combine_code_blocks()
                # Save and handle HTML response
                return self._handle_html_response(chat_id, combined_html)
            
            return {
                "text": self.code_blocks['explanation'],
                "mapHtml": None
            }
        except Exception as e:
            self.logger.error(f"{chat_id}: Processing error: {str(e)}")
            raise

    def _update_conversation_history(self, chat_id: str, response: str) -> None:
        self.conversations[chat_id]["history"].append({
            "role": "assistant",
            "content": response
        })

    def _handle_html_response(self, chat_id: str, html_content: str) -> Dict[str, Any]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save separate files for debugging/reference
        base_filename = f"generated_maps/map_{chat_id}_{timestamp}"
        
        # Replace placeholder with Azure Maps subscription key
        processed_html = html_content.replace(
            "AZURE_MAPS_SUBSCRIPTION_KEY",
            os.getenv("AZURE_MAPS_SUB_KEY")
        )

        # Replace placeholder USER_FILE_NAME with user file name, in format 
        processed_html = processed_html.replace(
            "USER_FILE_NAME",
            "http://127.0.0.1:8000/data/data_sample/" + self.conversations[chat_id]["fileName"]
        )
        
        # Save combined HTML
        with open(f"{base_filename}.html", "w") as f:
            f.write(processed_html)
            
        return {
            "text": "I've generated a map visualization. You can see it on the right panel.",
            "mapHtml": processed_html
        }

    def _save_chat_history(self, chat_id: str) -> None:
        filepath = f"chat_histories/chat_{chat_id}.json"
        with open(filepath, "w") as f:
            json.dump(self.conversations[chat_id], f)

    @staticmethod
    def _get_system_prompt() -> str:
        return open('./templates/system_prompt.txt', 'r').read()

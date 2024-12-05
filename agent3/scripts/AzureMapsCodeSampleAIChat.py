from dotenv import load_dotenv
load_dotenv()

from openai import AzureOpenAI
import os
from pathlib import Path
from common.constants import CONSTANTS

class VisualizationAgent:
    def __init__(self, samples_dir):
        self.client = AzureOpenAI(
            api_key=os.getenv('AzureOpenAI_API_KEY'),
            api_version=CONSTANTS.AZURE_OPENAI.API_VERSION,
            azure_endpoint=os.getenv('AzureOpenAI_ENDPOINT')
        )
        self.samples_dir = samples_dir
        self.context = self._prepare_context()
        
    def _load_samples(self):
        print("Loading samples...")
        samples = []
        try:
            for category_folder in os.listdir(self.samples_dir):
                category_path = Path(self.samples_dir) / category_folder
                if category_path.is_dir():
                    for sample_folder in category_path.iterdir():
                        if sample_folder.is_dir():
                            for html_file in sample_folder.glob('*.html'):
                                print(f"Loading: {category_folder}/{sample_folder.name}/{html_file.name}")
                                with open(html_file, 'r', encoding='utf-8') as f:
                                    samples.append({
                                        'name': html_file.name,
                                        'category': category_folder,
                                        'subcategory': sample_folder.name,
                                        'content': f.read()
                                    })
        except Exception as e:
            print(f"Error loading samples: {str(e)}")
            raise
        
        print(f"Loaded {len(samples)} samples")
        return samples

    def _prepare_system_message(self):
        return """You are a Visualization Intelligence Agent specialized in Azure Maps. 
        You help users create visualizations using Azure Maps SDK.
        
        When helping users:
        1. Understand their visualization needs
        2. Suggest appropriate visualization types
        3. Generate complete, working Azure Maps code
        4. Explain customization options
        
        Base your responses on the Azure Maps samples provided in the context.
        Be concise but informative in your responses."""

    def _prepare_context(self):
        samples = self._load_samples()
        context = "Available Azure Maps samples:\n\n"
        for sample in self.samples:
            context += f"Category: {sample['category']}\n"
            context += f"SubCategory: {sample['subcategory']}\n"
            context += f"Sample: {sample['name']}\n"
            context += f"Content: {sample['content']}\n"
            context += "---\n\n"
        return context

    def chat(self, user_input):
        try:
            messages = [
                {"role": "system", "content": self._prepare_system_message()},
                {"role": "system", "content": self._prepare_context()},
                {"role": "user", "content": user_input}
            ]

            response = self.client.chat.completions.create(
                model="gpt-4",  # your deployed model name
                messages=messages,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

def main():
    # Configuration
    API_KEY = "your-api-key"  # Replace with your API key
    SAMPLES_DIR = "path_to_samples_directory"  # Replace with your samples directory path

    try:
        # Initialize the agent
        agent = VisualizationAgent(API_KEY, SAMPLES_DIR)
        
        print("Visualization Intelligence Agent Ready! (Type 'quit' to exit)")
        
        # Interactive loop
        while True:
            user_input = input("\nYou: ")
            if user_input.lower() == 'quit':
                break
                
            response = agent.chat(user_input)
            print("\nAgent:", response)

    except Exception as e:
        print(f"Application error: {str(e)}")

if __name__ == "__main__":
    main()
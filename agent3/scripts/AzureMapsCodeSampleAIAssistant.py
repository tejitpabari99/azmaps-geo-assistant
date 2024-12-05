from openai import AzureOpenAI
import os, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Constants
SAMPLES_DIR = "../AzureMapsCodeSamples/Samples"
CONFIG_FILE = '../config/assistant_config.json'
API_VERSION = "2024-08-01-preview"

def initialize_client():
    try:
        client = AzureOpenAI(
            api_key=os.getenv('AzureOpenAI_API_KEY'),
            api_version=API_VERSION,
            azure_endpoint=os.getenv('AzureOpenAI_ENDPOINT')
        )
        # Test the connection
        client.models.list()  # This will verify the connection
        return client
    except Exception as e:
        print(f"Error initializing Azure OpenAI client: {str(e)}")
        raise

def upload_sample_files(client, samples_dir):
    file_ids = []
    try:
        for category_folder in os.listdir(samples_dir):
            category_path = Path(samples_dir) / category_folder
            if category_path.is_dir():
                for sample_folder in category_path.iterdir():
                    if sample_folder.is_dir():
                        # Combine all samples in a category into one file
                        category_content = []
                        for html_file in sample_folder.glob('*.html'):
                            print(f"Uploading: {category_folder}/{sample_folder.name}/{html_file.name}")
                            with open(html_file, 'r', encoding='utf-8') as f:
                                file = client.files.create(
                                    file=(html_file.name, f.read(), 'text/html'),
                                    purpose='assistants'
                                )
                                file_ids.append(file.id)
    except Exception as e:
        print(f"Error in upload_sample_files: {str(e)}")
        raise
    return file_ids

def create_visualization_assistant(client, file_ids):
    assistant = client.beta.assistants.create(
        name="Azure Maps Visualization Assistant",
        instructions="""You are a Visualization Intelligence Agent specialized in Azure Maps. 
        Your role is to help users create visualizations using Azure Maps SDK.
        
        When helping users:
        1. Analyze their data needs
        2. Suggest appropriate visualization types
        3. Generate complete, working Azure Maps code
        4. Explain customization options
        
        Use the provided Azure Maps samples as reference for generating code.
        Be interactive and ask clarifying questions when needed.""",
        model="gpt-4-1106-preview",
        tools=[{"type": "code_interpreter"}],
        file_ids=file_ids
    )
    return assistant

def load_or_create_assistant(client):
    # Check if we have a stored assistant ID
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            print("Loading existing assistant...")
            aid = config.get('assistant_id', None)
            fids = config.get('file_ids', None)
            if aid:
                return aid, fids
            else: 
                print("No assistant id found...")
    
    print("Creating new assistant...")
    # If not, create new assistant
    file_ids = upload_sample_files(client, SAMPLES_DIR)
    assistant = create_visualization_assistant(client, file_ids)
    
    # Store the configuration
    config = {
        'assistant_id': assistant.id,
        'file_ids': file_ids
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
    
    return assistant.id, file_ids

def create_thread(client):
    return client.beta.threads.create()

def chat_with_assistant(client, assistant_id, thread_id, user_message):
    # Add the user's message to the thread
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message
    )

    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )

    # Wait for completion
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        if run_status.status == 'completed':
            break

    # Get the assistant's response
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return messages.data[0].content[0].text.value

def start_interactive_session(client, assistant_id, thread_id):
    print("Visualization Intelligence Agent Ready! (Type 'quit' to exit)")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower().strip() == 'quit':
            break
            
        response = chat_with_assistant(client, assistant_id, thread_id, user_input)
        print("\nAgent:", response)

# Run the setup and start interaction
if __name__ == "__main__":
    client = initialize_client()
    assistant_id, file_ids = load_or_create_assistant(client)
    thread_id = create_thread(client)
    start_interactive_session(client, assistant_id, thread_id)
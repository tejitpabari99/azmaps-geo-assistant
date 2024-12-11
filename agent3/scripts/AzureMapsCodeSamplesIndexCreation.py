from dotenv import load_dotenv
load_dotenv()

from common.constants import CONSTANTS
from common.helpers import get_project_root
from bs4 import BeautifulSoup
import os, json, shutil
import re
import uuid

def _clean_filename(text):
    cleaned = text.split('.')[0]
    # Keep only alphanumeric characters, hyphens, and underscores
    # Replace spaces with underscores
    # Convert to lowercase
    cleaned = re.sub(r'[^\w\-\s]', '', str(cleaned)).lower()
    # Replace spaces with underscores
    cleaned = re.sub(r'\s+', '_', cleaned)
    # Remove multiple consecutive underscores
    cleaned = re.sub(r'_+', '_', cleaned)
    # Remove leading/trailing underscores and spaces
    cleaned = cleaned.strip('_').strip()
    return cleaned

def process_html_sample(file_path, file_name, category):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Parse HTML
    soup = BeautifulSoup(content, 'html.parser')

    # Extract script content
    script_tags = soup.find_all('script')
    code_snippets = []
    for script in script_tags:
        if script.string:
            code_snippets.append(script.string)
    code_snippet = '\n'.join(code_snippets)

    # Extract fieldset content
    fieldset_tags = soup.find_all('fieldset')
    usage_descriptions = []
    for fieldset in fieldset_tags:
        if fieldset.string:
            usage_descriptions.append(fieldset.string.strip())
        else:
            # Get all text within fieldset even if nested
            usage_descriptions.append(fieldset.get_text(strip=True))
    usage_description = '\n'.join(usage_descriptions)
    
    sample_json = {
        "id": str(uuid.uuid4()),
        "file_name": file_name,
        "content_type": "azmaps_code_sample",
        "category": category,
        "title": soup.find('title').text,
        "description": soup.find('meta', {'name': 'description'})['content'],
        "keywords": soup.find('meta', {'name': 'keywords'})['content'].split(','),
        "code_snippet": code_snippet if code_snippet else "No Azure Maps code found",
        "api_reference": None,
        "content": content,
        "usage_description": usage_description if usage_description else "No usage description found",
    }
    
    # For embedding content, combine title, category, description, usage_description and keywords in a single string
    # Prefix each with its name, and separate by | character
    sample_json["embedding_content"] = f"title: {sample_json['title']} | category: {sample_json['category']} | description: {sample_json['description']} | usage_description: {sample_json['usage_description']} | keywords: {', '.join(sample_json['keywords'])}"
    return sample_json

def process_html_sample2(file_path, file_name, category):
    sample_json = process_html_sample(file_path, file_name, category)
    return {
        "id": sample_json["id"],
        "content_type": "code_sample",
        "title": sample_json["file_name"].split('.')[0],
        "content": sample_json["content"],
        "embedding_content": sample_json["embedding_content"]
    }

def process_all_samples(process_fun = process_html_sample, save_file_name = 'azmaps_code_samples.json', add_to_existing = False):
    source_folder = os.path.join(get_project_root(), CONSTANTS.AGENT3.AZURE_MAPS_CODE_SAMPLES_FOLDER)
    samples = []

    # Walk through all directories and subdirectories
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if file.lower().endswith(('.html', '.htm')):
                source_file = os.path.join(root, file)

                # Extract category (file root folder name) and store category - filename
                category = root.split("\\")[-2].replace("-", " ")
                file_name = f"{category}-{file}"
                sample_json = process_fun(source_file, file_name, category)
                samples.append(sample_json)

    dest_file_path = os.path.join(get_project_root(), CONSTANTS.AGENT3.DATA_FOLDER, save_file_name)
    if add_to_existing:
        # If file is present, load it and append to it
        if os.path.exists(dest_file_path):
            existing_samples = json.load(open(dest_file_path, 'r'))
            samples.extend(existing_samples)
        json.dump(samples, open(dest_file_path, 'w'), indent=4)
        return
    # If file is present, delete it
    if os.path.exists(dest_file_path):
        os.remove(dest_file_path)
    json.dump(samples, open(dest_file_path, 'w'), indent=4)

def create_samples_folder_upload():
    source_folder = os.path.join(get_project_root(), CONSTANTS.AGENT3.AZURE_MAPS_CODE_SAMPLES_FOLDER)
    destination_folder = os.path.join(get_project_root(), CONSTANTS.AGENT3.DATA_FOLDER, 'azure_maps_samples')

    # If folder exists, delete it, then create one
    if os.path.exists(destination_folder):
        shutil.rmtree(destination_folder)
    os.makedirs(destination_folder)
    
    counter = 0
    
    # Walk through all directories and subdirectories
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if file.lower().endswith(('.html', '.htm')):
                source_file = os.path.join(root, file)

                # Extract category (file root folder name) and store category - filename
                category = root.split("\\")[-2].replace("-", " ")
                destination_file = os.path.join(destination_folder, f"{category}-{file}")
                
                # Copy the file
                try:
                    shutil.copy2(source_file, destination_file)
                    counter += 1
                except Exception as e:
                    print(f"Error copying {source_file}: {str(e)}")
    print(f"Copied {counter} files to {destination_folder}")

if __name__ == "__main__":
    # create_samples_folder_upload()
    process_all_samples()
from dotenv import load_dotenv
load_dotenv()

import yaml
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import uuid
from common.constants import CONSTANTS
from common.helpers import get_project_root

def _parse_inner_info(doc, key):
    """Parse inner information from a YML document"""
    result = []
    if key in doc:
        result.append(f"{key.capitalize()}:")
        for item in doc[key]:
            result.append(f"- Name: {item.get('name', '')}")
            summary = item.get('summary', '').replace('\n', ' ')
            result.append(f"  Summary: {summary}")
    return '\n'.join(result)

def process_yml_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Process a single YML file and convert it to search index document format"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            doc = yaml.safe_load(file)
            # UID or File Name
            title = doc.get("uid", "") or Path(file_path).stem
            content = open(file_path, 'r', encoding='utf-8').read()

            content_parts = []
            content_parts.append(f"Type: {doc.get('type', '')} | Name: {doc.get('name', '')} | Package: {doc.get('package', '')} | UID: {doc.get('uid', '')} | Summary: {doc.get('summary', '')}")
            
            content_parts.append(_parse_inner_info(doc, 'constructors'))
            content_parts.append(_parse_inner_info(doc, 'properties'))
            content_parts.append(_parse_inner_info(doc, 'methods'))
            content_parts.append(_parse_inner_info(doc, 'fields'))
            # content_parts.append(_parse_inner_info(doc, 'inheritedProperties'))
            # content_parts.append(_parse_inner_info(doc, 'inheritedMethods'))

            if 'extends' in doc:
                content_parts.append(f"Extends: {doc['extends']}")
            
            embedding_content = '\n'.join(content_parts)
            return {
                "id": str(uuid.uuid4()),
                "content_type": "sdk_docs",
                "title": title,
                "content": content,
                "embedding_content": embedding_content
            }
            
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return None

def process_all_docs(process_fun = process_yml_file, save_file_name = 'azmaps_code_samples.json', add_to_existing = False):
    source_folder = os.path.join(get_project_root(), CONSTANTS.AGENT3.AZURE_SDK_DOCS_FOLDER)
    docs = []

    # Walk through all directories and subdirectories
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if file.lower().endswith(('.yml')) and 'toc.yml' not in file:
                source_file = os.path.join(root, file)
                doc_json = process_fun(source_file)
                docs.append(doc_json)

    dest_file_path = os.path.join(get_project_root(), CONSTANTS.AGENT3.DATA_FOLDER, save_file_name)
    if add_to_existing:
        # If file is present, load it and append to it
        if os.path.exists(dest_file_path):
            existing_samples = json.load(open(dest_file_path, 'r'))
            docs.extend(existing_samples)
        json.dump(docs, open(dest_file_path, 'w'), indent=4)
        return
    # If file is present, delete it
    if os.path.exists(dest_file_path):
        os.remove(dest_file_path)
    json.dump(docs, open(dest_file_path, 'w'), indent=4)
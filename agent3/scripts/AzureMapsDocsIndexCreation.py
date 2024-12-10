from dotenv import load_dotenv
load_dotenv()

import yaml
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import uuid

def process_yml_file(file_path: str) -> Optional[Dict[str, Any]]:
    """Process a single YML file and convert it to search index document format"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            doc = yaml.safe_load(file)
            
            # Create simplified search document with essential information
            search_doc = {
                "id":str(uuid.uuid4()),  # Required unique identifier
                "uid": doc.get("uid", ""), # Unique identifier from YML file
                "name": doc.get("name", ""),  # Class/interface/type name
                "type": doc.get("type", ""),  # e.g., class, interface, type
                "summary": doc.get("summary", ""),  # Main description
                "package": doc.get("package", ""),  # Package name (azure-maps-control)
                "isDeprecation": doc.get("isDeprecation", False),

                # Simplified properties list - just name and description
                "properties": [
                    {
                        "name": prop.get("name", ""),
                        "description": prop.get("summary", ""),
                        "isDeprecated": prop.get("isDeprecated", False)
                    }
                    for prop in doc.get("properties", [])
                    if prop.get("name")
                ],
                
                # Simplified methods list - just name, description, and parameters
                "methods": [
                    {
                        "name": method.get("name", ""),
                        "description": method.get("summary", ""),
                        "parameters": [
                            f"{param.get('id')}: {param.get('description')}"
                            for param in method.get("syntax", {}).get("parameters", [])
                            if param.get('id') and param.get('description')
                        ]
                    }
                    for method in doc.get("inheritedMethods", [])
                    if method.get("name") and method.get("summary")
                ],
                
                # Combined searchable text for better semantic search
                "content": " ".join([
                    doc.get("name", ""),
                    doc.get("summary", ""),
                    doc.get("fullName", ""),
                    " ".join(
                        prop.get("summary", "")
                        for prop in doc.get("properties", [])
                    ),
                    " ".join(
                        method.get("summary", "")
                        for method in doc.get("inheritedMethods", [])
                    )
                ]).strip()
            }
            
            return search_doc
            
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return None

def process_directory(directory_path: str) -> List[Dict[str, Any]]:
    """Process all YML files in a directory and create search documents"""
    search_documents = []
    yml_files = Path(directory_path).glob('**/*.yml')
    
    for file_path in yml_files:
        doc = process_yml_file(str(file_path))
        if doc:
            search_documents.append(doc)
            print(f"Processed: {file_path.name}")
    
    return search_documents

def save_documents(documents: List[Dict[str, Any]], output_file: str):
    """Save processed documents to a JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2)

if __name__ == "__main__":
    yml_directory = "./yml_docs"
    output_file = "processed_api_docs.json"
    
    print("Processing YML files...")
    documents = process_directory(yml_directory)
    
    print(f"\nSaving {len(documents)} documents to {output_file}...")
    save_documents(documents, output_file)
    
    print("\nProcessing complete!")
import logging
import azure.functions as func
import json
from bs4 import BeautifulSoup

app = func.FunctionApp()

@app.function_name(name="azmaps_sample_extract_code")
@app.route(route="azmaps_sample_extract_code", auth_level=func.AuthLevel.FUNCTION)
def azmaps_sample_extract_code(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Get request body
        body = req.get_json()

        values = body.get('values', [])
        
        results = []
        for record in values:
            # Process each record
            try:
                recordId = record['recordId']
                html_content = record['data']['content']
                
                # Parse HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                
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
                
                # Add the record to results
                results.append({
                    "recordId": recordId,
                    "data": {
                        "code_snippet": code_snippet if code_snippet else "No Azure Maps code found",
                        "usage_description": usage_description if usage_description else "No usage description found"
                    },
                    "errors": None,
                    "warnings": None
                })
                
            except Exception as error:
                results.append({
                    "recordId": recordId,
                    "data": {
                        "code_snippet": None,
                        "usage_description": None
                    },
                    "errors": [{"message": str(error)}],
                    "warnings": None
                })
                        
        # Return the results
        return func.HttpResponse(
            body=json.dumps({"values": results}),
            mimetype="application/json"
        )
            
    except Exception as ex:
        return func.HttpResponse(
            json.dumps({
                "values": [{
                    "recordId": None,
                    "errors": [{"message": str(ex)}]
                }]
            }),
            status_code=500,
            mimetype="application/json"
        )
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from ChatAssistant import ChatAssistant, ChatMessage
import os

from dotenv import load_dotenv
load_dotenv()

# Initialize FastAPI app and ChatAssistant
app = FastAPI()
assistant = ChatAssistant()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat")
async def chat(request: ChatMessage):
    try:
        return await assistant.process_message(request)
    except ValueError as e:
        assistant.logger.error(f"Failed to process chat message: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        assistant.logger.error(f"Failed to process chat message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data")
async def list_data_files():
    """List all files in the data directory"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "data")
    
    html_content = ["<html><body><h1>Data Files:</h1><ul>"]
    
    for root, dirs, files in os.walk(data_dir):
        rel_path = os.path.relpath(root, data_dir)
        if rel_path == ".":
            path_prefix = ""
        else:
            path_prefix = rel_path + "/"
            
        for file in files:
            file_path = path_prefix + file
            html_content.append(f'<li><a href="/data/{file_path}">{file_path}</a></li>')
    
    html_content.append("</ul></body></html>")
    return HTMLResponse(content="\n".join(html_content))

# Get current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Serve static files
app.mount("/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static")
# Mount data directory with directory listing enabled
app.mount("/data", StaticFiles(directory=os.path.join(current_dir, "data"), html=True), name="data")
# Root should be last to not override other routes
app.mount("/", StaticFiles(directory=os.path.join(current_dir, "static"), html=True), name="root")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

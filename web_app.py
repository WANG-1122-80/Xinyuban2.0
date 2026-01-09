import uvicorn
import re
import uuid
import json
from typing import Dict, List, Optional
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os

# Import the graph app from rag_graph.py
# IMPORTANT: This assumes rag_graph.py exposes 'app'
from rag_graph import app as graph_app
from langchain_core.messages import HumanMessage, AIMessage

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class SessionData(BaseModel):
    id: str
    name: str
    chat_history: List[dict] # [{"sender": "user", "text": "..."}, ...]
    thought_history: List[dict]
    turn_count: int

# In-memory store
sessions: Dict[str, SessionData] = {}
DATA_FILE = "sessions_data.json"

def save_sessions():
    """Persist sessions to a JSON file."""
    data = {}
    for sid, session in sessions.items():
        data[sid] = session.model_dump()
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving sessions: {e}")

def load_sessions():
    """Load sessions from JSON file."""
    global sessions
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for sid, sdata in data.items():
                sessions[sid] = SessionData(**sdata)
            print(f"Loaded {len(sessions)} sessions from {DATA_FILE}")
        except Exception as e:
            print(f"Error loading sessions: {e}")

# Load on startup
load_sessions()

# Initialize default if missing
if "default" not in sessions:
    sessions["default"] = SessionData(
        id="default", name="默认对话", chat_history=[], thought_history=[], turn_count=0
    )
    save_sessions()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/new_session")
async def new_session():
    session_id = str(uuid.uuid4())
    session_name = f"咨询会话 {len(sessions) + 1}"
    sessions[session_id] = SessionData(
        id=session_id,
        name=session_name,
        chat_history=[],
        thought_history=[],
        turn_count=0
    )
    save_sessions()
    return {"session_id": session_id, "name": session_name}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
        save_sessions()
        return {"success": True}
    return {"error": "Session not found"}

@app.get("/sessions")
async def get_sessions():
    return {"sessions": [{"id": s.id, "name": s.name} for s in sessions.values()]}

@app.get("/session_history")
async def get_session_history(session_id: str):
    if session_id in sessions:
        return sessions[session_id]
    return {"error": "Session not found"}

@app.get("/thoughts")
async def get_thoughts(session_id: str = "default"):
    if session_id in sessions:
        return {"history": sessions[session_id].thought_history}
    return {"history": []}

@app.post("/chat")
async def chat(request: ChatRequest):
    user_query = request.message
    session_id = request.session_id
    
    if session_id not in sessions:
        # Fallback or create? Let's just create if missing or default to default
        if session_id == "default":
             if "default" not in sessions:
                  sessions["default"] = SessionData(id="default", name="默认对话", chat_history=[], thought_history=[], turn_count=0)
        else:
             return {"response": "会话不存在，请刷新页面。", "error": True}
        
    session = sessions[session_id]
    session.turn_count += 1
    
    # Store User Msg
    session.chat_history.append({"sender": "user", "text": user_query})
    
    # Initial State for the graph
    # Construct history messages for LangGraph input
    history_messages = []
    for msg in session.chat_history[-10:]: # Last 10 messages context
        if msg["sender"] == "user":
            history_messages.append(HumanMessage(content=msg["text"]))
        else:
            history_messages.append(AIMessage(content=msg["text"]))
    
    initial_state = {
        "messages": history_messages,
        "context": ""
    }
    
    bot_response = "..."
    raw_response = ""
    
    try:
        # Run the graph
        output = graph_app.invoke(initial_state)
        messages = output['messages']
        last_msg = messages[-1]
        raw_response = last_msg.content
        
        # 1. Separate Thoughts from Reply
        # Regex to find [------思考过程------ ... ] content
        pattern = r"\[------思考过程------(.*?)\]"
        match = re.search(pattern, raw_response, re.DOTALL)
        
        parsed_thoughts = {
            "turn": session.turn_count,
            "stage": "未知",
            "mood": "未识别", 
            "needs": "未识别",
            "supervision": "未识别",
            "focus": "未启用",
            "change_tools": "未启用",
            "notes": "无"
        }

        if match:
            thought_content = match.group(1).strip()
            # Remove the thought block from the final response
            bot_response = re.sub(pattern, "", raw_response, flags=re.DOTALL).replace("思考ing... 正在为你准备暖心回复：", "").replace("---", "").strip()
            
            # 2. Parse Thought Fields (Robust Regex extraction)
            try:
                # Extract Stage (usually first line)
                lines = thought_content.split('\n')
                if lines:
                    parsed_thoughts["stage"] = lines[0].strip()

                def extract_section_regex(text, header_pattern):
                    # headers start typically with · or just text, followed eventually by content
                    # We look for the specific header, then capture everything until the next likely header or end of string
                    # The next header is any of our known headers
                    
                    # Known headers pattern part
                    all_headers_str = "实时(?:AI)?督导|需求分析|聚焦技术|例外探索|促进改变|建议工具包|情绪反馈|会谈小记"
                    
                    # Pattern: 
                    # 1. match the header (loose matching for bullets/colons)
                    # 2. match content (non-greedy)
                    # 3. lookahead for next header OR end of string
                    
                    # regex for the specific header we want: 
                    # (?:\·|\-|\*|\s)? matches optional bullet
                    # header_pattern matches the keyword
                    # [:\uff1a]? matches optional colon
                    # \s* matches optional whitespace
                    
                    pattern = re.compile(
                        r"(?:^|\n)(?:[\·\-\*\s]+)?" + header_pattern + r"[:\uff1a]?\s*(.*?)(?=(?:\n(?:[\·\-\*\s]+)?(?:" + all_headers_str + r"))|$)", 
                        re.DOTALL | re.IGNORECASE
                    )
                    
                    match_sect = pattern.search(text)
                    if match_sect:
                        return match_sect.group(1).strip()
                    return "无"

                parsed_thoughts["mood"] = extract_section_regex(thought_content, "情绪反馈")
                parsed_thoughts["needs"] = extract_section_regex(thought_content, "需求分析")
                parsed_thoughts["supervision"] = extract_section_regex(thought_content, "实时(?:AI)?督导")
                parsed_thoughts["focus"] = extract_section_regex(thought_content, "聚焦技术")
                
                # Combing Exception/Change/Toolkit into one column "Change/Tools"
                exception = extract_section_regex(thought_content, "例外探索")
                change = extract_section_regex(thought_content, "促进改变")
                tools = extract_section_regex(thought_content, "建议工具包")
                
                features = []
                if exception != "无": features.append(f"<b>例外:</b> {exception}")
                if change != "无": features.append(f"<b>改变:</b> {change}")
                if tools != "无": features.append(f"<b>工具:</b> {tools}")
                
                parsed_thoughts["change_tools"] = "<br>".join(features) if features else "无"

                # Fix Note extraction
                parsed_thoughts["notes"] = extract_section_regex(thought_content, "会谈小记")
                
            except Exception as parse_e:
                print(f"Error parsing thoughts: {parse_e}")

        else:
            bot_response = raw_response

        # Store thoughts in session
        session.thought_history.append(parsed_thoughts)
        
        # Store Bot Msg in session
        session.chat_history.append({"sender": "bot", "text": bot_response})
        
        save_sessions()

    except Exception as e:
        print(f"Error processing graph: {e}")
        bot_response = "抱歉，我现在有点累，请稍后再试...(系统错误)"

    return {"response": bot_response}

if __name__ == "__main__":
    print("--- 启动 Web 前端服务 ---")
    print("请在浏览器打开: http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)

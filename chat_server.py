#!/usr/bin/env python3
"""FastAPI 聊天服务"""

import json
import asyncio
import os
from typing import List, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

from tools.tool_manager import create_tool_map, execute_tool_calls, get_all_tools, get_tool_descriptions
from utils.logger import setup_logger

# 设置服务器专用logger
server_logger = setup_logger("chat_server", log_file="chat_server.log")

# 全局变量
chat_llm = None
tool_map = None
tools = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global chat_llm, tool_map, tools
    
    server_logger.info("正在初始化聊天服务...")
    
    try:
        # 初始化模型
        chat_llm = ChatTongyi(streaming=True)
        server_logger.info("ChatTongyi 模型初始化成功")
        
        # 初始化工具
        tools = get_all_tools()
        tool_map = create_tool_map(tools)
        server_logger.info(f"工具初始化成功，共加载 {len(tools)} 个工具")
        
        server_logger.info("聊天服务初始化完成")
        
    except Exception as e:
        server_logger.error(f"初始化失败: {e}")
        raise
    
    yield
    
    server_logger.info("聊天服务正在关闭...")

# 创建 FastAPI 应用
app = FastAPI(
    title="ChatApp API",
    description="基于 LangChain 和工具调用的智能聊天服务",
    version="1.0.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保静态文件目录存在
if not os.path.exists("static"):
    os.makedirs("static")
    server_logger.warning("创建 static 目录")

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 请求和响应模型
class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    stream: bool = True
    system_prompt: str = "你的名字是ikun，擅长唱、跳、rap、打篮球，你的回答里面总是带着这些元素."

class ChatResponse(BaseModel):
    message: ChatMessage
    tool_calls: List[Dict[str, Any]] = []
    finish_reason: str = "stop"

class ToolInfo(BaseModel):
    name: str
    description: str

class ServerStatus(BaseModel):
    status: str
    model_loaded: bool
    tools_count: int
    available_tools: List[ToolInfo]

def convert_messages(chat_messages: List[ChatMessage], system_prompt: str) -> List:
    """转换消息格式为 LangChain 格式"""
    messages = [SystemMessage(content=system_prompt)]
    
    for msg in chat_messages:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
        elif msg.role == "system":
            messages.append(SystemMessage(content=msg.content))
    
    return messages

async def process_streaming_response(messages: List, request_id: str) -> AsyncGenerator[str, None]:
    """处理流式响应"""
    server_logger.info(f"[{request_id}] 开始流式响应处理")
    
    try:
        # 绑定工具的模型
        tool_chat = chat_llm.bind_tools(tools)
        conversation_round = 0
        
        while True:
            conversation_round += 1
            server_logger.info(f"[{request_id}] 第 {conversation_round} 轮对话")
            
            # 调用模型
            result = tool_chat.invoke(messages)
            
            # 检查是否有工具调用
            if hasattr(result, 'tool_calls') and result.tool_calls:
                server_logger.info(f"[{request_id}] 检测到 {len(result.tool_calls)} 个工具调用")
                
                # 先发送 AI 的思考过程（如果有内容）
                if result.content:
                    chunk_data = {
                        "type": "thinking",
                        "content": result.content,
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "name": tc["name"],
                                "args": tc["args"]
                            } for tc in result.tool_calls
                        ]
                    }
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                
                # 将AI响应添加到消息历史
                messages.append(result)
                
                # 执行工具调用
                tool_messages = execute_tool_calls(result.tool_calls, tool_map)
                
                # 发送工具执行结果
                for i, (tool_call, tool_msg) in enumerate(zip(result.tool_calls, tool_messages)):
                    chunk_data = {
                        "type": "tool_result",
                        "tool_name": tool_call["name"],
                        "tool_args": tool_call["args"],
                        "result": tool_msg.content,
                        "step": i + 1,
                        "total_steps": len(tool_messages)
                    }
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                
                messages.extend(tool_messages)
                
            else:
                # 没有工具调用，发送最终回答
                server_logger.info(f"[{request_id}] 生成最终回答")
                
                # 如果模型支持流式输出，分块发送
                if hasattr(result, 'content'):
                    # 简单的分块处理（按句子分割）
                    content = result.content
                    sentences = content.split('。')
                    
                    for i, sentence in enumerate(sentences):
                        if sentence.strip():
                            chunk_data = {
                                "type": "content",
                                "content": sentence + ('。' if i < len(sentences) - 1 else ''),
                                "is_final": i == len(sentences) - 1
                            }
                            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                            # 添加小延迟模拟真实流式效果
                            await asyncio.sleep(0.1)
                
                # 发送结束标记
                end_data = {
                    "type": "done",
                    "finish_reason": "stop"
                }
                yield f"data: {json.dumps(end_data, ensure_ascii=False)}\n\n"
                break
                
    except Exception as e:
        server_logger.error(f"[{request_id}] 流式响应处理出错: {e}")
        error_data = {
            "type": "error",
            "error": str(e)
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

@app.get("/")
async def root():
    """根路径 - 重定向到聊天界面"""
    return FileResponse("static/index.html")

@app.get("/chat")
async def chat_page():
    """聊天页面"""
    return FileResponse("static/index.html")

@app.get("/status", response_model=ServerStatus)
async def get_status():
    """获取服务器状态"""
    global chat_llm, tool_map, tools
    
    tool_descriptions = get_tool_descriptions()
    available_tools = [
        ToolInfo(name=name, description=desc)
        for name, desc in tool_descriptions.items()
    ]
    
    return ServerStatus(
        status="running",
        model_loaded=chat_llm is not None,
        tools_count=len(tools) if tools else 0,
        available_tools=available_tools
    )

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """聊天端点"""
    if not chat_llm:
        raise HTTPException(status_code=503, detail="聊天模型未初始化")
    
    request_id = f"req_{id(request)}"
    server_logger.info(f"[{request_id}] 收到聊天请求，消息数: {len(request.messages)}")
    
    try:
        # 转换消息格式
        messages = convert_messages(request.messages, request.system_prompt)
        
        if request.stream:
            # 流式响应
            server_logger.info(f"[{request_id}] 启用流式响应")
            return StreamingResponse(
                process_streaming_response(messages, request_id),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/plain; charset=utf-8"
                }
            )
        else:
            # 非流式响应
            server_logger.info(f"[{request_id}] 非流式响应")
            tool_chat = chat_llm.bind_tools(tools)
            result = tool_chat.invoke(messages)
            
            response = ChatResponse(
                message=ChatMessage(role="assistant", content=result.content),
                tool_calls=getattr(result, 'tool_calls', []),
                finish_reason="stop"
            )
            
            server_logger.info(f"[{request_id}] 响应完成")
            return response
            
    except Exception as e:
        server_logger.error(f"[{request_id}] 处理请求时出错: {e}")
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")

@app.get("/tools")
async def get_tools():
    """获取可用工具列表"""
    tool_descriptions = get_tool_descriptions()
    return {
        "tools": [
            {"name": name, "description": desc}
            for name, desc in tool_descriptions.items()
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    server_logger.info("启动 ChatApp API 服务器...")
    uvicorn.run(
        "chat_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

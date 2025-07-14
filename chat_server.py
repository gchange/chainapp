#!/usr/bin/env python3
"""FastAPI 聊天服务"""

import json
import asyncio
import os
from typing import List, Dict, Any, AsyncGenerator, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

from tools.tool_manager import create_tool_map, execute_tool_calls, get_all_tools, get_tool_descriptions
from utils.logger import setup_logger
from utils.session_manager import session_manager
from models.model_manager import model_manager
from storage.storage_manager import storage_manager as storage_mgr, StorageConfig
from roles.role_manager import role_manager, RoleConfig
from storage.storage_manager import storage_manager as storage_mgr, StorageConfig

# 设置服务器专用logger
server_logger = setup_logger("chat_server", log_file="chat_server.log")

# 全局变量
tool_map = None
tools = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global tool_map, tools
    
    server_logger.info("正在初始化聊天服务...")
    
    try:
        # 初始化工具
        tools = get_all_tools()
        tool_map = create_tool_map(tools)
        server_logger.info(f"工具初始化成功，共加载 {len(tools)} 个工具")
        
        # 检查模型状态
        current_model = model_manager.get_current_model()
        if current_model:
            config = model_manager.get_current_config()
            server_logger.info(f"当前使用模型: {config.display_name}")
        else:
            server_logger.warning("没有加载任何模型")
        
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
    messages: List[ChatMessage] = []  # 如果提供了session_id，这个可以为空
    stream: bool = True
    system_prompt: str = "你的名字是ikun，擅长唱、跳、rap、打篮球，你的回答里面总是带着这些元素."
    session_id: Optional[str] = None
    use_memory: bool = True

class ChatResponse(BaseModel):
    message: ChatMessage
    tool_calls: List[Dict[str, Any]] = []
    finish_reason: str = "stop"

class ToolInfo(BaseModel):
    name: str
    description: str

class ModelInfo(BaseModel):
    name: str
    display_name: str
    provider: str
    description: str
    is_current: bool
    is_available: bool

class ServerStatus(BaseModel):
    status: str
    current_model: Optional[str]
    available_models: List[ModelInfo]
    tools_count: int
    available_tools: List[ToolInfo]
    session_count: int

class SwitchModelRequest(BaseModel):
    name: str

class StorageConfigRequest(BaseModel):
    backend: str
    config: Dict[str, Any]

class CreateSessionRequest(BaseModel):
    system_prompt: Optional[str] = None
    role_id: Optional[str] = None
    user_info: Optional[Dict[str, Any]] = None

class CreateRoleRequest(BaseModel):
    name: str
    description: str
    system_prompt: str
    avatar: str = "🤖"
    category: str = "通用"
    tags: Optional[List[str]] = None

class UpdateRoleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    avatar: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

class RoleResponse(BaseModel):
    role_id: str
    name: str
    description: str
    system_prompt: str
    avatar: str
    category: str
    tags: List[str]
    created_at: float
    updated_at: float
    is_system: bool
    user_id: Optional[str] = None

class SessionInfo(BaseModel):
    session_id: str
    created_at: float
    last_active: float
    message_count: int
    system_prompt: str

class SessionResponse(BaseModel):
    session_id: str
    message: str = "会话创建成功"

def convert_messages(chat_messages: List[ChatMessage], system_prompt: str, session_id: Optional[str] = None) -> List:
    """转换消息格式为 LangChain 格式"""
    messages = [SystemMessage(content=system_prompt)]
    
    # 如果有会话ID，加载历史消息
    if session_id:
        historical_messages = session_manager.get_messages(session_id, limit=20)  # 最近20条消息
        for hist_msg in historical_messages:
            if hist_msg.role == "user":
                messages.append(HumanMessage(content=hist_msg.content))
            elif hist_msg.role == "assistant":
                messages.append(AIMessage(content=hist_msg.content))
    
    # 添加当前消息
    for msg in chat_messages:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
        elif msg.role == "system":
            messages.append(SystemMessage(content=msg.content))
    
    return messages

async def process_streaming_response(messages: List, request_id: str, session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
    """处理流式响应"""
    server_logger.info(f"[{request_id}] 开始流式响应处理")
    
    try:
        # 获取当前模型并绑定工具
        current_model = model_manager.get_current_model()
        if not current_model:
            raise Exception("没有可用的模型")
        
        tool_chat = current_model.bind_tools(tools)
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
                
                # 保存助手响应到会话
                if session_id:
                    session_manager.add_message(session_id, "assistant", result.content)
                
                # 发送结束标记
                end_data = {
                    "type": "done",
                    "finish_reason": "stop",
                    "session_id": session_id
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
    global tool_map, tools
    
    tool_descriptions = get_tool_descriptions()
    available_tools = [
        ToolInfo(name=name, description=desc)
        for name, desc in tool_descriptions.items()
    ]
    
    sessions = session_manager.list_sessions(limit=1000)
    
    # 获取模型信息
    available_models_data = model_manager.get_available_models()
    available_models = [
        ModelInfo(
            name=model["name"],
            display_name=model["display_name"],
            provider=model["provider"],
            description=model["description"],
            is_current=model["is_current"],
            is_available=True  # 已经过筛选
        )
        for model in available_models_data
    ]
    
    current_config = model_manager.get_current_config()
    current_model_name = current_config.name if current_config else None
    
    return ServerStatus(
        status="running",
        current_model=current_model_name,
        available_models=available_models,
        tools_count=len(tools) if tools else 0,
        available_tools=available_tools,
        session_count=len(sessions)
    )

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """聊天端点"""
    current_model = model_manager.get_current_model()
    if not current_model:
        raise HTTPException(status_code=503, detail="没有可用的聊天模型，请先选择模型")
    
    request_id = f"req_{id(request)}"
    current_config = model_manager.get_current_config()
    server_logger.info(f"[{request_id}] 收到聊天请求，使用模型: {current_config.display_name}，会话ID: {request.session_id}")
    
    try:
        # 处理会话
        session_id = request.session_id
        if request.use_memory and not session_id:
            # 创建新会话
            session_id = session_manager.create_session(request.system_prompt)
            server_logger.info(f"[{request_id}] 创建新会话: {session_id}")
        
        # 保存用户消息到会话
        if session_id and request.messages:
            for msg in request.messages:
                if msg.role == "user":
                    session_manager.add_message(session_id, msg.role, msg.content)
        
        # 转换消息格式
        messages = convert_messages(request.messages, request.system_prompt, session_id if request.use_memory else None)
        
        if request.stream:
            # 流式响应
            server_logger.info(f"[{request_id}] 启用流式响应")
            return StreamingResponse(
                process_streaming_response(messages, request_id, session_id),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/plain; charset=utf-8",
                    "X-Session-ID": session_id or "",
                    "X-Model-Name": current_config.name
                }
            )
        else:
            # 非流式响应
            server_logger.info(f"[{request_id}] 非流式响应")
            tool_chat = current_model.bind_tools(tools)
            result = tool_chat.invoke(messages)
            
            # 保存助手响应到会话
            if session_id:
                tool_calls_data = getattr(result, 'tool_calls', [])
                session_manager.add_message(
                    session_id, 
                    "assistant", 
                    result.content,
                    tool_calls=tool_calls_data
                )
            
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

@app.post("/sessions", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """创建新会话"""
    try:
        session_id = session_manager.create_session(
            system_prompt=request.system_prompt or "",
            role_id=request.role_id,
            user_info=request.user_info
        )
        return SessionResponse(session_id=session_id)
    except Exception as e:
        server_logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions")
async def list_sessions(limit: int = 50):
    """获取会话列表"""
    sessions = session_manager.list_sessions(limit)
    return {"sessions": sessions}

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """获取会话详情"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "last_active": session.last_active,
        "system_prompt": session.system_prompt,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "tool_calls": msg.tool_calls,
                "tool_results": msg.tool_results
            }
            for msg in session.messages
        ]
    }

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"message": "会话已删除"}

@app.put("/sessions/{session_id}/system-prompt")
async def update_system_prompt(session_id: str, request: Dict[str, str]):
    """更新会话系统提示"""
    system_prompt = request.get("system_prompt", "")
    success = session_manager.update_system_prompt(session_id, system_prompt)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"message": "系统提示已更新"}

# 模型管理API
@app.get("/models")
async def get_models():
    """获取模型列表"""
    try:
        models = model_manager.get_available_models()
        current_config = model_manager.get_current_config()
        current_model = current_config.name if current_config else None
        
        return {
            "models": models,
            "current_model": current_model
        }
    except Exception as e:
        server_logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/models/switch")
async def switch_model(request: SwitchModelRequest):
    """切换模型"""
    try:
        success = model_manager.switch_model(request.name)
        if success:
            config = model_manager.get_current_config()
            return {
                "message": f"已切换到模型: {config.display_name}",
                "model_name": config.display_name,
                "provider": config.provider
            }
        else:
            raise HTTPException(status_code=400, detail="模型切换失败")
    except Exception as e:
        server_logger.error(f"切换模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/{model_name}")
async def get_model_info(model_name: str):
    """获取模型详细信息"""
    model_info = model_manager.get_model_info(model_name)
    if not model_info:
        raise HTTPException(status_code=404, detail="模型不存在")
    return model_info

# 存储管理API
@app.get("/storage")
async def get_storage_info():
    """获取存储信息"""
    return storage_mgr.get_storage_info()

@app.post("/storage/switch")
async def switch_storage(request: StorageConfigRequest):
    """切换存储后端"""
    try:
        config = StorageConfig(backend=request.backend, config=request.config)
        success = storage_mgr.switch_storage(config)
        
        if success:
            return {"message": f"已切换到存储后端: {request.backend}"}
        else:
            raise HTTPException(status_code=400, detail="存储后端切换失败")
            
    except Exception as e:
        server_logger.error(f"切换存储后端时出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/storage/cleanup")
async def cleanup_storage(days: int = 7):
    """清理过期数据"""
    try:
        cleaned_count = session_manager.cleanup_expired_sessions(days)
        return {"message": f"清理了 {cleaned_count} 个过期会话"}
    except Exception as e:
        server_logger.error(f"清理存储时出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 角色管理API
@app.get("/roles")
async def get_roles(category: Optional[str] = None, user_id: Optional[str] = None):
    """获取角色列表"""
    try:
        roles = role_manager.list_roles(category=category, user_id=user_id)
        return {
            "roles": [
                RoleResponse(
                    role_id=role.role_id,
                    name=role.name,
                    description=role.description,
                    system_prompt=role.system_prompt,
                    avatar=role.avatar,
                    category=role.category,
                    tags=role.tags,
                    created_at=role.created_at,
                    updated_at=role.updated_at,
                    is_system=role.is_system,
                    user_id=role.user_id
                ) for role in roles
            ],
            "categories": role_manager.get_categories()
        }
    except Exception as e:
        server_logger.error(f"获取角色列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/roles")
async def create_role(request: CreateRoleRequest):
    """创建新角色"""
    try:
        role = role_manager.create_role(
            name=request.name,
            description=request.description,
            system_prompt=request.system_prompt,
            avatar=request.avatar,
            category=request.category,
            tags=request.tags or []
        )
        
        return RoleResponse(
            role_id=role.role_id,
            name=role.name,
            description=role.description,
            system_prompt=role.system_prompt,
            avatar=role.avatar,
            category=role.category,
            tags=role.tags,
            created_at=role.created_at,
            updated_at=role.updated_at,
            is_system=role.is_system,
            user_id=role.user_id
        )
    except Exception as e:
        server_logger.error(f"创建角色失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/roles/{role_id}")
async def get_role(role_id: str):
    """获取角色详情"""
    role = role_manager.get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    return RoleResponse(
        role_id=role.role_id,
        name=role.name,
        description=role.description,
        system_prompt=role.system_prompt,
        avatar=role.avatar,
        category=role.category,
        tags=role.tags,
        created_at=role.created_at,
        updated_at=role.updated_at,
        is_system=role.is_system,
        user_id=role.user_id
    )

@app.put("/roles/{role_id}")
async def update_role(role_id: str, request: UpdateRoleRequest):
    """更新角色"""
    try:
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        success = role_manager.update_role(role_id, **update_data)
        
        if not success:
            raise HTTPException(status_code=404, detail="角色不存在或无法修改")
        
        updated_role = role_manager.get_role(role_id)
        return RoleResponse(
            role_id=updated_role.role_id,
            name=updated_role.name,
            description=updated_role.description,
            system_prompt=updated_role.system_prompt,
            avatar=updated_role.avatar,
            category=updated_role.category,
            tags=updated_role.tags,
            created_at=updated_role.created_at,
            updated_at=updated_role.updated_at,
            is_system=updated_role.is_system,
            user_id=updated_role.user_id
        )
    except Exception as e:
        server_logger.error(f"更新角色失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/roles/{role_id}")
async def delete_role(role_id: str):
    """删除角色"""
    try:
        success = role_manager.delete_role(role_id)
        if not success:
            raise HTTPException(status_code=404, detail="角色不存在或无法删除")
        
        return {"message": "角色删除成功"}
    except Exception as e:
        server_logger.error(f"删除角色失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/roles/search/{query}")
async def search_roles(query: str):
    """搜索角色"""
    try:
        roles = role_manager.search_roles(query)
        return {
            "query": query,
            "roles": [
                RoleResponse(
                    role_id=role.role_id,
                    name=role.name,
                    description=role.description,
                    system_prompt=role.system_prompt,
                    avatar=role.avatar,
                    category=role.category,
                    tags=role.tags,
                    created_at=role.created_at,
                    updated_at=role.updated_at,
                    is_system=role.is_system,
                    user_id=role.user_id
                ) for role in roles
            ]
        }
    except Exception as e:
        server_logger.error(f"搜索角色失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/roles/info")
async def get_roles_info():
    """获取角色管理信息"""
    return role_manager.get_storage_info()

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

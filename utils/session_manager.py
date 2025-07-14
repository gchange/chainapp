"""会话管理器"""

import json
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from utils.logger import setup_logger

# 设置会话管理器logger
session_logger = setup_logger("session_manager")

@dataclass
class ChatMessage:
    """聊天消息数据类"""
    role: str
    content: str
    timestamp: float
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None

@dataclass
class ChatSession:
    """聊天会话数据类"""
    session_id: str
    created_at: float
    last_active: float
    messages: List[ChatMessage]
    system_prompt: str
    user_info: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "messages": [asdict(msg) for msg in self.messages],
            "system_prompt": self.system_prompt,
            "user_info": self.user_info
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        """从字典创建"""
        messages = [
            ChatMessage(**msg_data) for msg_data in data.get("messages", [])
        ]
        return cls(
            session_id=data["session_id"],
            created_at=data["created_at"],
            last_active=data["last_active"],
            messages=messages,
            system_prompt=data.get("system_prompt", ""),
            user_info=data.get("user_info")
        )

class SessionManager:
    """会话管理器"""
    
    def __init__(self, storage_dir: str = "sessions", max_sessions: int = 1000):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.max_sessions = max_sessions
        self.sessions: Dict[str, ChatSession] = {}
        self.load_sessions()
        session_logger.info(f"会话管理器初始化完成，存储目录: {self.storage_dir}")
    
    def create_session(self, system_prompt: str = "", user_info: Optional[Dict[str, Any]] = None) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        current_time = time.time()
        
        session = ChatSession(
            session_id=session_id,
            created_at=current_time,
            last_active=current_time,
            messages=[],
            system_prompt=system_prompt,
            user_info=user_info
        )
        
        self.sessions[session_id] = session
        self.save_session(session_id)
        
        session_logger.info(f"创建新会话: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.last_active = time.time()
            return session
        
        # 尝试从文件加载
        session_file = self.storage_dir / f"{session_id}.json"
        if session_file.exists():
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                session = ChatSession.from_dict(data)
                session.last_active = time.time()
                self.sessions[session_id] = session
                session_logger.info(f"从文件加载会话: {session_id}")
                return session
            except Exception as e:
                session_logger.error(f"加载会话文件失败 {session_id}: {e}")
        
        return None
    
    def add_message(self, session_id: str, role: str, content: str, 
                   tool_calls: Optional[List[Dict[str, Any]]] = None,
                   tool_results: Optional[List[Dict[str, Any]]] = None) -> bool:
        """添加消息到会话"""
        session = self.get_session(session_id)
        if not session:
            session_logger.warning(f"会话不存在: {session_id}")
            return False
        
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=time.time(),
            tool_calls=tool_calls,
            tool_results=tool_results
        )
        
        session.messages.append(message)
        session.last_active = time.time()
        
        # 限制消息数量（保留最近的100条消息）
        if len(session.messages) > 100:
            session.messages = session.messages[-100:]
            session_logger.info(f"会话 {session_id} 消息数量达到上限，保留最近100条")
        
        self.save_session(session_id)
        session_logger.debug(f"添加消息到会话 {session_id}: {role}")
        return True
    
    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        """获取会话消息"""
        session = self.get_session(session_id)
        if not session:
            return []
        
        messages = session.messages
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def update_system_prompt(self, session_id: str, system_prompt: str) -> bool:
        """更新系统提示"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.system_prompt = system_prompt
        session.last_active = time.time()
        self.save_session(session_id)
        session_logger.info(f"更新会话 {session_id} 系统提示")
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        session_file = self.storage_dir / f"{session_id}.json"
        if session_file.exists():
            try:
                session_file.unlink()
                session_logger.info(f"删除会话: {session_id}")
                return True
            except Exception as e:
                session_logger.error(f"删除会话文件失败 {session_id}: {e}")
                return False
        
        return True
    
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出会话"""
        # 获取所有会话文件
        all_sessions = []
        
        # 内存中的会话
        for session in self.sessions.values():
            all_sessions.append({
                "session_id": session.session_id,
                "created_at": session.created_at,
                "last_active": session.last_active,
                "message_count": len(session.messages),
                "system_prompt": session.system_prompt[:100] + "..." if len(session.system_prompt) > 100 else session.system_prompt
            })
        
        # 文件中的会话
        for session_file in self.storage_dir.glob("*.json"):
            session_id = session_file.stem
            if session_id not in self.sessions:
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    all_sessions.append({
                        "session_id": data["session_id"],
                        "created_at": data["created_at"],
                        "last_active": data["last_active"],
                        "message_count": len(data.get("messages", [])),
                        "system_prompt": data.get("system_prompt", "")[:100] + "..." if len(data.get("system_prompt", "")) > 100 else data.get("system_prompt", "")
                    })
                except Exception as e:
                    session_logger.error(f"读取会话文件失败 {session_file}: {e}")
        
        # 按最后活跃时间排序
        all_sessions.sort(key=lambda x: x["last_active"], reverse=True)
        return all_sessions[:limit]
    
    def save_session(self, session_id: str) -> bool:
        """保存会话到文件"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session_file = self.storage_dir / f"{session_id}.json"
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            session_logger.error(f"保存会话失败 {session_id}: {e}")
            return False
    
    def load_sessions(self) -> None:
        """加载所有会话文件（仅加载基本信息）"""
        session_files = list(self.storage_dir.glob("*.json"))
        session_logger.info(f"发现 {len(session_files)} 个会话文件")
        
        # 清理过期会话（7天未活跃）
        current_time = time.time()
        expired_threshold = current_time - (7 * 24 * 60 * 60)  # 7天
        
        for session_file in session_files:
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                last_active = data.get("last_active", 0)
                if last_active < expired_threshold:
                    session_file.unlink()
                    session_logger.info(f"删除过期会话: {data.get('session_id', 'unknown')}")
                    
            except Exception as e:
                session_logger.error(f"处理会话文件失败 {session_file}: {e}")
    
    def clear_old_sessions(self) -> None:
        """清理旧会话"""
        if len(self.sessions) > self.max_sessions:
            # 按最后活跃时间排序，删除最旧的会话
            sorted_sessions = sorted(
                self.sessions.items(),
                key=lambda x: x[1].last_active
            )
            
            sessions_to_remove = sorted_sessions[:len(self.sessions) - self.max_sessions]
            for session_id, _ in sessions_to_remove:
                self.delete_session(session_id)
            
            session_logger.info(f"清理了 {len(sessions_to_remove)} 个旧会话")

# 全局会话管理器实例
session_manager = SessionManager()
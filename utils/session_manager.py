"""会话管理器 - 使用存储管理器"""

import time
import uuid
from typing import Dict, List, Optional, Any
from utils.logger import setup_logger
from storage.storage_manager import storage_manager, ChatSession, ChatMessage

# 设置会话管理器logger
session_logger = setup_logger("session_manager")

class SessionManager:
    """会话管理器 - 使用存储抽象层"""
    
    def __init__(self, max_sessions: int = 1000):
        self.max_sessions = max_sessions
        self.sessions_cache: Dict[str, ChatSession] = {}  # 内存缓存
        
        # 清理过期会话
        self.cleanup_expired_sessions()
        session_logger.info("会话管理器初始化完成")
    
    def create_session(self, system_prompt: str = "", role_id: Optional[str] = None, user_info: Optional[Dict[str, Any]] = None) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        current_time = time.time()
        
        # 如果指定了角色ID，从角色管理器获取系统提示
        if role_id:
            from roles.role_manager import role_manager
            role = role_manager.get_role(role_id)
            if role:
                system_prompt = role.system_prompt
                if not user_info:
                    user_info = {}
                user_info["role_id"] = role_id
                user_info["role_name"] = role.name
        
        session = ChatSession(
            session_id=session_id,
            created_at=current_time,
            last_active=current_time,
            messages=[],
            system_prompt=system_prompt,
            user_info=user_info
        )
        
        # 保存到存储后端
        if storage_manager.save_session(session):
            self.sessions_cache[session_id] = session
            session_logger.info(f"创建新会话: {session_id}, 角色: {role_id or '默认'}")
            return session_id
        else:
            session_logger.error(f"创建会话失败: {session_id}")
            raise Exception("创建会话失败")
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话"""
        # 先从缓存中获取
        if session_id in self.sessions_cache:
            session = self.sessions_cache[session_id]
            session.last_active = time.time()
            return session
        
        # 从存储后端加载
        session = storage_manager.load_session(session_id)
        if session:
            session.last_active = time.time()
            self.sessions_cache[session_id] = session
            session_logger.debug(f"从存储加载会话: {session_id}")
            return session
        
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
        
        # 保存到存储后端
        if storage_manager.save_session(session):
            session_logger.debug(f"添加消息到会话{session_id}: {role}")
            return True
        else:
            session_logger.error(f"保存会话失败: {session_id}")
            return False
    
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
        
        if storage_manager.save_session(session):
            session_logger.info(f"更新会话 {session_id} 系统提示")
            return True
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        # 从缓存中删除
        if session_id in self.sessions_cache:
            del self.sessions_cache[session_id]
        
        # 从存储后端删除
        if storage_manager.delete_session(session_id):
            session_logger.info(f"删除会话: {session_id}")
            return True
        return False
    
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出会话"""
        return storage_manager.list_sessions(limit)
    
    def cleanup_expired_sessions(self, days: int = 7) -> int:
        """清理过期会话"""
        cleaned_count = storage_manager.cleanup_expired_sessions(days)
        # 清理缓存中的过期会话
        current_time = time.time()
        expired_threshold = current_time - (days * 24 * 60 * 60)
        
        expired_cache_sessions = [
            session_id for session_id, session in self.sessions_cache.items()
            if session.last_active < expired_threshold
        ]
        
        for session_id in expired_cache_sessions:
            del self.sessions_cache[session_id]
        
        return cleaned_count

# 全局会话管理器实例
session_manager = SessionManager()
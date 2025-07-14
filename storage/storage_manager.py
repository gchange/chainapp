"""存储管理器 - 支持多种存储后端"""

import json
import time
import uuid
from typing import Dict, List, Optional, Any, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from utils.logger import setup_logger

# 设置存储管理器logger
storage_logger = setup_logger("storage_manager")

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

@dataclass
class StorageConfig:
    """存储配置"""
    backend: str  # "file", "mongodb", "redis", "sqlite"
    config: Dict[str, Any]

class BaseStorage(ABC):
    """存储后端基类"""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化存储后端"""
        pass
    
    @abstractmethod
    def save_session(self, session: ChatSession) -> bool:
        """保存会话"""
        pass
    
    @abstractmethod
    def load_session(self, session_id: str) -> Optional[ChatSession]:
        """加载会话"""
        pass
    
    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        pass
    
    @abstractmethod
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出会话"""
        pass
    
    @abstractmethod
    def cleanup_expired_sessions(self, days: int = 7) -> int:
        """清理过期会话，返回清理数量"""
        pass
    
    @abstractmethod
    def get_session_count(self) -> int:
        """获取会话总数"""
        pass

class FileStorage(BaseStorage):
    """文件存储后端"""
    
    def __init__(self):
        self.storage_dir: Optional[Path] = None
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化文件存储"""
        try:
            storage_dir = config.get("directory", "sessions")
            self.storage_dir = Path(storage_dir)
            self.storage_dir.mkdir(exist_ok=True)
            
            storage_logger.info(f"文件存储初始化完成，目录: {self.storage_dir}")
            return True
        except Exception as e:
            storage_logger.error(f"文件存储初始化失败: {e}")
            return False
    
    def save_session(self, session: ChatSession) -> bool:
        """保存会话到文件"""
        if not self.storage_dir:
            return False
            
        try:
            session_file = self.storage_dir / f"{session.session_id}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            storage_logger.error(f"保存会话失败 {session.session_id}: {e}")
            return False
    
    def load_session(self, session_id: str) -> Optional[ChatSession]:
        """从文件加载会话"""
        if not self.storage_dir:
            return None
            
        session_file = self.storage_dir / f"{session_id}.json"
        if not session_file.exists():
            return None
            
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ChatSession.from_dict(data)
        except Exception as e:
            storage_logger.error(f"加载会话失败 {session_id}: {e}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话文件"""
        if not self.storage_dir:
            return False
            
        session_file = self.storage_dir / f"{session_id}.json"
        if session_file.exists():
            try:
                session_file.unlink()
                return True
            except Exception as e:
                storage_logger.error(f"删除会话文件失败 {session_id}: {e}")
                return False
        return True
    
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出会话文件"""
        if not self.storage_dir:
            return []
            
        sessions = []
        try:
            for session_file in self.storage_dir.glob("*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    sessions.append({
                        "session_id": data["session_id"],
                        "created_at": data["created_at"],
                        "last_active": data["last_active"],
                        "message_count": len(data.get("messages", [])),
                        "system_prompt": data.get("system_prompt", "")[:100] + "..." if len(data.get("system_prompt", "")) > 100 else data.get("system_prompt", "")
                    })
                except Exception as e:
                    storage_logger.error(f"读取会话文件失败 {session_file}: {e}")
            
            # 按最后活跃时间排序
            sessions.sort(key=lambda x: x["last_active"], reverse=True)
            return sessions[:limit]
            
        except Exception as e:
            storage_logger.error(f"列出会话失败: {e}")
            return []
    
    def cleanup_expired_sessions(self, days: int = 7) -> int:
        """清理过期会话文件"""
        if not self.storage_dir:
            return 0
            
        current_time = time.time()
        expired_threshold = current_time - (days * 24 * 60 * 60)
        cleaned_count = 0
        
        try:
            for session_file in self.storage_dir.glob("*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    last_active = data.get("last_active", 0)
                    if last_active < expired_threshold:
                        session_file.unlink()
                        cleaned_count += 1
                        storage_logger.info(f"删除过期会话: {data.get('session_id', 'unknown')}")
                        
                except Exception as e:
                    storage_logger.error(f"处理会话文件失败 {session_file}: {e}")
                    
        except Exception as e:
            storage_logger.error(f"清理过期会话失败: {e}")
            
        return cleaned_count
    
    def get_session_count(self) -> int:
        """获取会话总数"""
        if not self.storage_dir:
            return 0
        try:
            return len(list(self.storage_dir.glob("*.json")))
        except:
            return 0

class MongoStorage(BaseStorage):
    """MongoDB存储后端"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化MongoDB存储"""
        try:
            # 延迟导入，避免强制依赖
            from pymongo import MongoClient
            
            connection_string = config.get("connection_string", "mongodb://localhost:27017/")
            database_name = config.get("database", "chatapp")
            collection_name = config.get("collection", "sessions")
            
            self.client = MongoClient(connection_string)
            self.db = self.client[database_name]
            self.collection = self.db[collection_name]
            
            # 创建索引
            self.collection.create_index("session_id", unique=True)
            self.collection.create_index("last_active")
            
            storage_logger.info(f"MongoDB存储初始化完成，数据库: {database_name}")
            return True
            
        except ImportError:
            storage_logger.error("MongoDB存储需要安装 pymongo: pip install pymongo")
            return False
        except Exception as e:
            storage_logger.error(f"MongoDB存储初始化失败: {e}")
            return False
    
    def save_session(self, session: ChatSession) -> bool:
        """保存会话到MongoDB"""
        if not self.collection:
            return False
            
        try:
            session_data = session.to_dict()
            self.collection.replace_one(
                {"session_id": session.session_id},
                session_data,
                upsert=True
            )
            return True
        except Exception as e:
            storage_logger.error(f"保存会话失败 {session.session_id}: {e}")
            return False
    
    def load_session(self, session_id: str) -> Optional[ChatSession]:
        """从MongoDB加载会话"""
        if not self.collection:
            return None
            
        try:
            data = self.collection.find_one({"session_id": session_id})
            if data:
                data.pop('_id', None)  # 移除MongoDB的_id字段
                return ChatSession.from_dict(data)
            return None
        except Exception as e:
            storage_logger.error(f"加载会话失败 {session_id}: {e}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """从MongoDB删除会话"""
        if not self.collection:
            return False
            
        try:
            result = self.collection.delete_one({"session_id": session_id})
            return result.deleted_count > 0
        except Exception as e:
            storage_logger.error(f"删除会话失败 {session_id}: {e}")
            return False
    
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """从MongoDB列出会话"""
        if not self.collection:
            return []
            
        try:
            sessions = []
            cursor = self.collection.find(
                {},
                {
                    "session_id": 1,
                    "created_at": 1,
                    "last_active": 1,
                    "system_prompt": 1,
                    "messages": {"$size": "$messages"}
                }
            ).sort("last_active", -1).limit(limit)
            
            for doc in cursor:
                doc.pop('_id', None)
                doc["message_count"] = doc.pop("messages", 0)
                system_prompt = doc.get("system_prompt", "")
                if len(system_prompt) > 100:
                    doc["system_prompt"] = system_prompt[:100] + "..."
                sessions.append(doc)
                
            return sessions
            
        except Exception as e:
            storage_logger.error(f"列出会话失败: {e}")
            return []
    
    def cleanup_expired_sessions(self, days: int = 7) -> int:
        """清理MongoDB中的过期会话"""
        if not self.collection:
            return 0
            
        try:
            current_time = time.time()
            expired_threshold = current_time - (days * 24 * 60 * 60)
            
            result = self.collection.delete_many({
                "last_active": {"$lt": expired_threshold}
            })
            
            cleaned_count = result.deleted_count
            storage_logger.info(f"清理了 {cleaned_count} 个过期会话")
            return cleaned_count
            
        except Exception as e:
            storage_logger.error(f"清理过期会话失败: {e}")
            return 0
    
    def get_session_count(self) -> int:
        """获取MongoDB中的会话总数"""
        if not self.collection:
            return 0
        try:
            return self.collection.count_documents({})
        except:
            return 0

class SQLiteStorage(BaseStorage):
    """SQLite存储后端"""
    
    def __init__(self):
        self.db_path = None
        self.connection = None
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化SQLite存储"""
        try:
            import sqlite3
            
            self.db_path = config.get("database_path", "sessions.db")
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            
            # 创建表
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at REAL,
                    last_active REAL,
                    system_prompt TEXT,
                    user_info TEXT,
                    messages TEXT
                )
            """)
            
            # 创建索引
            self.connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_active ON sessions(last_active)
            """)
            
            self.connection.commit()
            
            storage_logger.info(f"SQLite存储初始化完成，数据库: {self.db_path}")
            return True
            
        except Exception as e:
            storage_logger.error(f"SQLite存储初始化失败: {e}")
            return False
    
    def save_session(self, session: ChatSession) -> bool:
        """保存会话到SQLite"""
        if not self.connection:
            return False
            
        try:
            session_data = session.to_dict()
            messages_json = json.dumps(session_data["messages"], ensure_ascii=False)
            user_info_json = json.dumps(session_data["user_info"]) if session_data["user_info"] else None
            
            self.connection.execute("""
                INSERT OR REPLACE INTO sessions 
                (session_id, created_at, last_active, system_prompt, user_info, messages)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.created_at,
                session.last_active,
                session.system_prompt,
                user_info_json,
                messages_json
            ))
            
            self.connection.commit()
            return True
            
        except Exception as e:
            storage_logger.error(f"保存会话失败 {session.session_id}: {e}")
            return False
    
    def load_session(self, session_id: str) -> Optional[ChatSession]:
        """从SQLite加载会话"""
        if not self.connection:
            return None
            
        try:
            cursor = self.connection.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            
            if row:
                messages = json.loads(row["messages"]) if row["messages"] else []
                user_info = json.loads(row["user_info"]) if row["user_info"] else None
                
                session_data = {
                    "session_id": row["session_id"],
                    "created_at": row["created_at"],
                    "last_active": row["last_active"],
                    "system_prompt": row["system_prompt"] or "",
                    "user_info": user_info,
                    "messages": messages
                }
                
                return ChatSession.from_dict(session_data)
                
            return None
            
        except Exception as e:
            storage_logger.error(f"加载会话失败 {session_id}: {e}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """从SQLite删除会话"""
        if not self.connection:
            return False
            
        try:
            cursor = self.connection.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            self.connection.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            storage_logger.error(f"删除会话失败 {session_id}: {e}")
            return False
    
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """从SQLite列出会话"""
        if not self.connection:
            return []
            
        try:
            cursor = self.connection.execute("""
                SELECT session_id, created_at, last_active, system_prompt, messages
                FROM sessions
                ORDER BY last_active DESC
                LIMIT ?
            """, (limit,))
            
            sessions = []
            for row in cursor:
                messages = json.loads(row["messages"]) if row["messages"] else []
                system_prompt = row["system_prompt"] or ""
                
                sessions.append({
                    "session_id": row["session_id"],
                    "created_at": row["created_at"],
                    "last_active": row["last_active"],
                    "message_count": len(messages),
                    "system_prompt": system_prompt[:100] + "..." if len(system_prompt) > 100 else system_prompt
                })
                
            return sessions
            
        except Exception as e:
            storage_logger.error(f"列出会话失败: {e}")
            return []
    
    def cleanup_expired_sessions(self, days: int = 7) -> int:
        """清理SQLite中的过期会话"""
        if not self.connection:
            return 0
            
        try:
            current_time = time.time()
            expired_threshold = current_time - (days * 24 * 60 * 60)
            
            cursor = self.connection.execute(
                "DELETE FROM sessions WHERE last_active < ?",
                (expired_threshold,)
            )
            self.connection.commit()
            
            cleaned_count = cursor.rowcount
            storage_logger.info(f"清理了 {cleaned_count} 个过期会话")
            return cleaned_count
            
        except Exception as e:
            storage_logger.error(f"清理过期会话失败: {e}")
            return 0
    
    def get_session_count(self) -> int:
        """获取SQLite中的会话总数"""
        if not self.connection:
            return 0
        try:
            cursor = self.connection.execute("SELECT COUNT(*) FROM sessions")
            return cursor.fetchone()[0]
        except:
            return 0

class StorageManager:
    """存储管理器"""
    
    def __init__(self):
        self.storage_backends: Dict[str, Type[BaseStorage]] = {
            "file": FileStorage,
            "mongodb": MongoStorage,
            "sqlite": SQLiteStorage,
        }
        
        self.current_storage: Optional[BaseStorage] = None
        self.current_config: Optional[StorageConfig] = None
        
        # 默认配置
        default_config = StorageConfig(
            backend="file",
            config={"directory": "sessions"}
        )
        
        self.initialize_storage(default_config)
        
    def initialize_storage(self, config: StorageConfig) -> bool:
        """初始化存储后端"""
        try:
            if config.backend not in self.storage_backends:
                storage_logger.error(f"不支持的存储后端: {config.backend}")
                return False
            
            storage_class = self.storage_backends[config.backend]
            storage_instance = storage_class()
            
            if storage_instance.initialize(config.config):
                self.current_storage = storage_instance
                self.current_config = config
                storage_logger.info(f"存储后端初始化成功: {config.backend}")
                return True
            else:
                storage_logger.error(f"存储后端初始化失败: {config.backend}")
                return False
                
        except Exception as e:
            storage_logger.error(f"初始化存储后端时出错: {e}")
            return False
    
    def switch_storage(self, config: StorageConfig) -> bool:
        """切换存储后端"""
        return self.initialize_storage(config)
    
    def save_session(self, session: ChatSession) -> bool:
        """保存会话"""
        if not self.current_storage:
            return False
        return self.current_storage.save_session(session)
    
    def load_session(self, session_id: str) -> Optional[ChatSession]:
        """加载会话"""
        if not self.current_storage:
            return None
        return self.current_storage.load_session(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if not self.current_storage:
            return False
        return self.current_storage.delete_session(session_id)
    
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出会话"""
        if not self.current_storage:
            return []
        return self.current_storage.list_sessions(limit)
    
    def cleanup_expired_sessions(self, days: int = 7) -> int:
        """清理过期会话"""
        if not self.current_storage:
            return 0
        return self.current_storage.cleanup_expired_sessions(days)
    
    def get_session_count(self) -> int:
        """获取会话总数"""
        if not self.current_storage:
            return 0
        return self.current_storage.get_session_count()
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        return {
            "backend": self.current_config.backend if self.current_config else None,
            "config": self.current_config.config if self.current_config else {},
            "session_count": self.get_session_count(),
            "available_backends": list(self.storage_backends.keys())
        }

# 全局存储管理器实例
storage_manager = StorageManager()
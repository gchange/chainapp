"""角色管理器 - 支持多种存储后端"""

import json
import time
import uuid
from typing import Dict, List, Optional, Any, Type
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from pathlib import Path
from utils.logger import setup_logger

# 设置角色管理器logger
role_logger = setup_logger("role_manager")

@dataclass
class RoleConfig:
    """角色配置"""
    role_id: str
    name: str
    description: str
    system_prompt: str
    avatar: str = "🤖"
    category: str = "通用"
    tags: List[str] = None
    created_at: float = 0
    updated_at: float = 0
    is_system: bool = False  # 是否为系统内置角色
    user_id: Optional[str] = None  # 创建者ID
    default_model: Optional[str] = None  # 默认使用的模型名称
    model_config: Optional[Dict[str, Any]] = None  # 模型特定配置
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at == 0:
            self.created_at = time.time()
        if self.updated_at == 0:
            self.updated_at = time.time()
        if self.model_config is None:
            self.model_config = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RoleConfig':
        """从字典创建"""
        return cls(**data)

class BaseRoleStorage(ABC):
    """角色存储后端基类"""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化存储后端"""
        pass
    
    @abstractmethod
    def save_role(self, role: RoleConfig) -> bool:
        """保存角色"""
        pass
    
    @abstractmethod
    def load_role(self, role_id: str) -> Optional[RoleConfig]:
        """加载角色"""
        pass
    
    @abstractmethod
    def delete_role(self, role_id: str) -> bool:
        """删除角色"""
        pass
    
    @abstractmethod
    def list_roles(self, category: Optional[str] = None, user_id: Optional[str] = None) -> List[RoleConfig]:
        """列出角色"""
        pass
    
    @abstractmethod
    def search_roles(self, query: str) -> List[RoleConfig]:
        """搜索角色"""
        pass

class FileRoleStorage(BaseRoleStorage):
    """文件角色存储后端"""
    
    def __init__(self):
        self.storage_dir: Optional[Path] = None
        
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化文件存储"""
        try:
            storage_dir = config.get("directory", "roles")
            self.storage_dir = Path(storage_dir)
            self.storage_dir.mkdir(exist_ok=True)
            
            role_logger.info(f"文件角色存储初始化完成，目录: {self.storage_dir}")
            return True
        except Exception as e:
            role_logger.error(f"文件角色存储初始化失败: {e}")
            return False
    
    def save_role(self, role: RoleConfig) -> bool:
        """保存角色到文件"""
        if not self.storage_dir:
            return False
            
        try:
            role_file = self.storage_dir / f"{role.role_id}.json"
            role.updated_at = time.time()
            with open(role_file, 'w', encoding='utf-8') as f:
                json.dump(role.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            role_logger.error(f"保存角色失败 {role.role_id}: {e}")
            return False
    
    def load_role(self, role_id: str) -> Optional[RoleConfig]:
        """从文件加载角色"""
        if not self.storage_dir:
            return None
            
        role_file = self.storage_dir / f"{role_id}.json"
        if not role_file.exists():
            return None
            
        try:
            with open(role_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return RoleConfig.from_dict(data)
        except Exception as e:
            role_logger.error(f"加载角色失败 {role_id}: {e}")
            return None
    
    def delete_role(self, role_id: str) -> bool:
        """删除角色文件"""
        if not self.storage_dir:
            return False
            
        role_file = self.storage_dir / f"{role_id}.json"
        if role_file.exists():
            try:
                role_file.unlink()
                return True
            except Exception as e:
                role_logger.error(f"删除角色文件失败 {role_id}: {e}")
                return False
        return True
    
    def list_roles(self, category: Optional[str] = None, user_id: Optional[str] = None) -> List[RoleConfig]:
        """列出角色文件"""
        if not self.storage_dir:
            return []
            
        roles = []
        try:
            for role_file in self.storage_dir.glob("*.json"):
                try:
                    with open(role_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    role = RoleConfig.from_dict(data)
                    
                    # 过滤条件
                    if category and role.category != category:
                        continue
                    if user_id and role.user_id != user_id:
                        continue
                        
                    roles.append(role)
                except Exception as e:
                    role_logger.error(f"读取角色文件失败 {role_file}: {e}")
            
            # 按更新时间排序
            roles.sort(key=lambda x: x.updated_at, reverse=True)
            return roles
            
        except Exception as e:
            role_logger.error(f"列出角色失败: {e}")
            return []
    
    def search_roles(self, query: str) -> List[RoleConfig]:
        """搜索角色"""
        query = query.lower()
        all_roles = self.list_roles()
        
        matching_roles = []
        for role in all_roles:
            if (query in role.name.lower() or 
                query in role.description.lower() or 
                any(query in tag.lower() for tag in role.tags)):
                matching_roles.append(role)
        
        return matching_roles

class MongoRoleStorage(BaseRoleStorage):
    """MongoDB角色存储后端"""
    
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
            collection_name = config.get("collection", "roles")
            
            self.client = MongoClient(connection_string)
            self.db = self.client[database_name]
            self.collection = self.db[collection_name]
            
            # 创建索引
            self.collection.create_index("role_id", unique=True)
            self.collection.create_index("category")
            self.collection.create_index("user_id")
            self.collection.create_index("tags")
            self.collection.create_index([("name", "text"), ("description", "text")])
            
            role_logger.info(f"MongoDB角色存储初始化完成，数据库: {database_name}")
            return True
            
        except ImportError:
            role_logger.error("MongoDB存储需要安装 pymongo: pip install pymongo")
            return False
        except Exception as e:
            role_logger.error(f"MongoDB角色存储初始化失败: {e}")
            return False
    
    def save_role(self, role: RoleConfig) -> bool:
        """保存角色到MongoDB"""
        if not self.collection:
            return False
            
        try:
            role.updated_at = time.time()
            role_data = role.to_dict()
            self.collection.replace_one(
                {"role_id": role.role_id},
                role_data,
                upsert=True
            )
            return True
        except Exception as e:
            role_logger.error(f"保存角色失败 {role.role_id}: {e}")
            return False
    
    def load_role(self, role_id: str) -> Optional[RoleConfig]:
        """从MongoDB加载角色"""
        if not self.collection:
            return None
            
        try:
            data = self.collection.find_one({"role_id": role_id})
            if data:
                data.pop('_id', None)  # 移除MongoDB的_id字段
                return RoleConfig.from_dict(data)
            return None
        except Exception as e:
            role_logger.error(f"加载角色失败 {role_id}: {e}")
            return None
    
    def delete_role(self, role_id: str) -> bool:
        """从MongoDB删除角色"""
        if not self.collection:
            return False
            
        try:
            result = self.collection.delete_one({"role_id": role_id})
            return result.deleted_count > 0
        except Exception as e:
            role_logger.error(f"删除角色失败 {role_id}: {e}")
            return False
    
    def list_roles(self, category: Optional[str] = None, user_id: Optional[str] = None) -> List[RoleConfig]:
        """从MongoDB列出角色"""
        if not self.collection:
            return []
            
        try:
            query = {}
            if category:
                query["category"] = category
            if user_id:
                query["user_id"] = user_id
                
            cursor = self.collection.find(query).sort("updated_at", -1)
            
            roles = []
            for doc in cursor:
                doc.pop('_id', None)
                roles.append(RoleConfig.from_dict(doc))
                
            return roles
            
        except Exception as e:
            role_logger.error(f"列出角色失败: {e}")
            return []
    
    def search_roles(self, query: str) -> List[RoleConfig]:
        """搜索MongoDB中的角色"""
        if not self.collection:
            return []
            
        try:
            # 使用文本搜索
            cursor = self.collection.find({
                "$or": [
                    {"$text": {"$search": query}},
                    {"tags": {"$regex": query, "$options": "i"}}
                ]
            }).sort("updated_at", -1)
            
            roles = []
            for doc in cursor:
                doc.pop('_id', None)
                roles.append(RoleConfig.from_dict(doc))
                
            return roles
            
        except Exception as e:
            role_logger.error(f"搜索角色失败: {e}")
            return []

class RoleManager:
    """角色管理器"""
    
    def __init__(self):
        self.storage_backends: Dict[str, Type[BaseRoleStorage]] = {
            "file": FileRoleStorage,
            "mongodb": MongoRoleStorage,
        }
        
        self.current_storage: Optional[BaseRoleStorage] = None
        self.current_backend: str = "file"
        
        # 默认使用文件存储
        self.initialize_storage("file", {"directory": "roles"})
        
        # 初始化系统角色
        self.init_system_roles()
        
    def initialize_storage(self, backend: str, config: Dict[str, Any]) -> bool:
        """初始化存储后端"""
        try:
            if backend not in self.storage_backends:
                role_logger.error(f"不支持的存储后端: {backend}")
                return False
            
            storage_class = self.storage_backends[backend]
            storage_instance = storage_class()
            
            if storage_instance.initialize(config):
                self.current_storage = storage_instance
                self.current_backend = backend
                role_logger.info(f"角色存储后端初始化成功: {backend}")
                return True
            else:
                role_logger.error(f"角色存储后端初始化失败: {backend}")
                return False
                
        except Exception as e:
            role_logger.error(f"初始化角色存储后端时出错: {e}")
            return False
    
    def init_system_roles(self) -> None:
        """初始化系统内置角色"""
        system_roles = [
            RoleConfig(
                role_id="default",
                name="默认助手",
                description="通用智能助手，可以回答各种问题并执行工具",
                system_prompt="你是一个有用的AI助手，可以回答用户的问题并使用提供的工具来帮助用户完成任务。",
                avatar="🤖",
                category="通用",
                tags=["默认", "通用", "助手"],
                is_system=True,
                default_model="gpt-4o-mini",
                model_config={
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "top_p": 0.9
                }
            ),
            RoleConfig(
                role_id="ikun",
                name="iKun",
                description="会唱、跳、rap、篮球的智能助手",
                system_prompt="你的名字是iKun，擅长唱、跳、rap、打篮球，你的回答里面总是带着这些元素。你是一个活泼、有趣、充满活力的助手。",
                avatar="🏀",
                category="娱乐",
                tags=["iKun", "娱乐", "活泼", "篮球"],
                is_system=True,
                default_model="gpt-4o-mini",
                model_config={
                    "temperature": 0.9,
                    "max_tokens": 3000,
                    "top_p": 0.95
                }
            ),
            RoleConfig(
                role_id="programmer",
                name="程序员助手",
                description="专业的编程助手，擅长代码编写和技术问题解答",
                system_prompt="你是一个专业的编程助手，精通多种编程语言和技术框架。你可以帮助用户编写代码、调试问题、解释技术概念，并提供最佳实践建议。",
                avatar="👨‍💻",
                category="技术",
                tags=["编程", "开发", "技术", "代码"],
                is_system=True,
                default_model="claude-3-5-sonnet-20241022",
                model_config={
                    "temperature": 0.3,
                    "max_tokens": 8000,
                    "top_p": 0.8
                }
            ),
            RoleConfig(
                role_id="translator",
                name="翻译专家",
                description="专业的多语言翻译助手",
                system_prompt="你是一个专业的翻译专家，精通多种语言之间的翻译。你会提供准确、自然、符合语境的翻译，并能解释语言细节和文化差异。",
                avatar="🌍",
                category="语言",
                tags=["翻译", "语言", "多语言"],
                is_system=True,
                default_model="gpt-4o",
                model_config={
                    "temperature": 0.3,
                    "max_tokens": 4000,
                    "top_p": 0.8
                }
            ),
            RoleConfig(
                role_id="teacher",
                name="教学助手",
                description="耐心的教学助手，擅长解释复杂概念",
                system_prompt="你是一个耐心的教学助手，擅长用简单易懂的方式解释复杂的概念。你会根据用户的理解水平调整解释方式，并提供相关的例子和练习。",
                avatar="👨‍🏫",
                category="教育",
                tags=["教学", "教育", "解释", "学习"],
                is_system=True,
                default_model="claude-3-5-sonnet-20241022",
                model_config={
                    "temperature": 0.5,
                    "max_tokens": 6000,
                    "top_p": 0.85
                }
            ),
            RoleConfig(
                role_id="creative_writer",
                name="创意写手",
                description="富有创意的写作助手",
                system_prompt="你是一个富有创意的写作助手，擅长创作各种类型的文字内容，包括故事、诗歌、文章等。你有丰富的想象力和优秀的文字表达能力。",
                avatar="✍️",
                category="创作",
                tags=["写作", "创意", "文学", "创作"],
                is_system=True,
                default_model="claude-3-5-sonnet-20241022",
                model_config={
                    "temperature": 0.8,
                    "max_tokens": 6000,
                    "top_p": 0.9
                }
            )
        ]
        
        for role in system_roles:
            existing_role = self.get_role(role.role_id)
            if not existing_role:
                self.save_role(role)
                role_logger.info(f"初始化系统角色: {role.name}")
    
    def save_role(self, role: RoleConfig) -> bool:
        """保存角色"""
        if not self.current_storage:
            return False
        return self.current_storage.save_role(role)
    
    def get_role(self, role_id: str) -> Optional[RoleConfig]:
        """获取角色"""
        if not self.current_storage:
            return None
        return self.current_storage.load_role(role_id)
    
    def delete_role(self, role_id: str) -> bool:
        """删除角色（不能删除系统角色）"""
        if not self.current_storage:
            return False
            
        role = self.get_role(role_id)
        if role and role.is_system:
            role_logger.warning(f"尝试删除系统角色: {role_id}")
            return False
            
        return self.current_storage.delete_role(role_id)
    
    def list_roles(self, category: Optional[str] = None, user_id: Optional[str] = None) -> List[RoleConfig]:
        """列出角色"""
        if not self.current_storage:
            return []
        return self.current_storage.list_roles(category, user_id)
    
    def search_roles(self, query: str) -> List[RoleConfig]:
        """搜索角色"""
        if not self.current_storage:
            return []
        return self.current_storage.search_roles(query)
    
    def create_role(self, name: str, description: str, system_prompt: str, 
                   avatar: str = "🤖", category: str = "通用", 
                   tags: List[str] = None, user_id: Optional[str] = None,
                   default_model: Optional[str] = None,
                   model_config: Optional[Dict[str, Any]] = None) -> RoleConfig:
        """创建新角色"""
        role_id = str(uuid.uuid4())
        role = RoleConfig(
            role_id=role_id,
            name=name,
            description=description,
            system_prompt=system_prompt,
            avatar=avatar,
            category=category,
            tags=tags or [],
            user_id=user_id,
            is_system=False,
            default_model=default_model,
            model_config=model_config or {}
        )
        
        if self.save_role(role):
            role_logger.info(f"创建新角色: {name}")
            return role
        else:
            raise Exception("保存角色失败")
    
    def update_role(self, role_id: str, **kwargs) -> bool:
        """更新角色"""
        role = self.get_role(role_id)
        if not role:
            return False
            
        # 系统角色不允许修改
        if role.is_system:
            role_logger.warning(f"尝试修改系统角色: {role_id}")
            return False
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(role, key):
                setattr(role, key, value)
        
        role.updated_at = time.time()
        return self.save_role(role)
    
    def get_categories(self) -> List[str]:
        """获取所有角色分类"""
        roles = self.list_roles()
        categories = list(set(role.category for role in roles))
        categories.sort()
        return categories
    
    def switch_storage(self, backend: str, config: Dict[str, Any]) -> bool:
        """切换存储后端"""
        return self.initialize_storage(backend, config)
    
    def get_role_recommended_model(self, role_id: str) -> Optional[str]:
        """获取角色推荐的模型"""
        role = self.get_role(role_id)
        if role and role.default_model:
            return role.default_model
        return None
    
    def get_role_model_config(self, role_id: str) -> Dict[str, Any]:
        """获取角色的模型配置"""
        role = self.get_role(role_id)
        if role and role.model_config:
            return role.model_config
        return {}
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        roles = self.list_roles()
        return {
            "backend": self.current_backend,
            "role_count": len(roles),
            "categories": self.get_categories(),
            "available_backends": list(self.storage_backends.keys())
        }

# 全局角色管理器实例
role_manager = RoleManager()
"""角色工具管理器 - 将角色注册为可调用的工具"""

import json
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from roles.role_manager import role_manager, RoleConfig
from models.model_manager import model_manager
from utils.session_manager import session_manager
from utils.logger import setup_logger

# 设置角色工具logger
role_tools_logger = setup_logger("role_tools")

@dataclass
class RoleToolContext:
    """角色工具上下文"""
    role_id: str
    session_id: str
    messages: List[Dict[str, Any]]
    model_name: Optional[str] = None
    
class RoleToolManager:
    """角色工具管理器"""
    
    def __init__(self):
        self.role_contexts: Dict[str, Dict[str, RoleToolContext]] = {}  # user_id -> role_id -> context
        self.active_sessions: Dict[str, str] = {}  # context_id -> session_id
        
    def get_role_tools(self) -> List[Dict[str, Any]]:
        """获取所有角色工具的定义"""
        tools = []
        roles = role_manager.list_roles()
        
        for role in roles:
            # 为每个角色创建一个工具定义
            tool_definition = {
                "type": "function",
                "function": {
                    "name": f"call_role_{role.role_id}",
                    "description": f"调用角色 {role.name}: {role.description}。适用场景: {', '.join(role.tags)}",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "要发送给角色的消息内容"
                            },
                            "user_id": {
                                "type": "string", 
                                "description": "用户ID，用于维护独立的对话上下文",
                                "default": "default_user"
                            },
                            "model_override": {
                                "type": "string",
                                "description": "可选：指定使用的模型，如果不指定则使用角色的默认模型"
                            }
                        },
                        "required": ["message"]
                    }
                }
            }
            tools.append(tool_definition)
            
        role_tools_logger.info(f"注册了 {len(tools)} 个角色工具")
        return tools
    
    def _get_or_create_role_context(self, role_id: str, user_id: str = "default_user") -> RoleToolContext:
        """获取或创建角色上下文"""
        if user_id not in self.role_contexts:
            self.role_contexts[user_id] = {}
            
        if role_id not in self.role_contexts[user_id]:
            # 创建新的角色上下文
            role = role_manager.get_role(role_id)
            if not role:
                raise ValueError(f"角色不存在: {role_id}")
                
            # 为角色创建独立的会话
            session_id = session_manager.create_session(
                system_prompt=role.system_prompt,
                role_id=role_id
            )
            
            context = RoleToolContext(
                role_id=role_id,
                session_id=session_id,
                messages=[],
                model_name=role.default_model
            )
            
            self.role_contexts[user_id][role_id] = context
            role_tools_logger.info(f"为用户 {user_id} 创建角色 {role.name} 的上下文")
            
        return self.role_contexts[user_id][role_id]
    
    def call_role_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用角色函数"""
        try:
            # 解析角色ID
            if not function_name.startswith("call_role_"):
                raise ValueError(f"无效的角色函数名: {function_name}")
                
            role_id = function_name[10:]  # 移除 "call_role_" 前缀
            role = role_manager.get_role(role_id)
            if not role:
                raise ValueError(f"角色不存在: {role_id}")
            
            # 获取参数
            message = arguments.get("message", "")
            user_id = arguments.get("user_id", "default_user")
            model_override = arguments.get("model_override")
            
            if not message:
                raise ValueError("消息内容不能为空")
            
            # 获取或创建角色上下文
            context = self._get_or_create_role_context(role_id, user_id)
            
            # 确定使用的模型
            target_model = model_override or context.model_name
            current_model_config = model_manager.get_current_config()
            
            # 如果需要切换模型
            if target_model and (not current_model_config or current_model_config.name != target_model):
                available_models = [m["name"] for m in model_manager.get_available_models()]
                if target_model in available_models:
                    model_manager.switch_model(target_model)
                    role_tools_logger.info(f"为角色 {role.name} 切换到模型: {target_model}")
                else:
                    role_tools_logger.warning(f"模型 {target_model} 不可用，使用当前模型")
            
            # 构建消息历史
            messages = []
            
            # 添加系统提示
            if role.system_prompt:
                messages.append({"role": "system", "content": role.system_prompt})
            
            # 添加历史消息
            history_messages = session_manager.get_messages(context.session_id, limit=10)
            for hist_msg in history_messages:
                messages.append({"role": hist_msg.role, "content": hist_msg.content})
            
            # 添加当前用户消息
            messages.append({"role": "user", "content": message})
            
            # 使用模型管理器处理消息
            response = model_manager.chat_with_model(messages)
            
            # 保存消息到会话
            session_manager.add_message(context.session_id, "user", message)
            session_manager.add_message(context.session_id, "assistant", response)
            
            # 更新上下文消息历史
            context.messages.append({"role": "user", "content": message})
            context.messages.append({"role": "assistant", "content": response})
            
            # 限制消息历史长度
            if len(context.messages) > 20:
                context.messages = context.messages[-20:]
            
            return {
                "role_name": role.name,
                "role_id": role_id,
                "response": response,
                "model_used": model_manager.get_current_config().name if model_manager.get_current_config() else "unknown",
                "context_length": len(context.messages),
                "success": True
            }
            
        except Exception as e:
            role_tools_logger.error(f"调用角色函数失败 {function_name}: {e}")
            return {
                "error": str(e),
                "success": False
            }
    
    def get_role_context_info(self, role_id: str, user_id: str = "default_user") -> Dict[str, Any]:
        """获取角色上下文信息"""
        if user_id in self.role_contexts and role_id in self.role_contexts[user_id]:
            context = self.role_contexts[user_id][role_id]
            role = role_manager.get_role(role_id)
            return {
                "role_name": role.name if role else "未知",
                "role_id": role_id,
                "session_id": context.session_id,
                "message_count": len(context.messages),
                "model_name": context.model_name,
                "has_context": True
            }
        else:
            return {
                "role_id": role_id,
                "has_context": False
            }
    
    def clear_role_context(self, role_id: str, user_id: str = "default_user") -> bool:
        """清除角色上下文"""
        try:
            if user_id in self.role_contexts and role_id in self.role_contexts[user_id]:
                context = self.role_contexts[user_id][role_id]
                # 删除会话
                session_manager.delete_session(context.session_id)
                # 删除上下文
                del self.role_contexts[user_id][role_id]
                role_tools_logger.info(f"清除用户 {user_id} 的角色 {role_id} 上下文")
                return True
            return False
        except Exception as e:
            role_tools_logger.error(f"清除角色上下文失败: {e}")
            return False
    
    def get_all_contexts_info(self, user_id: str = "default_user") -> List[Dict[str, Any]]:
        """获取用户的所有角色上下文信息"""
        contexts = []
        if user_id in self.role_contexts:
            for role_id in self.role_contexts[user_id]:
                contexts.append(self.get_role_context_info(role_id, user_id))
        return contexts
    
    def cleanup_inactive_contexts(self, max_idle_time: int = 3600) -> int:
        """清理不活跃的上下文"""
        # 这里可以实现基于时间的清理逻辑
        # 暂时返回0
        return 0

# 全局角色工具管理器实例
role_tool_manager = RoleToolManager()
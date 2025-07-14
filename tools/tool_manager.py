"""新版工具管理器 - 支持角色工具和常规工具"""

import json
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from utils.logger import setup_logger
from .role_tools import role_tool_manager

# 设置工具管理器logger
tools_logger = setup_logger("tools")

class BaseTool(ABC):
    """工具基类"""
    
    @abstractmethod
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取工具定义"""
        pass
    
    @abstractmethod
    def execute(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        pass
    
    @abstractmethod
    def can_handle(self, function_name: str) -> bool:
        """检查是否能处理指定的函数"""
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """检查工具是否启用"""
        pass

class MathTool(BaseTool):
    """数学工具"""
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "add",
                    "description": "计算两个数的和",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number", "description": "第一个数"},
                            "b": {"type": "number", "description": "第二个数"}
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "multiply",
                    "description": "计算两个数的乘积",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number", "description": "第一个数"},
                            "b": {"type": "number", "description": "第二个数"}
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "subtract",
                    "description": "计算两个数的差",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number", "description": "被减数"},
                            "b": {"type": "number", "description": "减数"}
                        },
                        "required": ["a", "b"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "divide",
                    "description": "计算两个数的商",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number", "description": "被除数"},
                            "b": {"type": "number", "description": "除数"}
                        },
                        "required": ["a", "b"]
                    }
                }
            }
        ]
    
    def execute(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            a = arguments.get("a", 0)
            b = arguments.get("b", 0)
            
            if function_name == "add":
                result = a + b
            elif function_name == "multiply":
                result = a * b
            elif function_name == "subtract":
                result = a - b
            elif function_name == "divide":
                if b == 0:
                    return {"error": "除数不能为零"}
                result = a / b
            else:
                return {"error": f"未知的数学函数: {function_name}"}
            
            return {"result": result, "operation": f"{a} {function_name} {b} = {result}"}
        except Exception as e:
            return {"error": str(e)}
    
    def can_handle(self, function_name: str) -> bool:
        return function_name in ["add", "multiply", "subtract", "divide"]
    
    def is_enabled(self) -> bool:
        return True

class SearchTool(BaseTool):
    """搜索工具"""
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "在网络上搜索信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索查询"}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    def execute(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if function_name == "web_search":
                query = arguments.get("query", "")
                # 这里应该实现真正的搜索逻辑
                return {
                    "query": query,
                    "results": f"搜索结果：{query}（模拟结果）",
                    "status": "success"
                }
            else:
                return {"error": f"未知的搜索函数: {function_name}"}
        except Exception as e:
            return {"error": str(e)}
    
    def can_handle(self, function_name: str) -> bool:
        return function_name in ["web_search"]
    
    def is_enabled(self) -> bool:
        return True

class ToolManager:
    """统一工具管理器"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {
            "math": MathTool(),
            "search": SearchTool(),
        }
        tools_logger.info(f"工具管理器初始化完成，注册了 {len(self.tools)} 类工具")
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取所有可用工具的定义"""
        tools = []
        
        # 添加常规工具
        for tool in self.tools.values():
            if tool.is_enabled():
                tools.extend(tool.get_tool_definitions())
        
        # 添加角色工具
        role_tools = role_tool_manager.get_role_tools()
        tools.extend(role_tools)
        
        return tools
    
    def execute_tool(self, tool_call) -> Dict[str, Any]:
        """执行工具调用"""
        try:
            # 兼容字典和对象两种格式
            if isinstance(tool_call, dict):
                function_name = tool_call.get('name')
                arguments = tool_call.get('args', {})
            else:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
            
            tools_logger.info(f"执行工具调用: {function_name}, 参数: {arguments}")
            
            # 检查是否是角色工具调用
            if function_name.startswith("call_role_"):
                result = role_tool_manager.call_role_function(function_name, arguments)
                tools_logger.info(f"角色工具执行结果: {result}")
                return result
            
            # 查找对应的常规工具
            for tool in self.tools.values():
                if tool.is_enabled() and tool.can_handle(function_name):
                    result = tool.execute(function_name, arguments)
                    tools_logger.info(f"工具执行结果: {result}")
                    return result
            
            # 如果没有找到对应的工具
            error_msg = f"未找到工具: {function_name}"
            tools_logger.error(error_msg)
            return {"error": error_msg}
            
        except Exception as e:
            error_msg = f"工具执行失败: {str(e)}"
            tools_logger.error(error_msg)
            return {"error": error_msg}
    
    def get_tool_categories(self) -> Dict[str, List[str]]:
        """获取工具分类信息"""
        categories = {}
        
        # 常规工具分类
        for name, tool in self.tools.items():
            if tool.is_enabled():
                tool_defs = tool.get_tool_definitions()
                categories[name] = [t["function"]["name"] for t in tool_defs]
        
        # 角色工具分类
        role_tools = role_tool_manager.get_role_tools()
        if role_tools:
            categories["roles"] = [t["function"]["name"] for t in role_tools]
        
        return categories
    
    def register_tool(self, name: str, tool: BaseTool) -> bool:
        """注册新工具"""
        try:
            self.tools[name] = tool
            tools_logger.info(f"注册新工具: {name}")
            return True
        except Exception as e:
            tools_logger.error(f"注册工具失败: {e}")
            return False

# 全局工具管理器实例
tool_manager = ToolManager()

# 兼容旧版接口
def get_all_tools():
    """获取所有可用工具（兼容旧版接口）"""
    return tool_manager.get_available_tools()

def create_tool_map(tools_list):
    """创建工具映射（兼容旧版接口）"""
    return {tool["function"]["name"]: tool for tool in tools_list}

def execute_tool_calls(tool_calls, tool_map):
    """执行工具调用（兼容旧版接口）"""
    from langchain_core.messages import ToolMessage
    tool_messages = []
    
    for tool_call in tool_calls:
        try:
            # 使用新的工具管理器执行
            result = tool_manager.execute_tool(tool_call)
            
            # 格式化结果
            if "error" in result:
                content = f"错误: {result['error']}"
            else:
                content = json.dumps(result, ensure_ascii=False)
            
            # 兼容字典和对象两种格式获取tool_call_id
            if isinstance(tool_call, dict):
                tool_call_id = tool_call.get('id', str(id(tool_call)))
            else:
                tool_call_id = tool_call.id
            
            tool_message = ToolMessage(
                content=content,
                tool_call_id=tool_call_id
            )
            tool_messages.append(tool_message)
            
        except Exception as e:
            # 兼容字典和对象两种格式获取tool_call_id
            if isinstance(tool_call, dict):
                tool_call_id = tool_call.get('id', str(id(tool_call)))
            else:
                tool_call_id = tool_call.id
                
            error_message = ToolMessage(
                content=f"工具执行错误: {str(e)}",
                tool_call_id=tool_call_id
            )
            tool_messages.append(error_message)
    
    return tool_messages

def get_tool_descriptions():
    """获取所有工具的描述（兼容旧版接口）"""
    tools = tool_manager.get_available_tools()
    descriptions = {}
    for tool in tools:
        descriptions[tool["function"]["name"]] = tool["function"]["description"]
    return descriptions
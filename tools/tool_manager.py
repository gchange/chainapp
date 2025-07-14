"""工具管理器"""

from langchain_core.messages import ToolMessage
from typing import List, Dict, Any
from utils.logger import setup_logger

# 设置工具管理器专用的logger
tool_manager_logger = setup_logger("tool_manager")

def create_tool_map(tools_list):
    """创建工具名称到工具对象的映射"""
    tool_map = {}
    for tool in tools_list:
        tool_map[tool.name] = tool
    
    tool_manager_logger.info(f"创建工具映射，包含 {len(tool_map)} 个工具: {list(tool_map.keys())}")
    return tool_map

def execute_tool_calls(tool_calls, tool_map):
    """执行工具调用并返回结果消息列表"""
    tool_manager_logger.info(f"开始执行 {len(tool_calls)} 个工具调用")
    tool_messages = []
    
    for i, tool_call in enumerate(tool_calls, 1):
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        tool_call_id = tool_call['id']
        
        tool_manager_logger.info(f"执行工具 [{i}/{len(tool_calls)}]: {tool_name}")
        tool_manager_logger.debug(f"工具参数: {tool_args}")
        
        if tool_name in tool_map:
            try:
                # 通用的工具调用方式
                tool_result = tool_map[tool_name].invoke(tool_args)
                tool_manager_logger.info(f"工具 {tool_name} 执行成功")
                tool_manager_logger.debug(f"工具执行结果: {str(tool_result)[:200]}...")
                
                # 创建工具响应消息
                tool_message = ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call_id
                )
                tool_messages.append(tool_message)
                
            except Exception as e:
                tool_manager_logger.error(f"工具 {tool_name} 执行出错: {e}")
                error_message = ToolMessage(
                    content=f"Error executing {tool_name}: {str(e)}",
                    tool_call_id=tool_call_id
                )
                tool_messages.append(error_message)
        else:
            tool_manager_logger.error(f"未找到工具: {tool_name}")
            error_message = ToolMessage(
                content=f"Tool {tool_name} not found",
                tool_call_id=tool_call_id
            )
            tool_messages.append(error_message)
    
    tool_manager_logger.info(f"工具调用执行完成，生成 {len(tool_messages)} 个响应消息")
    return tool_messages

def get_all_tools():
    """获取所有可用工具"""
    from . import multiply, add, divide, subtract
    return [multiply, add, divide, subtract]

def get_tool_descriptions():
    """获取所有工具的描述"""
    tools = get_all_tools()
    descriptions = {}
    for tool in tools:
        descriptions[tool.name] = tool.description
    return descriptions
def get_all_tools():
    """获取所有可用工具"""
    from . import (multiply, add, divide, subtract, power, square_root, absolute, round_number,
                   uppercase, lowercase, reverse_string, count_words,
                   web_search, quick_search, search_definition, search_news)
    return [multiply, add, divide, subtract, power, square_root, absolute, round_number,
            uppercase, lowercase, reverse_string, count_words,
            web_search, quick_search, search_definition, search_news]

def get_math_tools():
    """获取数学工具"""
    from . import multiply, add, divide, subtract, power, square_root, absolute, round_number
    return [multiply, add, divide, subtract, power, square_root, absolute, round_number]

def get_string_tools():
    """获取字符串工具"""
    from . import uppercase, lowercase, reverse_string, count_words
    return [uppercase, lowercase, reverse_string, count_words]

def get_search_tools():
    """获取搜索工具"""
    from . import web_search, quick_search, search_definition, search_news
    return [web_search, quick_search, search_definition, search_news]

def get_all_tools_with_categories():
    """获取所有工具，按类别分组"""
    return {
        'math': get_math_tools(),
        'string': get_string_tools(),
        'search': get_search_tools()
    }
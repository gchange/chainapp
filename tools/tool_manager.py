"""工具管理器"""

from langchain_core.messages import ToolMessage
from typing import List, Dict, Any

def create_tool_map(tools_list):
    """创建工具名称到工具对象的映射"""
    tool_map = {}
    for tool in tools_list:
        tool_map[tool.name] = tool
    return tool_map

def execute_tool_calls(tool_calls, tool_map):
    """执行工具调用并返回结果消息列表"""
    tool_messages = []
    
    for tool_call in tool_calls:
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        tool_call_id = tool_call['id']
        
        print(f"执行工具: {tool_name}")
        print(f"参数: {tool_args}")
        
        if tool_name in tool_map:
            try:
                # 通用的工具调用方式
                tool_result = tool_map[tool_name].invoke(tool_args)
                print(f"工具执行结果: {tool_result}")
                
                # 创建工具响应消息
                tool_message = ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call_id
                )
                tool_messages.append(tool_message)
                
            except Exception as e:
                print(f"工具 {tool_name} 执行出错: {e}")
                error_message = ToolMessage(
                    content=f"Error executing {tool_name}: {str(e)}",
                    tool_call_id=tool_call_id
                )
                tool_messages.append(error_message)
        else:
            print(f"未找到工具: {tool_name}")
            error_message = ToolMessage(
                content=f"Tool {tool_name} not found",
                tool_call_id=tool_call_id
            )
            tool_messages.append(error_message)
    
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
    from . import multiply, add, divide, subtract, power, square_root, absolute, round_number
    return [multiply, add, divide, subtract, power, square_root, absolute, round_number]

def get_math_tools():
    """获取数学工具"""
    from . import multiply, add, divide, subtract, power, square_root, absolute, round_number
    return [multiply, add, divide, subtract, power, square_root, absolute, round_number]

def get_string_tools():
    """获取字符串工具"""
    from . import uppercase, lowercase, reverse_string, count_words
    return [uppercase, lowercase, reverse_string, count_words]

def get_all_tools_with_categories():
    """获取所有工具，按类别分组"""
    return {
        'math': get_math_tools(),
        'string': get_string_tools()
    }
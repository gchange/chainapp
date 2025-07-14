#coding: utf8

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage

# 导入工具包
from tools import multiply, add, divide, subtract
from tools.tool_manager import create_tool_map, execute_tool_calls, get_all_tools, get_tool_descriptions

def stream_output(res):
    print('chat resp:', end='\t')
    for r in res:
      print(r.content, end='')
    print('')

def main():
    # 初始化模型
    chatLLM = ChatTongyi(
        streaming=False,  # 关闭流式输出，便于处理工具调用
    )

    # 消息列表
    messages = [
        SystemMessage(
            content="你的名字是ikun，擅长唱、跳、rap、打篮球，你的回答里面总是带着这些元素."
        ),
        HumanMessage(
            content="计算3.14乘以2.5，然后加上1.86，最后开平方根，结果保留3位小数"
        ),
    ]

    # 工具列表 - 从工具包获取
    tools = get_all_tools()
    
    # 显示可用工具信息
    print("=== 可用工具 ===")
    tool_descriptions = get_tool_descriptions()
    for name, desc in tool_descriptions.items():
        print(f"- {name}: {desc}")
    print("=" * 50)

    # 创建工具映射
    tool_map = create_tool_map(tools)
    print(f"已加载工具: {list(tool_map.keys())}")

    # 绑定工具到模型
    tool_chat = chatLLM.bind_tools(tools)
    
    while True:
        try:
            # 第一次调用：获取AI响应
            result = tool_chat.invoke(messages)
            print("AI 响应:", result.content)
            
            # 检查是否有工具调用
            if hasattr(result, 'tool_calls') and result.tool_calls:
                print("检测到工具调用:", result.tool_calls)
                
                # 将AI的响应添加到消息历史
                messages.append(result)
                
                # 执行所有工具调用
                tool_messages = execute_tool_calls(result.tool_calls, tool_map)
                messages.extend(tool_messages)
            else:
                print("没有工具调用，直接回答")
                print("最终结果:", result.content)
                break
                
        except Exception as e:
            print(f"执行出错: {e}")
            # 如果工具调用失败，尝试简单调用
            simple_result = chatLLM.invoke(messages)
            print("简单调用结果:", simple_result.content)
            break

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""ChatApp API 客户端测试脚本"""

import json
import requests
import asyncio
import aiohttp
from typing import List, Dict, Any
from utils.logger import setup_logger

# 设置客户端logger
client_logger = setup_logger("chat_client", log_file="chat_client.log")

class ChatClient:
    """聊天客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        try:
            response = requests.get(f"{self.base_url}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            client_logger.error(f"获取状态失败: {e}")
            return {"error": str(e)}
    
    def get_tools(self) -> Dict[str, Any]:
        """获取可用工具"""
        try:
            response = requests.get(f"{self.base_url}/tools")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            client_logger.error(f"获取工具列表失败: {e}")
            return {"error": str(e)}
    
    def chat_sync(self, messages: List[Dict[str, str]], stream: bool = False) -> Dict[str, Any]:
        """同步聊天"""
        try:
            payload = {
                "messages": messages,
                "stream": stream
            }
            
            response = requests.post(
                f"{self.base_url}/chat",
                json=payload
            )
            response.raise_for_status()
            
            if not stream:
                return response.json()
            else:
                return {"content": response.text}
                
        except Exception as e:
            client_logger.error(f"同步聊天失败: {e}")
            return {"error": str(e)}
    
    async def chat_stream(self, messages: List[Dict[str, str]]) -> None:
        """流式聊天"""
        if not self.session:
            client_logger.error("会话未初始化")
            return
        
        try:
            payload = {
                "messages": messages,
                "stream": True
            }
            
            client_logger.info("发送流式聊天请求...")
            
            async with self.session.post(
                f"{self.base_url}/chat",
                json=payload
            ) as response:
                response.raise_for_status()
                
                print("\n=== 流式响应开始 ===")
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if line.startswith('data: '):
                        data_str = line[6:]  # 移除 'data: ' 前缀
                        
                        try:
                            data = json.loads(data_str)
                            await self._handle_stream_data(data)
                        except json.JSONDecodeError:
                            client_logger.debug(f"跳过非 JSON 数据: {data_str}")
                
                print("\n=== 流式响应结束 ===")
                
        except Exception as e:
            client_logger.error(f"流式聊天失败: {e}")
            print(f"错误: {e}")
    
    async def _handle_stream_data(self, data: Dict[str, Any]) -> None:
        """处理流式数据"""
        data_type = data.get("type", "unknown")
        
        if data_type == "thinking":
            print(f"\n🤔 AI 思考: {data.get('content', '')}")
            if data.get('tool_calls'):
                print("🔧 准备调用工具:")
                for tc in data['tool_calls']:
                    print(f"  - {tc['name']}: {tc['args']}")
        
        elif data_type == "tool_result":
            tool_name = data.get('tool_name', '未知工具')
            result = data.get('result', '无结果')
            step = data.get('step', 0)
            total = data.get('total_steps', 0)
            
            print(f"\n⚡ 工具执行 [{step}/{total}]: {tool_name}")
            print(f"📊 结果: {result}")
        
        elif data_type == "content":
            content = data.get('content', '')
            print(content, end='', flush=True)
        
        elif data_type == "done":
            print(f"\n\n✅ 对话完成 (原因: {data.get('finish_reason', 'unknown')})")
        
        elif data_type == "error":
            print(f"\n❌ 错误: {data.get('error', '未知错误')}")
        
        else:
            client_logger.debug(f"未知数据类型: {data_type}")

async def main():
    """主函数"""
    client_logger.info("启动聊天客户端")
    
    client = ChatClient()
    
    # 检查服务器状态
    print("检查服务器状态...")
    status = client.get_status()
    if "error" in status:
        print(f"服务器连接失败: {status['error']}")
        return
    
    print(f"服务器状态: {status['status']}")
    print(f"模型已加载: {status['model_loaded']}")
    print(f"可用工具数: {status['tools_count']}")
    
    # 获取工具列表
    print("\n获取可用工具...")
    tools = client.get_tools()
    if "error" not in tools:
        print("可用工具:")
        for tool in tools.get('tools', []):
            print(f"  - {tool['name']}: {tool['description']}")
    
    # 测试场景
    test_cases = [
        {
            "name": "数学计算",
            "messages": [
                {"role": "user", "content": "计算 3.14 乘以 2.5，然后加上 1.86，最后开平方根"}
            ]
        },
        {
            "name": "搜索功能",
            "messages": [
                {"role": "user", "content": "搜索一下今天的天气情况"}
            ]
        },
        {
            "name": "混合场景",
            "messages": [
                {"role": "user", "content": "搜索篮球的标准直径，然后计算周长"}
            ]
        }
    ]
    
    # 选择测试场景
    print(f"\n可用测试场景:")
    for i, case in enumerate(test_cases):
        print(f"{i+1}. {case['name']}")
    
    try:
        choice = input("\n请选择测试场景 (1-3, 默认1): ").strip() or "1"
        case_index = int(choice) - 1
        
        if 0 <= case_index < len(test_cases):
            selected_case = test_cases[case_index]
            print(f"\n选择的场景: {selected_case['name']}")
            
            # 流式聊天测试
            async with ChatClient() as stream_client:
                await stream_client.chat_stream(selected_case['messages'])
        
        else:
            print("无效选择")
    
    except ValueError:
        print("输入无效")
    except KeyboardInterrupt:
        print("\n用户中断")
    
    client_logger.info("客户端测试完成")

if __name__ == "__main__":
    asyncio.run(main())
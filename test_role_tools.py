"""测试角色工具功能"""

import requests
import json

def test_role_tools():
    base_url = "http://localhost:8000"
    
    # 1. 获取角色工具列表
    print("1. 获取角色工具列表...")
    response = requests.get(f"{base_url}/roles/tools")
    if response.status_code == 200:
        tools = response.json()
        print(f"找到 {tools['tool_count']} 个角色工具")
        for tool in tools['tools'][:3]:  # 只显示前3个
            print(f"  - {tool['function']['name']}: {tool['function']['description']}")
    else:
        print(f"获取失败: {response.status_code}")
        return
    
    # 2. 测试调用程序员助手
    print("\n2. 测试调用程序员助手...")
    test_data = {
        "function_name": "call_role_programmer",
        "arguments": {
            "message": "请用Python写一个简单的计算器函数",
            "user_id": "test_user"
        }
    }
    
    response = requests.post(f"{base_url}/roles/tools/call", json=test_data)
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print(f"调用成功!")
            print(f"角色: {result['role_name']}")
            print(f"使用模型: {result['model_used']}")
            print(f"回复: {result['response'][:200]}...")
        else:
            print(f"调用失败: {result.get('error')}")
    else:
        print(f"请求失败: {response.status_code}")
    
    # 3. 查看上下文信息
    print("\n3. 查看上下文信息...")
    response = requests.get(f"{base_url}/roles/contexts/test_user")
    if response.status_code == 200:
        contexts = response.json()
        print(f"用户 test_user 有 {contexts['context_count']} 个角色上下文")
        for context in contexts['contexts']:
            if context['has_context']:
                print(f"  - {context['role_name']}: {context['message_count']} 条消息")
    
    # 4. 再次调用同一个角色，测试上下文保持
    print("\n4. 再次调用同一个角色...")
    test_data2 = {
        "function_name": "call_role_programmer",
        "arguments": {
            "message": "请优化上面的代码，添加错误处理",
            "user_id": "test_user"
        }
    }
    
    response = requests.post(f"{base_url}/roles/tools/call", json=test_data2)
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print(f"上下文调用成功!")
            print(f"上下文长度: {result['context_length']}")
            print(f"回复: {result['response'][:200]}...")
    
    # 5. 测试调用不同的角色
    print("\n5. 测试调用翻译专家...")
    test_data3 = {
        "function_name": "call_role_translator",
        "arguments": {
            "message": "请将 'Hello, how are you today?' 翻译成中文",
            "user_id": "test_user"
        }
    }
    
    response = requests.post(f"{base_url}/roles/tools/call", json=test_data3)
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print(f"翻译角色调用成功!")
            print(f"角色: {result['role_name']}")
            print(f"使用模型: {result['model_used']}")
            print(f"回复: {result['response']}")

if __name__ == "__main__":
    test_role_tools()
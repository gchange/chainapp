#!/usr/bin/env python3
"""测试服务器"""

import requests
import time
from utils.logger import setup_logger

test_logger = setup_logger("test_server")

def test_server_endpoints():
    """测试服务器端点"""
    base_url = "http://localhost:8000"
    
    # 等待服务器启动
    print("等待服务器启动...")
    time.sleep(3)
    
    try:
        # 测试根路径
        print("测试根路径...")
        response = requests.get(f"{base_url}/")
        print(f"根路径状态码: {response.status_code}")
        
        # 测试状态接口
        print("测试状态接口...")
        response = requests.get(f"{base_url}/status")
        print(f"状态接口状态码: {response.status_code}")
        if response.status_code == 200:
            status_data = response.json()
            print(f"服务状态: {status_data}")
        else:
            print(f"状态接口错误: {response.text}")
        
        # 测试工具接口
        print("测试工具接口...")
        response = requests.get(f"{base_url}/tools")
        print(f"工具接口状态码: {response.status_code}")
        if response.status_code == 200:
            tools_data = response.json()
            print(f"工具数量: {len(tools_data.get('tools', []))}")
        
        # 测试文档
        print("测试API文档...")
        response = requests.get(f"{base_url}/docs")
        print(f"文档接口状态码: {response.status_code}")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保服务器正在运行")
    except Exception as e:
        print(f"❌ 测试出错: {e}")

if __name__ == "__main__":
    test_server_endpoints()
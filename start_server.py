#!/usr/bin/env python3
"""启动脚本"""

import os
import sys
import uvicorn
from utils.logger import setup_logger

# 设置启动脚本logger
start_logger = setup_logger("server_start")

def main():
    """主函数"""
    start_logger.info("正在启动 ChatApp 服务器...")
    
    # 检查环境
    try:
        import fastapi
        import uvicorn
        from langchain_community.chat_models.tongyi import ChatTongyi
        start_logger.info("依赖检查通过")
    except ImportError as e:
        start_logger.error(f"缺少依赖: {e}")
        print(f"请安装缺少的依赖: pip install {e.name}")
        sys.exit(1)
    
    # 检查静态文件目录
    if not os.path.exists("static"):
        start_logger.warning("static 目录不存在，创建中...")
        os.makedirs("static")
    
    # 启动服务器
    try:
        start_logger.info("启动 uvicorn 服务器...")
        uvicorn.run(
            "chat_server:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        start_logger.info("服务器被用户中断")
    except Exception as e:
        start_logger.error(f"服务器启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
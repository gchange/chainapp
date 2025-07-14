"""日志配置模块"""

import logging
import sys
from typing import Optional

def setup_logger(
    name: str = "chainapp",
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    设置并返回一个配置好的logger
    
    Args:
        name: logger名称
        level: 日志级别
        format_string: 日志格式字符串
        log_file: 日志文件路径（可选）
    
    Returns:
        配置好的logger实例
    """
    
    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 如果已经有处理器，先清除
    if logger.handlers:
        logger.handlers.clear()
    
    # 设置日志格式
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_string)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了文件）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# 创建默认logger实例
default_logger = setup_logger()

# 提供便捷的日志函数
def log_info(message: str, logger: Optional[logging.Logger] = None):
    """记录信息日志"""
    (logger or default_logger).info(message)

def log_error(message: str, logger: Optional[logging.Logger] = None):
    """记录错误日志"""
    (logger or default_logger).error(message)

def log_warning(message: str, logger: Optional[logging.Logger] = None):
    """记录警告日志"""
    (logger or default_logger).warning(message)

def log_debug(message: str, logger: Optional[logging.Logger] = None):
    """记录调试日志"""
    (logger or default_logger).debug(message)
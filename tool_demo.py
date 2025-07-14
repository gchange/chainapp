#!/usr/bin/env python3
"""工具演示脚本"""

from tools.search_tools import web_search, quick_search, search_definition
from tools.math_tools import multiply, add, divide, square_root, round_number
from utils.logger import setup_logger

# 设置演示脚本专用的logger
demo_logger = setup_logger("tool_demo")

def demo_search_tools():
    """演示搜索工具"""
    demo_logger.info("开始搜索工具演示")
    
    # 测试基本搜索
    demo_logger.info("测试基本搜索功能")
    try:
        result = web_search.invoke("Obama's first name")
        result_preview = result[:200] + "..." if len(str(result)) > 200 else str(result)
        demo_logger.info(f"基本搜索成功，结果长度: {len(str(result))}")
        demo_logger.debug(f"搜索结果预览: {result_preview}")
    except Exception as e:
        demo_logger.error(f"基本搜索失败: {e}")
    
    # 测试快速搜索
    demo_logger.info("测试快速搜索功能")
    try:
        result = quick_search.invoke("Python programming language")
        result_preview = result[:300] + "..." if len(str(result)) > 300 else str(result)
        demo_logger.info(f"快速搜索成功，结果长度: {len(str(result))}")
        demo_logger.debug(f"快速搜索结果预览: {result_preview}")
    except Exception as e:
        demo_logger.error(f"快速搜索失败: {e}")
    
    # 测试定义搜索
    demo_logger.info("测试定义搜索功能")
    try:
        result = search_definition.invoke("artificial intelligence")
        result_preview = result[:250] + "..." if len(str(result)) > 250 else str(result)
        demo_logger.info(f"定义搜索成功，结果长度: {len(str(result))}")
        demo_logger.debug(f"定义搜索结果预览: {result_preview}")
    except Exception as e:
        demo_logger.error(f"定义搜索失败: {e}")
    
    demo_logger.info("搜索工具演示完成")

def demo_math_tools():
    """演示数学工具"""
    demo_logger.info("开始数学工具演示")
    
    try:
        # 测试基本运算
        a, b = 3.14, 2.5
        demo_logger.info(f"计算 {a} × {b}")
        result1 = multiply.invoke({'first_number': a, 'second_number': b})
        demo_logger.info(f"乘法结果: {result1}")
        
        c = 1.86
        demo_logger.info(f"将结果加上 {c}")
        result2 = add.invoke({'first_number': result1, 'second_number': c})
        demo_logger.info(f"加法结果: {result2}")
        
        demo_logger.info("计算平方根")
        result3 = square_root.invoke({'number': result2})
        demo_logger.info(f"平方根结果: {result3}")
        
        demo_logger.info("保留3位小数")
        final_result = round_number.invoke({'number': result3, 'decimal_places': 3})
        demo_logger.info(f"最终结果: {final_result}")
        
    except Exception as e:
        demo_logger.error(f"数学工具演示失败: {e}")
    
    demo_logger.info("数学工具演示完成")

def main():
    """主函数"""
    demo_logger.info("工具包功能演示开始")
    demo_logger.info("=" * 50)
    
    try:
        demo_math_tools()
        demo_search_tools()
        demo_logger.info("所有演示完成")
    except Exception as e:
        demo_logger.error(f"演示过程中出现错误: {e}")
    
    demo_logger.info("演示程序结束")

if __name__ == "__main__":
    main()
"""搜索工具集合"""

from langchain_core.tools import tool
from typing import Union
import warnings
from utils.logger import setup_logger

# 设置搜索工具专用的logger
search_logger = setup_logger("search_tools")

# 初始化搜索引擎
_search_engine = None

def get_search_engine():
    """获取搜索引擎实例（单例模式）"""
    global _search_engine
    if _search_engine is None:
        try:
            # 尝试使用新的 ddgs 包
            try:
                from ddgs import DDGS
                _search_engine = DDGS()
                search_logger.info("成功初始化 ddgs 搜索引擎")
            except ImportError:
                # 如果 ddgs 不可用，尝试使用 langchain 的 DuckDuckGoSearchRun
                try:
                    # 忽略警告
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        from langchain_community.tools import DuckDuckGoSearchRun
                        _search_engine = DuckDuckGoSearchRun()
                    search_logger.info("成功初始化 langchain DuckDuckGoSearchRun 搜索引擎")
                except ImportError as e:
                    search_logger.error(f"无法导入搜索工具: {e}")
                    _search_engine = None
        except Exception as e:
            search_logger.error(f"初始化搜索引擎失败: {e}")
            _search_engine = None
    return _search_engine

def _perform_search(query: str, max_results: int = 5) -> str:
    """执行搜索的内部函数"""
    search_logger.debug(f"开始搜索: {query}, 最大结果数: {max_results}")
    
    search_engine = get_search_engine()
    if search_engine is None:
        search_logger.error("搜索引擎不可用")
        return "Error: Search engine not available"
    
    try:
        # 检查搜索引擎类型
        if hasattr(search_engine, 'text'):  # ddgs.DDGS 对象
            search_logger.debug("使用 ddgs 引擎执行搜索")
            results = search_engine.text(query, max_results=max_results)
            if results:
                formatted_results = []
                for i, result in enumerate(results[:max_results], 1):
                    title = result.get('title', 'No title')
                    body = result.get('body', 'No description')
                    url = result.get('href', 'No URL')
                    formatted_results.append(f"{i}. {title}\n{body}\nURL: {url}\n")
                search_logger.info(f"搜索成功，返回 {len(formatted_results)} 个结果")
                return '\n'.join(formatted_results)
            else:
                search_logger.warning("搜索未返回任何结果")
                return "No results found"
        else:  # langchain DuckDuckGoSearchRun 对象
            search_logger.debug("使用 langchain DuckDuckGoSearchRun 引擎执行搜索")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                results = search_engine.invoke(query)
            if results:
                search_logger.info("搜索成功")
            else:
                search_logger.warning("搜索未返回任何结果")
            return results if results else "No results found"
            
    except Exception as e:
        search_logger.error(f"搜索执行出错: {e}")
        return f"Search error: {str(e)}"

@tool
def web_search(query: str) -> str:
    """
    Search the web using DuckDuckGo search engine.
    
    Args:
        query: The search query string
        
    Returns:
        Search results as a string
    """
    return _perform_search(query, max_results=5)

@tool
def quick_search(query: str, max_results: int = 3) -> str:
    """
    Perform a quick web search with limited results.
    
    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 3)
        
    Returns:
        Formatted search results
    """
    return _perform_search(query, max_results=max_results)

@tool
def search_definition(term: str) -> str:
    """
    Search for the definition of a term or concept.
    
    Args:
        term: The term to define
        
    Returns:
        Definition or explanation of the term
    """
    query = f"what is {term} definition meaning"
    return _perform_search(query, max_results=3)

@tool
def search_news(topic: str, max_results: int = 3) -> str:
    """
    Search for recent news about a specific topic.
    
    Args:
        topic: The news topic to search for
        max_results: Maximum number of news results (default: 3)
        
    Returns:
        Recent news results
    """
    query = f"{topic} news recent"
    return _perform_search(query, max_results=max_results)
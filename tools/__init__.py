"""
工具包模块
"""
from .math_tools import multiply, add, divide, subtract

# 导出所有工具
__all__ = ['multiply', 'add', 'divide', 'subtract']
"""
工具包模块
"""
from .math_tools import multiply, add, divide, subtract, power, square_root, absolute, round_number
from .string_tools import uppercase, lowercase, reverse_string, count_words
from .search_tools import web_search, quick_search, search_definition, search_news

# 导出所有工具
__all__ = [
    'multiply', 'add', 'divide', 'subtract', 'power', 'square_root', 'absolute', 'round_number',
    'uppercase', 'lowercase', 'reverse_string', 'count_words',
    'web_search', 'quick_search', 'search_definition', 'search_news'
]
"""字符串处理工具集合"""

from langchain_core.tools import tool

@tool
def uppercase(text: str) -> str:
    """Convert text to uppercase."""
    return text.upper()

@tool
def lowercase(text: str) -> str:
    """Convert text to lowercase."""
    return text.lower()

@tool
def reverse_string(text: str) -> str:
    """Reverse the given string."""
    return text[::-1]

@tool
def count_words(text: str) -> int:
    """Count the number of words in the text."""
    return len(text.split())
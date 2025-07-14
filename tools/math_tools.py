"""数学计算工具集合"""

from langchain_core.tools import tool
from typing import Union

@tool
def multiply(first_number: float, second_number: float) -> float:
    """Multiply two numbers together. Supports both integers and floating point numbers."""
    return first_number * second_number

@tool
def add(first_number: float, second_number: float) -> float:
    """Add two numbers together. Supports both integers and floating point numbers."""
    return first_number + second_number

@tool
def divide(first_number: float, second_number: float) -> Union[float, str]:
    """Divide first number by second number. Supports both integers and floating point numbers."""
    if second_number == 0:
        return "Error: Division by zero"
    return first_number / second_number

@tool
def subtract(first_number: float, second_number: float) -> float:
    """Subtract second number from first number. Supports both integers and floating point numbers."""
    return first_number - second_number

@tool
def power(base: float, exponent: float) -> float:
    """Raise base to the power of exponent. Supports both integers and floating point numbers."""
    return base ** exponent

@tool
def square_root(number: float) -> Union[float, str]:
    """Calculate the square root of a number. Supports both integers and floating point numbers."""
    if number < 0:
        return "Error: Cannot calculate square root of negative number"
    return number ** 0.5

@tool
def absolute(number: float) -> float:
    """Get the absolute value of a number. Supports both integers and floating point numbers."""
    return abs(number)

@tool
def round_number(number: float, decimal_places: int = 2) -> float:
    """Round a number to specified decimal places. Default is 2 decimal places."""
    return round(number, decimal_places)
"""
测试目标：一个计算斐波那契数列的函数
目标：让 AI 优化这个函数的性能
"""
from functools import lru_cache

@lru_cache(maxsize=None)
def fibonacci(n):
    """计算斐波那契数列的第 n 个数"""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)


def fibonacci_list(n):
    """计算前 n 个斐波那契数列"""
    result = []
    a, b = 0, 1
    for _ in range(n):
        result.append(a)
        a, b = b, a + b
    return result


if __name__ == "__main__":
    # 测试
    print("fibonacci(10):", fibonacci(10))
    print("fibonacci_list(10):", fibonacci_list(10))

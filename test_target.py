"""
测试脚本：评估 target.py 的性能
"""

import sys
import time
import importlib.util

def load_target():
    """动态加载 target.py"""
    spec = importlib.util.spec_from_file_location("target", "target.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_correctness():
    """测试正确性"""
    m = load_target()
    
    # 测试 fibonacci
    assert m.fibonacci(0) == 0, "fibonacci(0) should be 0"
    assert m.fibonacci(1) == 1, "fibonacci(1) should be 1"
    assert m.fibonacci(10) == 55, "fibonacci(10) should be 55"
    assert m.fibonacci(20) == 6765, "fibonacci(20) should be 6765"
    
    # 测试 fibonacci_list
    assert m.fibonacci_list(5) == [0, 1, 1, 2, 3], "fibonacci_list(5)"
    assert m.fibonacci_list(10) == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34], "fibonacci_list(10)"
    
    return True

def measure_performance():
    """测量性能"""
    m = load_target()
    
    # 测量 fibonacci_list (迭代版本，应该很快)
    start = time.time()
    for _ in range(1000):
        m.fibonacci_list(1000)
    iter_time = time.time() - start
    
    # 测量 fibonacci (递归版本，很慢)
    # 只测试小数字，避免超时
    start = time.time()
    for i in range(20):
        m.fibonacci(i)
    rec_time_small = time.time() - start
    
    return {
        "iter_time": iter_time,
        "rec_time_small": rec_time_small
    }

def main():
    print("=" * 50)
    print("测试 target.py")
    print("=" * 50)
    
    # 正确性测试
    print("\n[1/2] 正确性测试...")
    try:
        test_correctness()
        print("✅ 正确性测试通过")
    except Exception as e:
        print(f"❌ 正确性测试失败: {e}")
        print("FAIL")
        sys.exit(1)
    
    # 性能测试
    print("\n[2/2] 性能测试...")
    perf = measure_performance()
    print(f"   fibonacci_list(1000) x1000: {perf['iter_time']:.4f}s")
    print(f"   fibonacci(0-19): {perf['rec_time_small']:.4f}s")
    
    # 计算一个综合分数
    # 分数 = 正确性 * (1 / (1 + time))
    score = 1000 / (1 + perf['iter_time'] + perf['rec_time_small'])
    
    print(f"\n📊 分数: {score:.2f}")
    print("PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()

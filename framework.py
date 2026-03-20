"""
AutoIter Framework - 通用 AI 迭代优化框架

核心思路来自 karpathy/autoresearch，但扩展为通用场景：
- 可以迭代优化任何文本形式的内容（代码、prompt、文章等）
- 支持多种评估方式（测试、LLM评判、规则校验）
"""

import os
import time
import subprocess
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable

# ============================================================================
# Target - 可迭代对象
# ============================================================================

class Target(ABC):
    """可迭代对象的抽象基类"""
    
    @abstractmethod
    def read(self) -> str:
        """读取当前内容"""
        pass
    
    @abstractmethod
    def write(self, content: str) -> None:
        """写入新内容"""
        pass
    
    @abstractmethod
    def description(self) -> str:
        """描述这个目标"""
        pass


class FileTarget(Target):
    """文件形式的 Target"""
    
    def __init__(self, path: str):
        self.path = Path(path)
    
    def read(self) -> str:
        return self.path.read_text()
    
    def write(self, content: str) -> None:
        self.path.write_text(content)
    
    def description(self) -> str:
        return f"文件: {self.path}"


# ============================================================================
# Evaluator - 评估器
# ============================================================================

@dataclass
class EvaluationResult:
    """评估结果"""
    score: float              # 分数（越高越好）
    metric_name: str         # 指标名称
    details: str             # 详细说明
    passed: bool             # 是否通过
    error: Optional[str] = None


class Evaluator(ABC):
    """评估器抽象基类"""
    
    @abstractmethod
    def evaluate(self, target: Target) -> EvaluationResult:
        """评估目标的质量"""
        pass
    
    @abstractmethod
    def description(self) -> str:
        """描述这个评估器"""
        pass


class TestEvaluator(Evaluator):
    """基于测试的评估器"""
    
    def __init__(self, test_func: Callable[[str], EvaluationResult]):
        self.test_func = test_func
    
    def evaluate(self, target: Target) -> EvaluationResult:
        content = target.read()
        return self.test_func(content)
    
    def description(self) -> str:
        return "测试评估器"


class CommandEvaluator(Evaluator):
    """基于命令执行的评估器"""
    
    def __init__(self, run_cmd: str, success_pattern: str = "PASS", 
                 extract_score: Optional[Callable[[str], float]] = None):
        self.run_cmd = run_cmd
        self.success_pattern = success_pattern
        self.extract_score = extract_score
    
    def evaluate(self, target: Target) -> EvaluationResult:
        try:
            result = subprocess.run(
                self.run_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            output = result.stdout + result.stderr
            
            # 检查是否成功
            passed = self.success_pattern in output
            
            # 提取分数
            if self.extract_score:
                score = self.extract_score(output)
            else:
                score = 1.0 if passed else 0.0
            
            return EvaluationResult(
                score=score,
                metric_name="test_result",
                details=output[:500],  # 截取前500字符
                passed=passed
            )
        except Exception as e:
            return EvaluationResult(
                score=0,
                metric_name="test_result",
                details=str(e),
                passed=False,
                error=str(e)
            )
    
    def description(self) -> str:
        return f"命令评估器: {self.run_cmd}"


# ============================================================================
# Agent - 修改者
# ============================================================================

class Agent(ABC):
    """Agent 抽象基类"""
    
    @abstractmethod
    def modify(self, target: Target, instruction: str) -> str:
        """根据指令修改目标"""
        pass


# ============================================================================
# Loop - 迭代控制
# ============================================================================

@dataclass
class LoopConfig:
    """循环配置"""
    max_iterations: int = 100
    time_budget_seconds: Optional[int] = None
    early_stop_no_improve: int = 10  # 连续多少次无改进后停止
    keep_if_better: bool = True


@dataclass
class IterationResult:
    """单次迭代结果"""
    iteration: int
    score: float
    previous_score: float
    improved: bool
    commit: str
    description: str
    duration_seconds: float


class AutoIterLoop:
    """迭代循环"""
    
    def __init__(self, target: Target, agent: Agent, evaluator: Evaluator,
                 config: Optional[LoopConfig] = None,
                 results_file: str = "results.tsv"):
        self.target = target
        self.agent = agent
        self.evaluator = evaluator
        self.config = config or LoopConfig()
        self.results_file = Path(results_file)
        
        # 状态
        self.best_score = float('-inf')
        self.current_score = float('-inf')
        self.no_improve_count = 0
        self.iterations = []
    
    def _init_results_file(self):
        """初始化结果文件"""
        if not self.results_file.exists():
            self.results_file.write_text("iteration\tscore\timproved\tdescription\tduration\n")
    
    def _log_result(self, result: IterationResult):
        """记录结果"""
        line = f"{result.iteration}\t{result.score:.6f}\t{result.improved}\t{result.description}\t{result.duration_seconds:.1f}\n"
        with open(self.results_file, "a") as f:
            f.write(line)
    
    def _git_commit(self, description: str) -> str:
        """Git 提交"""
        try:
            # Add changes
            subprocess.run(["git", "add", "-A"], capture_output=True)
            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", description],
                capture_output=True,
                text=True
            )
            # Get short hash
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except:
            return "no-git"
    
    def run(self, instruction: str) -> list[IterationResult]:
        """运行迭代循环"""
        self._init_results_file()
        
        print(f"🚀 开始 AutoIter 迭代")
        print(f"📋 目标: {self.target.description()}")
        print(f"📊 评估器: {self.evaluator.description()}")
        print(f"⚙️  配置: {self.config}")
        print("-" * 50)
        
        start_time = time.time()
        
        for i in range(1, self.config.max_iterations + 1):
            # 检查时间预算
            if self.config.time_budget_seconds:
                elapsed = time.time() - start_time
                if elapsed >= self.config.time_budget_seconds:
                    print(f"⏰ 达到时间预算，停止迭代")
                    break
            
            iter_start = time.time()
            print(f"\n📌 迭代 {i}/{self.config.max_iterations}")
            
            # 1. 获取当前内容
            current_content = self.target.read()
            
            # 2. 让 Agent 修改
            print(f"   🔧 Agent 正在修改...")
            new_content = self.agent.modify(self.target, instruction)
            
            # 3. 写入新内容
            self.target.write(new_content)
            
            # 4. Git 提交
            commit_hash = self._git_commit(f"Iteration {i}")
            
            # 5. 评估
            print(f"   📊 评估中...")
            eval_result = self.evaluator.evaluate(self.target)
            
            # 6. 判断是否改进
            improved = eval_result.score > self.current_score
            self.current_score = eval_result.score
            
            # 记录结果
            result = IterationResult(
                iteration=i,
                score=eval_result.score,
                previous_score=self.best_score if self.best_score != float('-inf') else 0,
                improved=improved,
                commit=commit_hash,
                description=eval_result.details[:100],
                duration_seconds=time.time() - iter_start
            )
            self.iterations.append(result)
            self._log_result(result)
            
            # 7. 如果改进，保留；否则回滚
            if improved:
                print(f"   ✅ 改进! 分数: {eval_result.score:.4f} (之前: {self.best_score:.4f})")
                self.best_score = eval_result.score
                self.no_improve_count = 0
            else:
                print(f"   ❌ 无改进，回滚")
                # 回滚到上一个版本（通过 git）
                subprocess.run(["git", "reset", "--hard", "HEAD~1"], capture_output=True)
                self.no_improve_count += 1
            
            # 8. 早停检查
            if self.no_improve_count >= self.config.early_stop_no_improve:
                print(f"🛑 连续 {self.no_improve_count} 次无改进，早停")
                break
        
        print("-" * 50)
        print(f"🎉 完成! 总迭代: {len(self.iterations)}")
        print(f"🏆 最佳分数: {self.best_score:.4f}")
        
        return self.iterations


# ============================================================================
# 便捷函数
# ============================================================================

def create_simple_loop(
    target_path: str,
    agent_modify_func: Callable[[str, str], str],
    evaluate_cmd: str,
    extract_score: Optional[Callable[[str], float]] = None,
    **config
) -> AutoIterLoop:
    """创建简单循环的便捷函数"""
    
    target = FileTarget(target_path)
    
    class SimpleAgent(Agent):
        def modify(self, target: Target, instruction: str) -> str:
            return agent_modify_func(target.read(), instruction)
    
    evaluator = CommandEvaluator(evaluate_cmd, extract_score=extract_score)
    
    return AutoIterLoop(
        target=target,
        agent=SimpleAgent(),
        evaluator=evaluator,
        config=LoopConfig(**config)
    )

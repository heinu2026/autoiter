# AutoIter

> 通用 AI 迭代优化框架 - 让 AI 自己迭代优化任何内容

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 灵感来源

本项目受 [karpathy/autoresearch](https://github.com/karpathy/autoresearch) 启发，将"让 AI 自己训练 LLM"的思路扩展为通用框架。

## 核心思路

```
修改 → 评估 → 保留/丢弃 → 重复
```

给 AI 一个可迭代的目标 + 评估标准，让它自己折腾，你来收割结果。

## 适用场景

| 场景 | Target | Evaluator |
|------|--------|-----------|
| 训练 LLM | `train.py` | val_bpb |
| 优化 Skill | skill 代码/prompt | 测试通过率 |
| 写文章 | markdown 文章 | LLM 评分 |
| 调 Prompt | system prompt | 任务成功率 |
| 优化代码 | 代码文件 | 测试用例 |

## 快速开始

### 安装

```bash
git clone https://github.com/heinu2026/autoiter.git
cd autoiter
```

### 运行测试示例

```bash
python3 test_target.py
```

这个测试会：
1. 加载 `target.py` 中的斐波那契函数
2. 运行性能测试
3. 输出分数

### 用 Agent 优化

```python
from framework import FileTarget, AutoIterLoop, LoopConfig
from your_agent import YourAgent
from your_evaluator import YourEvaluator

# 创建目标
target = FileTarget("your_target.py")

# 创建 Agent（Claude / Codex 等）
agent = YourAgent()

# 创建评估器
evaluator = YourEvaluator()

# 创建循环
loop = AutoIterLoop(
    target=target,
    agent=agent,
    evaluator=evaluator,
    config=LoopConfig(max_iterations=100, time_budget_seconds=3600)
)

# 启动！
loop.run(instruction="优化这个函数的性能")
```

## 框架设计

```
┌─────────────────────────────────────────────────┐
│                 AutoIter                         │
├─────────────────────────────────────────────────┤
│  Target (可迭代对象)                              │
│  - FileTarget: 文件形式                          │
│  - PromptTarget: prompt 文本                     │
│  - 自定义实现 Target 接口                         │
│                                                  │
│  Evaluator (评估器)                              │
│  - TestEvaluator: 运行测试用例                    │
│  - CommandEvaluator: 执行命令                     │
│  - LLMJudgeEvaluator: LLM 评判                   │
│                                                  │
│  Agent (修改者)                                  │
│  - Claude / Codex / 任何 LLM                    │
│                                                  │
│  Loop (迭代控制)                                 │
│  - 固定迭代次数                                  │
│  - 时间预算                                      │
│  - 早停策略                                      │
└─────────────────────────────────────────────────┘
```

## 核心组件

### Target

```python
class Target(ABC):
    @abstractmethod
    def read(self) -> str: ...
    
    @abstractmethod
    def write(self, content: str) -> None: ...
    
    @abstractmethod
    def description(self) -> str: ...
```

### Evaluator

```python
@dataclass
class EvaluationResult:
    score: float
    metric_name: str
    details: str
    passed: bool
    error: Optional[str] = None

class Evaluator(ABC):
    @abstractmethod
    def evaluate(self, target: Target) -> EvaluationResult: ...
```

### LoopConfig

```python
@dataclass
class LoopConfig:
    max_iterations: int = 100              # 最大迭代次数
    time_budget_seconds: Optional[int] = None  # 时间预算
    early_stop_no_improve: int = 10       # 连续多少次无改进后停止
```

## 示例：优化斐波那契函数

### 1. 准备目标文件 `target.py`

```python
def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)
```

### 2. 准备评估脚本 `test_target.py`

```python
import time
import importlib.util

def evaluate():
    spec = importlib.util.spec_from_file_location("target", "target.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    start = time.time()
    for i in range(20):
        module.fibonacci(i)
    duration = time.time() - start
    
    score = 1000 / (1 + duration)
    return score

if __name__ == "__main__":
    print(f"分数: {evaluate()}")
```

### 3. 运行

```bash
python3 test_target.py  # 初始分数 ~958
```

### 4. 让 Agent 优化

Agent 会自动发现递归版本性能差，加上 `@lru_cache` 优化。

优化后分数 ~960。

## 进阶用法

### 使用 Claude 作为 Agent

```python
import anthropic

class ClaudeAgent(Agent):
    def __init__(self, api_key):
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def modify(self, target: Target, instruction: str) -> str:
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": f"{instruction}\n\n当前代码:\n{target.read()}"}
            ]
        )
        return response.content[0].text
```

### 使用 LLM 作为评估器

```python
class LLMEvaluator(Evaluator):
    def __init__(self, agent, criteria):
        self.agent = agent
        self.criteria = criteria
    
    def evaluate(self, target: Target) -> EvaluationResult:
        prompt = f"""评估以下内容是否符合标准: {self.criteria}
        
内容:
{target.read()}
"""
        response = self.agent.ask(prompt)
        score = parse_score(response)
        return EvaluationResult(score=score, ...)
```

## TODO

- [ ] 支持更多 Target 类型（API、数据库等）
- [ ] 并行评估支持
- [ ] 可视化界面
- [ ] 历史版本对比

## License

MIT

# 核心回测功能深化设计方案

## 1. 引言

本文档旨在为 `ChronoRetrace` 项目的核心回测模块提出两项关键的功能增强：**策略参数优化**和**丰富的回测绩效指标**。这些功能将显著提升平台在策略研发和评估方面的专业性和实用性，帮助用户更科学、更高效地进行量化分析。

---

## 2. 功能一：策略参数优化 (Strategy Parameter Optimization)

### 2.1. 功能描述

允许用户对一个策略内的核心参数（如均线周期、RSI 阈值等）设定一个范围和步长，后端自动遍历所有参数组合并执行回测，最终返回一系列结果，帮助用户识别出在历史数据上表现最优的参数。

**用户场景示例：**
用户想测试一个简单的双均线金叉死叉策略，但不确定哪两个周期的组合最好。他可以将短均线的范围设为 `[5, 20]`，步长为 `5`；长均线的范围设为 `[30, 60]`，步长为 `10`。系统将自动测试 `(5, 30)`, `(5, 40)`, ..., `(20, 60)` 等所有16种组合，并告诉他哪种组合的年化收益最高。

### 2.2. 后端设计 (Backend Design)

#### 2.2.1. API 接口变更

修改现有的回测请求接口 `POST /api/v1/backtest`。

**请求体 (Request Body) 结构调整：**

在 `schemas/backtest.py` 中定义新的 Pydantic 模型。

```python
# schemas/backtest.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class StrategyParameter(BaseModel):
    name: str = Field(..., description="参数名称, e.g., 'short_ma'")
    value: Optional[Any] = Field(None, description="固定参数值")
    range: Optional[List[int]] = Field(None, description="参数范围 [start, end]")
    step: Optional[int] = Field(1, description="参数范围遍历的步长")

class BacktestRequest(BaseModel):
    code: str
    start_date: str
    end_date: str
    strategy_name: str
    strategy_params: List[StrategyParameter] # 从固定字典改为参数列表

# ... 其他模型
```

**请求示例：**

```json
{
  "code": "AAPL",
  "start_date": "2022-01-01",
  "end_date": "2023-01-01",
  "strategy_name": "DualMovingAverage",
  "strategy_params": [
    {
      "name": "short_ma",
      "range": [10, 20],
      "step": 5
    },
    {
      "name": "long_ma",
      "range": [30, 50],
      "step": 10
    }
  ]
}
```

#### 2.2.2. 服务层逻辑 (`services/backtester.py`)

`Backtester` 服务需要进行重构，以支持参数遍历。

1.  **参数解析与组合生成:**
    *   在 `run_backtest` 方法中，首先检查 `strategy_params`。
    *   识别出哪些参数是固定值，哪些是范围值。
    *   使用 `itertools.product` 等工具，根据范围和步长生成所有可能的参数组合。例如，`[{'short_ma': 10, 'long_ma': 30}, {'short_ma': 10, 'long_ma': 40}, ...]`。

2.  **循环执行回测:**
    *   遍历生成的参数组合。
    *   对每一个组合，执行现有的回测核心逻辑。
    *   为避免重复数据加载，应在循环外一次性获取股票数据。

3.  **结果聚合:**
    *   为每次回测生成一个简化的结果摘要（例如，只包含关键绩效指标和参数本身）。
    *   将所有摘要收集到一个列表中。

#### 2.2.3. 返回数据模型 (`schemas/backtest.py`)

设计新的返回模型以容纳优化结果。

```python
# schemas/backtest.py

class OptimizationResultItem(BaseModel):
    parameters: Dict[str, Any]
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float
    # ... 其他核心指标

class BacktestOptimizationResponse(BaseModel):
    optimization_results: List[OptimizationResultItem]
    best_result: OptimizationResultItem # 性能最佳的一组
```

### 2.3. 前端设计 (Frontend Design)

#### 2.3.1. UI/UX 变更 (`pages/BacktestPage.js`)

1.  **动态参数表单:**
    *   修改回测参数输入区域，允许用户为每个参数选择“固定值”或“范围”。
    *   当选择“范围”时，显示“起始值”、“结束值”和“步长”三个输入框。
    *   可以设计一个“添加参数”的按钮，动态增删策略参数。

2.  **状态管理:**
    *   使用 React State 来管理参数列表，每个参数对象包含其名称、类型（固定/范围）和对应的值。

#### 2.3.2. 数据可视化

1.  **结果表格:**
    *   收到后端的优化结果后，使用一个表格来清晰地展示所有参数组合及其对应的核心绩效指标。
    *   表格应支持按任意指标排序，方便用户找到最优组合。

2.  **热力图 (Heatmap):**
    *   如果优化涉及两个变量参数，可以使用热力图进行可视化。X轴为一个参数，Y轴为另一个参数，单元格的颜色深浅代表某个绩效指标（如夏普比率）的高低。这能非常直观地展示参数与性能的关系。可以使用 `Plotly.js` 或 `ECharts` 等库实现。

### 2.4. 潜在挑战

*   **性能问题:** 参数组合数量可能非常大，导致回测时间过长，API 请求超时。
    *   **解决方案:**
        1.  **异步任务:** 将参数优化作为后台异步任务处理。API 立即返回一个任务ID，前端通过轮询或 WebSocket 查询任务状态和最终结果。
        2.  **后端缓存:** 对已计算过的参数组合结果进行缓存。
        3.  **限制组合数量:** 在前端和后端对允许的参数组合总数设置上限。

---

## 3. 功能二：更丰富的回测绩效指标 (Richer Backtest Metrics)

### 3.1. 功能描述

在单次回测结果中，增加更多业界标准的量化策略评估指标，以提供对策略表现更全面的认知。

### 3.2. 新增指标定义

除了基础的年化收益率，至少应增加以下指标：

*   **夏普比率 (Sharpe Ratio):** `(策略年化收益率 - 无风险利率) / 收益率年化波动率`。衡量每单位风险带来的超额回报。
*   **最大回撤 (Max Drawdown):** `(回撤区间最高点净值 - 回撤区间最低点净值) / 回撤区间最高点净值`。衡量策略可能遭遇的最大资金损失。
*   **卡玛比率 (Calmar Ratio):** `策略年化收益率 / 最大回撤`。衡量收益与风险的比率。
*   **胜率 (Win Rate):** `盈利交易次数 / 总交易次数`。
*   **盈亏比 (Profit/Loss Ratio):** `平均每笔盈利金额 / 平均每笔亏损金额`。

### 3.3. 后端设计 (Backend Design)

#### 3.3.1. 服务层逻辑 (`services/backtester.py`)

1.  **引入计算库:**
    *   可以考虑引入成熟的金融分析库，如 `empyrical`，它提供了计算上述大多数指标的现成函数。
    *   如果不想引入重度依赖，也可以在 `services/data_utils.py` 或类似模块中自行实现计算逻辑。

2.  **指标计算:**
    *   在回测引擎的核心逻辑中，必须记录每一笔交易的开仓、平仓价格和时间。
    *   回测结束后，根据每日的投资组合净值序列计算**最大回撤**和**波动率**。
    *   根据交易记录列表计算**胜率**和**盈亏比**。
    *   最后，综合计算出**夏普比率**和**卡玛比率**。

#### 3.3.2. 数据模型 (`schemas/backtest.py`)

在现有的单次回测返回模型中，增加这些新指标的字段。

```python
# schemas/backtest.py

class BacktestResult(BaseModel):
    # ... 原有字段
    annualized_return: float
    cumulative_return: float
    sharpe_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    profit_loss_ratio: float
    # ... 交易详情等
```

### 3.4. 前端设计 (Frontend Design)

#### 3.4.1. UI/UX 变更 (`pages/BacktestPage.js`)

1.  **指标卡片展示:**
    *   在回测结果展示区域，使用 `components/KpiCard.js` 组件，将每个核心指标以名/值对的形式清晰地展示出来。
    *   将指标分为几类，如“收益类”、“风险类”、“交易类”，进行分组展示。

2.  **图表信息增强:**
    *   在净值曲线图上，可以考虑标注出最大回撤发生的区间。
    *   提供一个“指标解释”的提示图标（Tooltip），当用户鼠标悬停时，显示该指标的计算公式和意义。

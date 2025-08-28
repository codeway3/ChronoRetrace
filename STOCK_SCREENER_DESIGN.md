# 股票筛选器功能设计方案

## 1. 引言

为了增强 `ChronoRetrace` 平台的数据分析能力和实用性，本文档提出一个全新的核心功能：**股票筛选器 (Stock Screener)**。该功能将允许用户根据一系列自定义的基本面和技术面指标，从整个市场（初期以A股或美股为目标）中高效地筛选出符合其投资策略的股票。

---

## 2. 功能描述

股票筛选器是一个交互式工具，用户可以通过组合不同的筛选条件来缩小股票选择范围。

**核心用户流程：**
1.  用户进入“股票筛选器”页面。
2.  页面提供一个动态表单，用户可以点击“添加筛选条件”按钮。
3.  每条条件由三个部分组成：**指标** (如“市盈率 P/E”)、**操作符** (如“小于”)、**值** (如“20”)。
4.  用户可以添加多条筛选条件，所有条件将以“与”(AND) 的逻辑组合。
5.  系统根据用户设定的条件，向后端请求数据。
6.  筛选结果以可排序、可分页的表格形式实时展示在页面下方。

**初期支持的指标范围（示例）：**
*   **基本面指标:**
    *   市盈率 (P/E Ratio)
    *   市净率 (P/B Ratio)
    *   总市值 (Market Cap)
    *   股息率 (Dividend Yield)
*   **技术指标:**
    *   股价 (Price)
    *   5日均线 (MA5), 20日均线 (MA20), 60日均线 (MA60)
    *   成交量 (Volume)
    *   涨跌幅 (Percent Change)

---

## 3. 后端设计 (Backend Design)

筛选器的性能和可行性高度依赖于后端的数据准备和查询效率。实时计算全市场股票的指标是不可行的，因此需要预计算和专门的数据存储。

### 3.1. 数据库设计

新增一个核心数据表，用于存储每日更新的股票指标。

**表名:** `daily_stock_metrics`

**表结构 (Schema):**

| 字段名 (Column) | 类型 (Type) | 描述 | 索引 |
| :--- | :--- | :--- | :--- |
| `id` | Integer | 主键 | PK |
| `code` | String | 股票代码 | Indexed |
| `date` | Date | 数据日期 | Indexed |
| `market` | String | 所属市场 (e.g., 'A-Share', 'US-Stock') | Indexed |
| `close_price` | Float | 当日收盘价 | |
| `pe_ratio` | Float | 市盈率 (TTM) | Indexed |
| `pb_ratio` | Float | 市净率 | Indexed |
| `market_cap` | BigInteger | 总市值 | Indexed |
| `dividend_yield`| Float | 股息率 | Indexed |
| `ma5` | Float | 5日移动平均价 | |
| `ma20` | Float | 20日移动平均价 | |
| `volume` | BigInteger | 成交量 | |
| `updated_at` | DateTime | 记录更新时间 | |

**关键决策：**
*   **数据冗余:** 该表是为快速查询而设计的，是一种有目的的数据冗余。
*   **索引:** 在所有可供筛选的字段上建立数据库索引是保证查询性能的关键。

### 3.2. 数据更新机制 (Background Job)

需要一个后台定时任务，在每个交易日结束后执行。

*   **任务类型:** 可以是一个独立的 Python 脚本，通过 Cron Job 调度；或者使用更健壮的任务队列，如 Celery。
*   **任务流程:**
    1.  获取全市场股票列表。
    2.  遍历每只股票。
    3.  调用现有的数据获取服务 (`a_share_fetcher`, `us_stock_fetcher`) 获取最新的行情和基本面数据。
    4.  计算所有需要的技术指标（如均线）。
    5.  将计算和获取到的最新指标数据 `INSERT` 或 `UPDATE` 到 `daily_stock_metrics` 表中。

### 3.3. API 接口设计

创建一个新的 API endpoint 来处理筛选请求。

**Endpoint:** `POST /api/v1/screener/stocks`

*   **方法:** 使用 `POST` 而不是 `GET`，因为筛选条件组合可能非常复杂，不适合放在 URL 参数中。

**请求体 (Request Body) Pydantic 模型 (`schemas/stock.py`):**

```python
# schemas/stock.py

from pydantic import BaseModel, Field
from typing import List, Any

class ScreenerCondition(BaseModel):
    field: str = Field(..., description="要筛选的字段, e.g., 'pe_ratio'")
    operator: str = Field(..., description="操作符, e.g., 'gt', 'lt', 'eq', 'gte', 'lte'")
    value: Any = Field(..., description="要比较的值")

class StockScreenerRequest(BaseModel):
    market: str = Field('A-Share', description="目标市场")
    conditions: List[ScreenerCondition]
    page: int = 1
    size: int = 20
```

**返回体 (Response Body) Pydantic 模型:**

```python
# schemas/stock.py

class ScreenedStock(BaseModel):
    code: str
    name: str
    # ... 其他希望在结果列表中展示的字段
    pe_ratio: float
    market_cap: int

class StockScreenerResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[ScreenedStock]
```

### 3.4. 服务层逻辑 (`services/screener_service.py`)

创建一个新的服务来处理筛选逻辑。

1.  **接收请求:** 接收 `StockScreenerRequest` 对象。
2.  **动态查询构建:**
    *   使用 SQLAlchemy 核心表达式语言或 ORM，动态构建数据库查询。
    *   遍历 `conditions` 列表，将每个条件转换为一个 SQLAlchemy 的 `where` 子句。例如，`{'field': 'pe_ratio', 'operator': 'lt', 'value': 20}` 会被转换为 `daily_stock_metrics.c.pe_ratio < 20`。
    *   将所有子句用 `and_()` 连接起来。
3.  **执行查询:**
    *   首先执行一个 `count()` 查询以获取满足条件的总记录数，用于分页。
    *   然后执行主查询，应用 `limit()` 和 `offset()` 进行分页，并获取股票数据。
4.  **返回结果:** 将查询结果构造成 `StockScreenerResponse` 对象并返回。

---

## 4. 前端设计 (Frontend Design)

### 4.1. 页面与组件

1.  **新页面:** `pages/ScreenerPage.js`
    *   作为筛选器功能的主容器。
    *   管理筛选条件的状态和分页状态。
    *   调用 API 并在条件变化时重新获取数据。

2.  **新组件:** `components/FilterBuilder.js`
    *   负责筛选条件的动态添加、修改和删除。
    *   内部维护一个条件列表的状态，当状态变更时，通过回调函数通知父页面。

3.  **复用组件:** `components/TransactionsTable.js` (或创建一个类似的 `DataTable` 组件)
    *   用于展示筛选出的股票列表。
    *   需要支持分页和点击表头排序的功能。

### 4.2. UI/UX 流程

1.  **初始化:** 页面加载时，筛选条件为空，结果列表也为空或显示提示信息。
2.  **添加条件:** 用户点击“添加条件”按钮，`FilterBuilder` 组件中新增一行。
3.  **配置条件:**
    *   第一个下拉框选择**指标**（如“市盈率”）。
    *   第二个下拉框选择**操作符**（如“大于”）。
    *   第三个输入框填写**数值**。
4.  **触发搜索:**
    *   可以设计成“自动触发”：任何条件的改变都会立刻重新发起 API 请求。为防止频繁请求，需要加入防抖 (debounce) 逻辑。
    *   或者设计成“手动触发”：用户配置好所有条件后，点击一个“开始筛选”按钮。
5.  **展示结果:**
    *   API 返回数据后，更新结果表格。
    *   表格下方显示分页控件，告知用户总结果数和当前页码。

---

## 5. 潜在挑战与优化

*   **数据质量与覆盖范围:** 筛选器的价值直接取决于 `daily_stock_metrics` 表中数据的质量和广度。需要确保数据源稳定可靠。
*   **复杂查询:** V1 版本只支持 `AND` 逻辑。未来可以扩展支持 `OR` 和括号分组，但这会显著增加后端查询构建和前端 UI 的复杂度。
*   **性能:** 随着股票数量和历史数据的增多，`daily_stock_metrics` 表会变得非常大。必须确保所有用于筛选的字段都已正确建立数据库索引。

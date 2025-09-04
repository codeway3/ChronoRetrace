# 数据校验与去重模块

## 概述

数据校验与去重模块是ChronoRetrace系统的核心数据质量保障组件，提供全面的数据有效性验证、智能去重处理、错误处理机制和结构化日志记录功能。该模块具备良好的可扩展性和高性能表现，支持批量处理、并行处理和异步操作。

## 核心功能

### 1. 数据有效性验证
- **格式校验**: 股票代码、日期格式、数值格式等
- **类型校验**: 数据类型检查和转换
- **范围校验**: 价格、成交量、比率等数值范围验证
- **逻辑校验**: 价格关系、涨跌幅计算等业务逻辑验证
- **质量评分**: 基于多维度指标的数据质量评分

### 2. 智能去重处理
- **完全重复**: 所有字段完全相同的记录
- **部分重复**: 关键字段相同但其他字段不同的记录
- **相似重复**: 基于相似度算法识别的近似重复记录
- **多种策略**: 保留第一条、最后一条、质量最高或合并策略
- **批量处理**: 支持大数据集的高效去重

### 3. 错误处理机制
- **分级处理**: 错误、警告、信息三级处理
- **上下文记录**: 详细的错误上下文信息
- **友好提示**: 用户友好的错误信息和建议操作
- **异常恢复**: 系统异常的自动恢复机制

### 4. 结构化日志记录
- **操作追踪**: 完整的数据处理过程记录
- **性能监控**: 处理时间、内存使用等性能指标
- **统计分析**: 数据质量趋势和统计信息
- **多重输出**: 文件日志和数据库日志双重保障

## 模块结构

```
app/services/
├── data_quality_manager.py          # 主管理器，统一入口
├── data_validation_service.py       # 数据校验服务
├── data_deduplication_service.py    # 数据去重服务
├── error_handling_service.py        # 错误处理服务
├── logging_service.py               # 日志记录服务
├── performance_optimization_service.py  # 性能优化服务
└── README_data_quality.md           # 本文档

tests/
├── test_data_validation_service.py      # 数据校验测试
├── test_data_deduplication_service.py   # 数据去重测试
├── test_performance_optimization_service.py  # 性能优化测试
└── test_data_quality_integration.py     # 集成测试
```

## 快速开始

### 基本使用

```python
from app.services.data_quality_manager import DataQualityManager, DataQualityConfig
from app.db.session import get_db_session

# 获取数据库会话
session = get_db_session()

# 创建数据质量管理器
manager = DataQualityManager(session)

# 准备测试数据
data = [
    {
        'stock_code': '000001',
        'trade_date': '2024-01-15',
        'open_price': 10.0,
        'close_price': 10.5,
        'high_price': 11.0,
        'low_price': 9.5,
        'volume': 1000000,
        'turnover': 10000000.0
    },
    # 更多数据...
]

# 执行数据质量处理
result = manager.process_data(data, 'A_share')

# 检查结果
if result.success:
    print(f"处理成功: {result.valid_records}/{result.total_records} 条有效数据")
    print(f"质量评分: {result.quality_score:.2f}")
    print(f"处理时间: {result.processing_time:.2f}秒")
else:
    print(f"处理失败: {result.error_messages}")
```

### 自定义配置

```python
from app.services.data_deduplication_service import DeduplicationStrategy
from app.services.performance_optimization_service import ProcessingMode

# 自定义配置
config = DataQualityConfig(
    enable_validation=True,
    enable_deduplication=True,
    enable_performance_optimization=True,
    deduplication_strategy=DeduplicationStrategy.KEEP_HIGHEST_QUALITY,
    batch_size=200,
    max_workers=8,
    processing_mode=ProcessingMode.PARALLEL,
    log_level='DEBUG'
)

# 使用自定义配置创建管理器
manager = DataQualityManager(session, config)
```

### 单独使用各个服务

```python
# 仅数据校验
validation_reports = manager.validate_only(data, 'A_share')
for report in validation_reports:
    if not report.is_valid:
        print(f"校验失败: {report.errors}")

# 仅数据去重
from app.services.data_deduplication_service import DeduplicationStrategy
dedup_report = manager.deduplicate_only(data, DeduplicationStrategy.KEEP_FIRST)
print(f"去重完成: 移除 {dedup_report.duplicates_removed} 条重复数据")
```

### 上下文管理器使用

```python
# 自动资源管理
with DataQualityManager(session, config) as manager:
    result = manager.process_data(data, 'A_share')
    # 资源会自动清理
```

## 高级功能

### 性能优化

模块支持多种性能优化策略：

1. **批量处理**: 将大数据集分批处理，减少内存占用
2. **并行处理**: 利用多核CPU并行处理数据
3. **异步处理**: 支持异步操作，提高系统响应性
4. **内存管理**: 智能内存管理，防止内存溢出
5. **缓存机制**: 缓存常用数据和计算结果

```python
# 高性能配置示例
high_perf_config = DataQualityConfig(
    batch_size=500,
    max_workers=16,
    processing_mode=ProcessingMode.PARALLEL,
    enable_performance_optimization=True
)
```

### 自定义校验规则

```python
# 自定义校验规则
custom_rules = {
    'stock_code_pattern': r'^\d{6}$',
    'price_min': 0.01,
    'price_max': 10000.0,
    'volume_min': 0,
    'pe_ratio_max': 1000.0
}

config = DataQualityConfig(
    validation_rules=custom_rules
)
```

### 监控和统计

```python
# 获取质量统计信息
stats = manager.get_quality_statistics()
print(f"总处理记录数: {stats.get('total_operations', 0)}")
print(f"成功率: {stats.get('success_rate', 0):.2%}")
print(f"平均处理时间: {stats.get('avg_processing_time', 0):.2f}秒")
```

## 数据模型扩展

模块为数据库模型添加了质量追踪字段：

```python
# DailyStockMetrics 模型新增字段
data_source: str           # 数据来源
quality_score: float       # 质量评分 (0.0-1.0)
validation_status: str     # 校验状态
last_validated: datetime   # 最后校验时间
is_duplicate: bool         # 是否重复
duplicate_source: str      # 重复来源

# DataQualityLog 新模型
record_id: str            # 记录ID
table_name: str           # 表名
operation_type: str       # 操作类型
status: str              # 状态
message: str             # 消息
error_details: JSON      # 错误详情
execution_time: float    # 执行时间
created_at: datetime     # 创建时间
```

## 测试

### 运行单元测试

```bash
# 运行所有测试
python -m pytest backend/tests/test_data_*

# 运行特定测试
python -m pytest backend/tests/test_data_validation_service.py
python -m pytest backend/tests/test_data_deduplication_service.py
python -m pytest backend/tests/test_data_quality_integration.py

# 运行测试并生成覆盖率报告
python -m pytest backend/tests/test_data_* --cov=app.services --cov-report=html
```

### 性能测试

```python
# 性能基准测试
import time
from app.services.data_quality_manager import quick_quality_check

# 生成大数据集
large_dataset = generate_test_data(10000)  # 1万条记录

start_time = time.time()
result = quick_quality_check(session, large_dataset)
end_time = time.time()

print(f"处理 {len(large_dataset)} 条记录耗时: {end_time - start_time:.2f}秒")
print(f"处理速度: {len(large_dataset) / (end_time - start_time):.0f} 记录/秒")
```

## 最佳实践

### 1. 配置优化
- 根据数据量调整批处理大小
- 根据服务器配置设置工作线程数
- 在生产环境中启用性能优化
- 合理设置日志级别

### 2. 错误处理
- 始终检查处理结果的success字段
- 记录和分析错误信息
- 实施适当的重试机制
- 监控系统资源使用情况

### 3. 性能监控
- 定期检查处理性能指标
- 监控内存使用情况
- 分析数据质量趋势
- 优化数据库查询

### 4. 数据质量管理
- 建立数据质量标准
- 定期执行数据质量检查
- 跟踪数据质量改进情况
- 建立数据质量报告机制

## 故障排除

### 常见问题

1. **内存不足**
   - 减少批处理大小
   - 启用内存管理
   - 检查数据集大小

2. **处理速度慢**
   - 启用并行处理
   - 增加工作线程数
   - 优化数据库连接

3. **校验失败率高**
   - 检查校验规则设置
   - 分析数据源质量
   - 调整校验阈值

4. **去重效果不佳**
   - 调整相似度阈值
   - 选择合适的去重策略
   - 检查数据特征

### 日志分析

```python
# 查看详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 分析错误日志
from app.services.logging_service import LogStatus
error_logs = logging_service.get_logs_by_status(LogStatus.ERROR)
for log in error_logs:
    print(f"错误时间: {log.created_at}")
    print(f"错误信息: {log.message}")
    print(f"错误详情: {log.error_details}")
```

## 扩展开发

### 添加新的校验规则

```python
# 在 DataValidationService 中添加新方法
def validate_custom_field(self, value: Any, field_name: str) -> ValidationResult:
    """自定义字段校验"""
    # 实现自定义校验逻辑
    pass
```

### 添加新的去重策略

```python
# 在 DeduplicationStrategy 枚举中添加新策略
class DeduplicationStrategy(Enum):
    KEEP_FIRST = "keep_first"
    KEEP_LAST = "keep_last"
    KEEP_HIGHEST_QUALITY = "keep_highest_quality"
    MERGE_RECORDS = "merge_records"
    CUSTOM_STRATEGY = "custom_strategy"  # 新策略
```

### 集成外部服务

```python
# 集成外部数据质量服务
class ExternalQualityService:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        # 调用外部API进行校验
        pass
```

## 版本历史

- **v1.0.0**: 初始版本，包含基础校验和去重功能
- **v1.1.0**: 添加性能优化和并行处理支持
- **v1.2.0**: 增强错误处理和日志记录功能
- **v1.3.0**: 添加集成测试和性能监控

## 贡献指南

1. Fork 项目仓库
2. 创建功能分支
3. 编写测试用例
4. 实现功能代码
5. 运行所有测试
6. 提交 Pull Request

## 许可证

本模块遵循项目的整体许可证协议。
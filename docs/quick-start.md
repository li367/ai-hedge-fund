# AI对冲基金 - 快速入门指南

## 前提条件

- Python 3.9+
- Poetry (依赖管理工具)
- 交易所账户 (OKX, Binance等)
- LLM API密钥 (OpenAI, Anthropic等)

## 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/yourusername/ai-hedge-fund.git
   cd ai-hedge-fund
   ```

2. **安装依赖**
   ```bash
   poetry install
   ```

3. **配置环境变量**
   ```bash
   cp .env.example .env
   ```
   然后编辑`.env`文件，填入您的API密钥和其他配置信息。

## 使用方法

### 初始设置

1. **配置交易所**
   在`.env`文件中设置交易所API密钥和密码：
   ```
   OKX_API_KEY=your_api_key
   OKX_SECRET_KEY=your_secret_key
   OKX_PASSPHRASE=your_passphrase
   ```

2. **配置LLM**
   选择您想使用的LLM提供商并设置API密钥：
   ```
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-4
   OPENAI_API_KEY=your_openai_key
   ```

3. **设置交易参数**
   调整风险级别、仓位大小和止损止盈设置：
   ```
   RISK_LEVEL=medium
   MAX_POSITION_SIZE=10000
   STOP_LOSS_PERCENTAGE=2
   TAKE_PROFIT_PERCENTAGE=5
   ```

### 运行实时交易系统

```bash
poetry run python src/main.py
```

这将启动交易系统，连接到指定的交易所，并根据配置的策略开始监控市场和执行交易。

### 运行回测

使用历史数据评估您的策略性能：

```bash
poetry run python src/backtester.py
```

回测程序会提示您选择要测试的策略、时间范围和其他参数。

## 模块使用示例

### 示例1: 配置LLM策略

```python
from crypto.strategies.llm_strategy import LLMStrategy
from crypto.exchanges.okx import OKXExchange
from crypto.risk_manager import RiskManager

# 初始化交易所
exchange = OKXExchange(api_key="your_api_key", secret_key="your_secret_key", passphrase="your_passphrase")

# 初始化风险管理器
risk_manager = RiskManager(max_position_size=10000, stop_loss_percentage=2, take_profit_percentage=5)

# 创建LLM策略
strategy = LLMStrategy(
    exchange=exchange,
    risk_manager=risk_manager,
    symbol="BTC/USDT",
    model_name="gpt-4",
    model_provider="openai",
    timeframe="1h",
    news_lookback_hours=24,
    initial_capital=10000
)

# 分析市场并获取交易建议
analysis = await strategy.analyze_market()
print(f"市场分析结果: {analysis}")
```

### 示例2: 使用Warren Buffett代理分析股票

```python
from graph.state import AgentState
from agents.warren_buffett import warren_buffett_agent

# 准备数据状态
state = AgentState({
    "data": {
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "end_date": "2023-12-31"
    }
})

# 运行巴菲特代理
results = warren_buffett_agent(state)

# 查看分析结果
for ticker, analysis in results.items():
    print(f"{ticker} 分析:")
    print(f"信号: {analysis.signal}")
    print(f"信心度: {analysis.confidence}")
    print(f"理由: {analysis.reasoning}")
    print("-" * 40)
```

## 常见问题

### 1. 如何添加新的交易所?

创建一个新的交易所类，继承自`BaseExchange`并实现所有必需的方法：

```python
from crypto.exchanges.base import BaseExchange

class NewExchange(BaseExchange):
    def _initialize_exchange(self):
        # 实现交易所初始化逻辑
        pass
        
    async def get_balance(self):
        # 实现获取余额逻辑
        pass
        
    # 实现其他必需方法...
```

### 2. 如何创建自定义策略?

创建一个新的策略类，实现`analyze_market`和`execute_trades`方法：

```python
class MyCustomStrategy:
    def __init__(self, exchange, risk_manager, symbol):
        self.exchange = exchange
        self.risk_manager = risk_manager
        self.symbol = symbol
        
    async def analyze_market(self):
        # 实现市场分析逻辑
        pass
        
    async def execute_trades(self, analysis):
        # 实现交易执行逻辑
        pass
```

### 3. 遇到API限制怎么办?

系统内置了缓存机制来减少API调用。您可以通过调整以下参数来进一步优化:

- 在LLM策略中设置`use_cache=True`和较长的`cache_expire_minutes`
- 减少数据轮询频率
- 实现本地数据存储而不是频繁请求外部API

## 支持

如果您有任何问题或需要帮助，请提交GitHub Issue或联系项目维护者。
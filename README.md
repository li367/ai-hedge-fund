# AI 对冲基金

AI 驱动的股票交易和回测系统。利用多个 AI 分析师生成交易信号，并通过投资组合管理进行执行。

## 特点

- 自动股票交易和回测
- 多个 AI 分析师生成交易信号
- 风险管理
- 投资组合优化
- 支持中英文界面

## 快速开始

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 运行主程序

```bash
python src/main.py
```

## 开发

### 运行测试

项目包含单元测试以确保代码质量。

```bash
# 运行所有测试
python -m unittest discover tests

# 运行特定测试
python -m unittest tests.test_logger
```

#### 常见测试问题及解决方案

1. **文件锁定错误**：在 Windows 上运行测试时可能会遇到文件锁定问题，这通常是由于日志文件尚未关闭。解决方法：
   ```python
   # 在 tearDown 方法中添加
   import logging
   logging.shutdown()  # 关闭所有日志处理器
   ```

2. **导入错误**：如果遇到 `ModuleNotFoundError` 错误，可能是由于相对导入路径问题。解决方法：
   - 使用 `fix_imports.py` 脚本修复导入路径
   - 手动将导入路径从 `from xxx import yyy` 修改为 `from src.xxx import yyy`

3. **编码问题**：处理中文日志时可能遇到编码问题。解决方法：
   ```python
   # 读取文件时指定 UTF-8 编码
   with open(filename, 'r', encoding='utf-8') as f:
       content = f.read()
   ```

### 修复导入问题

项目提供了自动修复导入路径的工具脚本。当遇到 `ModuleNotFoundError` 错误时，可以尝试运行：

```bash
python fix_imports.py
```

该脚本会自动扫描 `src` 目录下的所有 `.py` 文件，并将所有相对导入（如 `from utils.xxx`）修改为绝对导入（如 `from src.utils.xxx`）。

### 模块结构

项目遵循以下模块导入规范：

- 在 `src` 目录外的文件（如测试）应使用绝对导入：`from src.xxx import yyy`
- 在 `src` 目录内的文件可以使用相对导入：`from .xxx import yyy` 或绝对导入

## 项目结构

```
ai-hedge-fund/
├── src/                # 主代码目录
│   ├── agents/         # AI 分析师代理
│   │   ├── risk_manager.py  # 风险管理代理
│   │   ├── portfolio_manager.py  # 投资组合管理代理
│   │   ├── warren_buffett.py  # 沃伦·巴菲特风格代理
│   │   ├── technicals.py  # 技术分析代理
│   │   └── ...        # 更多分析师代理
│   ├── data/           # 数据处理模块
│   ├── graph/          # 代理工作流图
│   │   ├── state.py    # 状态管理
│   │   └── workflow.py # 工作流定义
│   ├── llm/            # 语言模型接口
│   ├── tools/          # API 和工具
│   ├── utils/          # 实用工具
│   │   ├── logger.py   # 日志模块
│   │   └── ...        # 其他工具
│   ├── main.py         # 主程序
│   └── backtester.py   # 回测系统
├── tests/              # 测试代码
│   ├── test_logger.py  # 日志模块测试
│   ├── test_agents.py  # 代理模块测试
│   └── ...            # 其他测试
├── locales/            # 国际化文件
├── logs/               # 日志目录
├── fix_imports.py      # 导入路径修复工具
└── README.md           # 项目说明文档
```

## 开源协议

MIT

## 免责声明

本项目**仅供教育和研究目的**。

- 不适用于实际交易或投资
- 不提供任何保证或担保
- 过去的表现不代表未来的结果
- 创建者不对财务损失承担任何责任
- 投资决策请咨询财务顾问

使用本软件即表示您同意仅将其用于学习目的。

## 目录
- [设置](#setup)
- [使用方法](#usage)
  - [运行对冲基金](#running-the-hedge-fund)
  - [运行回测器](#running-the-backtester)
- [项目结构](#project-structure)
- [贡献](#contributing)
- [功能请求](#feature-requests)
- [许可证](#license)

## 设置

Clone the repository:
```bash
git clone https://github.com/virattt/ai-hedge-fund.git
cd ai-hedge-fund
```

1. Install Poetry (if not already installed):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Install dependencies:
```bash
poetry install
```

3. Set up your environment variables:
```bash
# Create .env file for your API keys
cp .env.example .env
```

4. Set your API keys:
```bash
# For running LLMs hosted by openai (gpt-4o, gpt-4o-mini, etc.)
# Get your OpenAI API key from https://platform.openai.com/
OPENAI_API_KEY=your-openai-api-key

# For running LLMs hosted by groq (deepseek, llama3, etc.)
# Get your Groq API key from https://groq.com/
GROQ_API_KEY=your-groq-api-key

# For getting financial data to power the hedge fund
# Get your Financial Datasets API key from https://financialdatasets.ai/
FINANCIAL_DATASETS_API_KEY=your-financial-datasets-api-key
```

**Important**: You must set `OPENAI_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, or `DEEPSEEK_API_KEY` for the hedge fund to work.  If you want to use LLMs from all providers, you will need to set all API keys.

Financial data for AAPL, GOOGL, MSFT, NVDA, and TSLA is free and does not require an API key.

For any other ticker, you will need to set the `FINANCIAL_DATASETS_API_KEY` in the .env file.

## Usage

### Running the Hedge Fund
```bash
poetry run python src/main.py --ticker AAPL,MSFT,NVDA
```

**Example Output:**
<img width="992" alt="Screenshot 2025-01-06 at 5 50 17 PM" src="https://github.com/user-attachments/assets/e8ca04bf-9989-4a7d-a8b4-34e04666663b" />

You can also specify a `--ollama` flag to run the AI hedge fund using local LLMs.

```bash
poetry run python src/main.py --ticker AAPL,MSFT,NVDA --ollama
```

You can also specify a `--show-reasoning` flag to print the reasoning of each agent to the console.

```bash
poetry run python src/main.py --ticker AAPL,MSFT,NVDA --show-reasoning
```
You can optionally specify the start and end dates to make decisions for a specific time period.

```bash
poetry run python src/main.py --ticker AAPL,MSFT,NVDA --start-date 2024-01-01 --end-date 2024-03-01 
```

### Running the Backtester

```bash
poetry run python src/backtester.py --ticker AAPL,MSFT,NVDA
```

**Example Output:**
<img width="941" alt="Screenshot 2025-01-06 at 5 47 52 PM" src="https://github.com/user-attachments/assets/00e794ea-8628-44e6-9a84-8f8a31ad3b47" />


You can optionally specify the start and end dates to backtest over a specific time period.

```bash
poetry run python src/backtester.py --ticker AAPL,MSFT,NVDA --start-date 2024-01-01 --end-date 2024-03-01
```

You can also specify a `--ollama` flag to run the backtester using local LLMs.
```bash
poetry run python src/backtester.py --ticker AAPL,MSFT,NVDA --ollama
```


## Project Structure 
```
ai-hedge-fund/
├── src/
│   ├── agents/                   # Agent definitions and workflow
│   │   ├── bill_ackman.py        # Bill Ackman agent
│   │   ├── fundamentals.py       # Fundamental analysis agent
│   │   ├── portfolio_manager.py  # Portfolio management agent
│   │   ├── risk_manager.py       # Risk management agent
│   │   ├── sentiment.py          # Sentiment analysis agent
│   │   ├── technicals.py         # Technical analysis agent
│   │   ├── valuation.py          # Valuation analysis agent
│   │   ├── ...                   # Other agents
│   │   ├── warren_buffett.py     # Warren Buffett agent
│   │   ├── ...                   # Additional agents
│   │   └── ...                   # ...
│   ├── tools/                    # Agent tools
│   │   ├── api.py                # API tools
│   │   └── ...                   # Additional tools
│   ├── backtester.py             # Backtesting tools
│   ├── main.py # Main entry point
├── pyproject.toml
├── tests/                      # Test code
├── locales/                    # Internationalization files
└── logs/                       # Log directory
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

**Important**: Please keep your pull requests small and focused.  This will make it easier to review and merge.

## Feature Requests

If you have a feature request, please open an [issue](https://github.com/virattt/ai-hedge-fund/issues) and make sure it is tagged with `enhancement`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

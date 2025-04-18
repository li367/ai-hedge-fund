# AI 对冲基金

这是一个 AI 驱动的对冲基金的概念验证。该项目的目标是探索使用 AI 进行交易决策。本项目**仅供教育**目的，不适用于实际交易或投资。

该系统由多个协同工作的智能体组成：

1. 本杰明·格雷厄姆智能体 - 价值投资之父，只购买具有安全边际的隐藏宝石
2. 比尔·阿克曼智能体 - 激进投资者，采取大胆立场并推动变革
3. 凯茜·伍德智能体 - 成长型投资女王，相信创新和颠覆的力量
4. 查理·芒格智能体 - 沃伦·巴菲特的合伙人，只以合理价格购买优质企业
5. 迈克尔·伯里智能体 - 《大空头》中的逆势者，寻找深度价值
6. 彼得·林奇智能体 - 务实投资者，在日常企业中寻找"十倍股"
7. 菲利普·费舍尔智能体 - 细致的成长型投资者，使用深度"小道消息"研究
8. 斯坦利·德鲁肯米勒智能体 - 宏观传奇人物，寻找具有增长潜力的不对称机会
9. 沃伦·巴菲特智能体 - 奥马哈的先知，以合理价格寻找优质公司
10. 估值智能体 - 计算股票内在价值并生成交易信号
11. 情绪智能体 - 分析市场情绪并生成交易信号
12. 基本面智能体 - 分析基本面数据并生成交易信号
13. 技术面智能体 - 分析技术指标并生成交易信号
14. 风险管理器 - 计算风险指标并设置仓位限制
15. 投资组合管理器 - 做出最终交易决策并生成订单
    
<img width="1042" alt="Screenshot 2025-03-22 at 6 19 07 PM" src="https://github.com/user-attachments/assets/cbae3dcf-b571-490d-b0ad-3f0f035ac0d4" />


**注意**：系统模拟交易决策，不进行实际交易。

[![Twitter Follow](https://img.shields.io/twitter/follow/virattt?style=social)](https://twitter.com/virattt)

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
│   ├── tools/                    # Agent tools
│   │   ├── api.py                # API tools
│   ├── backtester.py             # Backtesting tools
│   ├── main.py # Main entry point
├── pyproject.toml
├── ...
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

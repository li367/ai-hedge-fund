# AI对冲基金

一个基于大型语言模型(LLM)的智能交易系统，将AI技术与金融分析结合起来创建一个自动化的交易平台。

## 项目概述

AI对冲基金是一个利用人工智能技术，特别是大型语言模型(LLM)进行市场分析和交易决策的系统。该项目模拟了多位知名投资者的策略，并结合了实时市场数据、新闻分析和技术指标，为用户提供智能化的交易建议和自动执行交易的能力。

## 主要功能

- **多交易所支持**：集成OKX、Binance等主流加密货币交易所
- **LLM驱动的策略**：使用OpenAI、Anthropic、通义千问等大型语言模型分析市场
- **多样化代理**：实现了多位知名投资者(巴菲特、芒格、艾克曼等)的投资策略
- **全面的回测系统**：对策略进行历史回测并评估表现
- **风险管理**：内置风险控制机制确保交易安全
- **实时市场分析**：分析最新市场数据和新闻

## 项目结构

```
ai-hedge-fund/
├── src/                   # 主要源代码
│   ├── agents/            # 投资代理实现(巴菲特、芒格等)
│   ├── crypto/            # 加密货币交易相关
│   │   ├── exchanges/     # 交易所API实现
│   │   └── strategies/    # 交易策略实现
│   ├── data/              # 数据处理
│   ├── graph/             # 图表和可视化
│   ├── llm/               # 大型语言模型集成
│   ├── models/            # 机器学习模型
│   ├── tools/             # 工具和API
│   └── utils/             # 通用功能和辅助类
├── cache/                 # 缓存目录
└── logs/                  # 日志目录
```

## 安装指南

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/ai-hedge-fund.git
cd ai-hedge-fund
```

2. 使用Poetry安装依赖：
```bash
poetry install
```

3. 配置环境变量：
```bash
cp .env.example .env
# 编辑.env文件添加您的API密钥
```

## 使用方法

### 启动交易系统
```bash
poetry run python src/main.py
```

### 运行回测
```bash
poetry run python src/backtester.py
```

## 配置说明

在`.env`文件中配置以下信息：

- 交易所API密钥(OKX, Binance等)
- LLM API密钥(OpenAI, Anthropic等)
- 交易参数(风险级别, 最大仓位等)
- 模型参数

## 贡献指南

1. Fork本仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启Pull Request

## 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情
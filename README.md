# AI Hedge Fund

这是一个基于AI的对冲基金项目，使用先进的机器学习算法进行金融市场分析和交易。

## 项目结构

- `src/`: 源代码目录
- `.env.example`: 环境变量示例文件
- `pyproject.toml`: Python项目依赖配置
- `poetry.lock`: 依赖版本锁定文件

## 安装和设置

1. 克隆仓库
2. 删除现有的 lock 文件
3. 重新生成 lock 文件并安装依赖：`poetry lock` 和 `poetry install`
4. 复制 `.env.example` 到 `.env` 并填写配置
5. 运行项目：`poetry run python src/main.py`
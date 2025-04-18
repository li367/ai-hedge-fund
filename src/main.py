import argparse
import json
import sys
from datetime import datetime

import questionary
from colorama import Fore, Style, init
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from src.agents.portfolio_manager import portfolio_management_agent
from src.agents.risk_manager import risk_management_agent
from src.graph.state import AgentState
from src.llm.models import (LLM_ORDER, OLLAMA_LLM_ORDER, ModelProvider,
                        get_model_info)
from src.utils.analysts import ANALYST_ORDER, get_analyst_nodes
from src.utils.display import print_trading_output
from src.utils.i18n import _, get_current_language, set_language, load_all_languages
from src.utils.logger import get_logger
from src.utils.ollama import ensure_ollama_and_model
from src.utils.progress import progress
from src.utils.visualize import save_graph_as_png

# 获取日志记录器
logger = get_logger("main")

# 加载环境变量
load_dotenv()

# 初始化colorama
init(autoreset=True)

# 加载所有语言文件
load_all_languages()


def parse_hedge_fund_response(response):
    """解析JSON字符串并返回字典。"""
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        logger.error(_("error.json_decode", error=str(e), response=repr(response)))
        return None
    except TypeError as e:
        logger.error(_("error.invalid_type", type=type(response).__name__, error=str(e)))
        return None
    except Exception as e:
        logger.error(_("error.unexpected", error=str(e), response=repr(response)))
        return None


##### 运行对冲基金 #####
def run_hedge_fund(
    tickers: list[str],
    start_date: str,
    end_date: str,
    portfolio: dict,
    show_reasoning: bool = False,
    selected_analysts: list[str] = [],
    model_name: str = "gpt-4o",
    model_provider: str = "OpenAI",
):
    # 开始进度跟踪
    progress.start()

    try:
        # 如果分析师已自定义，创建新的工作流
        if selected_analysts:
            workflow = create_workflow(selected_analysts)
            agent = workflow.compile()
        else:
            agent = app

        final_state = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="Make trading decisions based on the provided data.",
                    )
                ],
                "data": {
                    "tickers": tickers,
                    "portfolio": portfolio,
                    "start_date": start_date,
                    "end_date": end_date,
                    "analyst_signals": {},
                },
                "metadata": {
                    "show_reasoning": show_reasoning,
                    "model_name": model_name,
                    "model_provider": model_provider,
                },
            },
        )

        return {
            "decisions": parse_hedge_fund_response(final_state["messages"][-1].content),
            "analyst_signals": final_state["data"]["analyst_signals"],
        }
    finally:
        # 停止进度跟踪
        progress.stop()


# 适配函数，使LangGraph工作流能够与Backtester兼容
def agent_adapter(
    tickers: list[str],
    start_date: str,
    end_date: str,
    portfolio: dict,
    model_name: str = "gpt-4o",
    model_provider: str = "OpenAI",
    selected_analysts: list[str] = [],
):
    """
    适配器函数，将LangGraph工作流适配为Backtester所需的函数签名。
    """
    # 创建并编译工作流
    workflow = create_workflow(selected_analysts)
    agent = workflow.compile()
    
    # 调用工作流
    final_state = agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Make trading decisions based on the provided data.",
                )
            ],
            "data": {
                "tickers": tickers,
                "portfolio": portfolio,
                "start_date": start_date,
                "end_date": end_date,
                "analyst_signals": {},
            },
            "metadata": {
                "show_reasoning": False,  # 回测模式下不显示推理过程
                "model_name": model_name,
                "model_provider": model_provider,
            },
        },
    )
    
    # 返回结果
    return {
        "decisions": parse_hedge_fund_response(final_state["messages"][-1].content),
        "analyst_signals": final_state["data"]["analyst_signals"],
    }


def start(state: AgentState):
    """使用输入消息初始化工作流。"""
    return state


def create_workflow(selected_analysts=None):
    """创建使用选定分析师的工作流。"""
    workflow = StateGraph(AgentState)
    workflow.add_node("start_node", start)

    # 从配置中获取分析师节点
    analyst_nodes = get_analyst_nodes()

    # 如果未选择分析师，默认使用全部
    if selected_analysts is None:
        selected_analysts = list(analyst_nodes.keys())
    # 添加选定的分析师节点
    for analyst_key in selected_analysts:
        node_name, node_func = analyst_nodes[analyst_key]
        workflow.add_node(node_name, node_func)
        workflow.add_edge("start_node", node_name)

    # 始终添加风险和投资组合管理
    workflow.add_node("risk_management_agent", risk_management_agent)
    workflow.add_node("portfolio_management_agent", portfolio_management_agent)

    # 将选定的分析师连接到风险管理
    for analyst_key in selected_analysts:
        node_name = analyst_nodes[analyst_key][0]
        workflow.add_edge(node_name, "risk_management_agent")

    workflow.add_edge("risk_management_agent", "portfolio_management_agent")
    workflow.add_edge("portfolio_management_agent", END)

    workflow.set_entry_point("start_node")
    return workflow


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description=_("cli.description"))
    parser.add_argument(
        "--initial-cash",
        type=float,
        default=100000.0,
        help=_("cli.initial_cash.help")
    )
    parser.add_argument(
        "--margin-requirement",
        type=float,
        default=0.0,
        help=_("cli.margin_requirement.help")
    )
    parser.add_argument(
        "--tickers", 
        type=str, 
        required=True, 
        help=_("cli.tickers.help")
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help=_("cli.start_date.help"),
    )
    parser.add_argument(
        "--end-date", 
        type=str, 
        help=_("cli.end_date.help")
    )
    parser.add_argument(
        "--show-reasoning", 
        action="store_true", 
        help=_("cli.show_reasoning.help")
    )
    parser.add_argument(
        "--show-agent-graph", 
        action="store_true", 
        help=_("cli.show_agent_graph.help")
    )
    parser.add_argument(
        "--ollama", 
        action="store_true", 
        help=_("cli.ollama.help")
    )
    parser.add_argument(
        "--language", 
        type=str, 
        choices=["en", "zh"], 
        default="en",
        help=_("cli.language.help")
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["trading", "backtest"],
        default="trading",
        help=_("cli.mode.help")
    )

    args = parser.parse_args()
    
    # 设置语言
    set_language(args.language)

    # 从逗号分隔的字符串解析股票代码
    tickers = [ticker.strip() for ticker in args.tickers.split(",")]

    # 选择分析师
    selected_analysts = None
    choices = questionary.checkbox(
        _("agent.select_prompt"),
        choices=[questionary.Choice(_(f"analyst.{value}"), value=value) for display, value in ANALYST_ORDER],
        instruction=_("agent.select_instructions"),
        validate=lambda x: len(x) > 0 or _("agent.select_validation"),
        style=questionary.Style(
            [
                ("checkbox-selected", "fg:green"),
                ("selected", "fg:green noinherit"),
                ("highlighted", "noinherit"),
                ("pointer", "noinherit"),
            ]
        ),
    ).ask()

    if not choices:
        logger.info(_("error.interrupt"))
        sys.exit(0)
    else:
        selected_analysts = choices
        analyst_names = [_(f"analyst.{choice}") for choice in choices]
        formatted_analysts = ', '.join(Fore.GREEN + name + Style.RESET_ALL for name in analyst_names)
        logger.info(_("agent.selected", analysts=formatted_analysts))

    # 根据是否使用Ollama选择LLM模型
    model_choice = None
    model_provider = None
    
    if args.ollama:
        logger.info(_("model.ollama.using"))
        
        # 从Ollama特定模型中选择
        model_choice = questionary.select(
            _("model.ollama.select_prompt"),
            choices=[questionary.Choice(display, value=value) for display, value, _ in OLLAMA_LLM_ORDER],
            style=questionary.Style([
                ("selected", "fg:green bold"),
                ("pointer", "fg:green bold"),
                ("highlighted", "fg:green"),
                ("answer", "fg:green bold"),
            ])
        ).ask()
        
        if not model_choice:
            logger.info(_("error.interrupt"))
            sys.exit(0)
        
        # 确保Ollama已安装、正在运行，并且所选模型可用
        if not ensure_ollama_and_model(model_choice):
            logger.error(_("model.ollama.error"))
            sys.exit(1)
        
        model_provider = ModelProvider.OLLAMA.value
        logger.info(_("model.ollama.selected", model=Fore.GREEN + Style.BRIGHT + model_choice + Style.RESET_ALL))
    else:
        # 使用标准的基于云的LLM选择
        model_choice = questionary.select(
            _("model.select_prompt"),
            choices=[questionary.Choice(display, value=value) for display, value, _ in LLM_ORDER],
            style=questionary.Style([
                ("selected", "fg:green bold"),
                ("pointer", "fg:green bold"),
                ("highlighted", "fg:green"),
                ("answer", "fg:green bold"),
            ])
        ).ask()

        if not model_choice:
            logger.info(_("error.interrupt"))
            sys.exit(0)
        else:
            # 使用辅助函数获取模型信息
            model_info = get_model_info(model_choice)
            if model_info:
                model_provider = model_info.provider.value
                logger.info(_("model.selected", 
                              provider=Fore.CYAN + model_provider + Style.RESET_ALL, 
                              model=Fore.GREEN + Style.BRIGHT + model_choice + Style.RESET_ALL))
            else:
                model_provider = "Unknown"
                logger.info(_("model.unknown_selected", 
                              model=Fore.GREEN + Style.BRIGHT + model_choice + Style.RESET_ALL))

    # 使用选定的分析师创建工作流
    workflow = create_workflow(selected_analysts)
    app = workflow.compile()

    if args.show_agent_graph:
        file_path = ""
        if selected_analysts is not None:
            for selected_analyst in selected_analysts:
                file_path += selected_analyst + "_"
            file_path += "graph.png"
        save_graph_as_png(app, file_path)

    # 验证日期格式（如果提供）
    if args.start_date:
        try:
            datetime.strptime(args.start_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(_("error.invalid_date", date_type="Start"))

    if args.end_date:
        try:
            datetime.strptime(args.end_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(_("error.invalid_date", date_type="End"))

    # 设置开始和结束日期
    end_date = args.end_date or datetime.now().strftime("%Y-%m-%d")
    if not args.start_date:
        # 计算结束日期前3个月
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = (end_date_obj - relativedelta(months=3)).strftime("%Y-%m-%d")
    else:
        start_date = args.start_date

    # 使用现金金额和股票仓位初始化投资组合
    portfolio = {
        "cash": args.initial_cash,  # 初始现金金额
        "margin_requirement": args.margin_requirement,  # 初始保证金要求
        "margin_used": 0.0,  # 所有空头仓位使用的总保证金
        "positions": {
            ticker: {
                "long": 0,  # 持有的多头股票数量
                "short": 0,  # 持有的空头股票数量
                "long_cost_basis": 0.0,  # 多头仓位的平均成本基础
                "short_cost_basis": 0.0,  # 股票做空的平均价格
                "short_margin_used": 0.0,  # 该股票空头使用的保证金
            } for ticker in tickers
        },
        "realized_gains": {
            ticker: {
                "long": 0.0,  # 多头仓位实现的收益
                "short": 0.0,  # 空头仓位实现的收益
            } for ticker in tickers
        }
    }

    # 根据模式选择运行交易或回测
    if args.mode == "trading":
        # 运行对冲基金
        result = run_hedge_fund(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            portfolio=portfolio,
            show_reasoning=args.show_reasoning,
            selected_analysts=selected_analysts,
            model_name=model_choice,
            model_provider=model_provider,
        )
        print_trading_output(result)
    else:  # backtest 模式
        # 导入backtester以避免影响初始启动时间
        from src.backtester import Backtester
        
        # 创建回测实例
        backtester = Backtester(
            agent=agent_adapter,
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            initial_capital=args.initial_cash,
            model_name=model_choice,
            model_provider=model_provider,
            selected_analysts=selected_analysts,
            initial_margin_requirement=args.margin_requirement,
        )
        
        # 运行回测
        backtester.run_backtest()

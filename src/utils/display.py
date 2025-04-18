import json
import os

from colorama import Fore, Style
from tabulate import tabulate

from .analysts import ANALYST_ORDER
from .i18n import _


def sort_agent_signals(signals):
    """对代理信号进行一致的排序。"""
    # 从ANALYST_ORDER创建排序映射
    analyst_order = {display: idx for idx, (display, _) in enumerate(ANALYST_ORDER)}
    analyst_order["Risk Management"] = len(ANALYST_ORDER)  # 将风险管理添加到末尾

    return sorted(signals, key=lambda x: analyst_order.get(x[0], 999))


def format_backtest_row(
    date: str,
    ticker: str,
    action: str,
    quantity: int,
    price: float,
    shares_owned: int,
    position_value: float,
    bullish_count: int = 0,
    bearish_count: int = 0,
    neutral_count: int = 0,
    is_summary: bool = False,
    total_value: float = None,
    return_pct: float = None,
    cash_balance: float = None,
    total_position_value: float = None,
    sharpe_ratio: float = None,
    sortino_ratio: float = None,
    max_drawdown: float = None,
):
    """
    格式化回测表格行
    
    Args:
        date: 日期
        ticker: 股票代码
        action: 执行的操作(BUY/SELL/HOLD等)
        quantity: 交易数量
        price: 价格
        shares_owned: 拥有的股票数量
        position_value: 仓位价值
        bullish_count: 看涨信号数量
        bearish_count: 看跌信号数量
        neutral_count: 中性信号数量
        is_summary: 是否为摘要行
        total_value: 总价值(仅摘要行)
        return_pct: 回报率(仅摘要行)
        cash_balance: 现金余额(仅摘要行)
        total_position_value: 总仓位价值(仅摘要行)
        sharpe_ratio: 夏普比率(仅摘要行)
        sortino_ratio: 索提诺比率(仅摘要行)
        max_drawdown: 最大回撤(仅摘要行)
        
    Returns:
        list: 格式化的行数据
    """
    if is_summary:
        # 摘要行
        return [
            date,
            "PORTFOLIO SUMMARY",
            f"${total_value:,.2f}",
            f"${cash_balance:,.2f}",
            f"${total_position_value:,.2f}",
            f"{return_pct:.2f}%",
            f"{sharpe_ratio:.3f}" if sharpe_ratio else "N/A",
            f"{sortino_ratio:.3f}" if sortino_ratio else "N/A",
            f"{max_drawdown:.2f}%" if max_drawdown else "N/A",
        ]
    
    # 股票数据行
    return [
        ticker,
        str(shares_owned),
        f"${price:.2f}",
        f"${position_value:.2f}",
        f"${position_value - (price * shares_owned):.2f}",
        f"{(position_value / (price * shares_owned) - 1) * 100:.2f}%" if shares_owned != 0 else "0.00%",
        action.upper(),
        str(quantity),
        f"({bullish_count}|{neutral_count}|{bearish_count})",
    ]


def print_trading_output(result: dict) -> None:
    """
    为多个股票打印格式化的交易结果，带有彩色表格。

    Args:
        result (dict): 包含多个股票的决策和分析师信号的字典
    """
    decisions = result.get("decisions")
    if not decisions:
        print(f"{Fore.RED}{_('display.no_decisions')}{Style.RESET_ALL}")
        return

    # 为每个股票打印决策
    for ticker, decision in decisions.items():
        print(f"\n{Fore.WHITE}{Style.BRIGHT}{_('display.analysis_for', ticker=Fore.CYAN + ticker + Style.RESET_ALL)}")
        print(f"{Fore.WHITE}{Style.BRIGHT}{'=' * 50}{Style.RESET_ALL}")

        # 为此股票准备分析师信号表
        table_data = []
        for agent, signals in result.get("analyst_signals", {}).items():
            if ticker not in signals:
                continue
                
            # 在信号部分跳过风险管理代理
            if agent == "risk_management_agent":
                continue

            signal = signals[ticker]
            agent_name = _(f"analyst.{agent.replace('_agent', '')}")
            signal_type = signal.get("signal", "").upper()
            confidence = signal.get("confidence", 0)

            signal_color = {
                "BULLISH": Fore.GREEN,
                "BEARISH": Fore.RED,
                "NEUTRAL": Fore.YELLOW,
            }.get(signal_type, Fore.WHITE)
            
            # 获取推理（如果可用）
            reasoning_str = ""
            if "reasoning" in signal and signal["reasoning"]:
                reasoning = signal["reasoning"]
                
                # 处理不同类型的推理（字符串、字典等）
                if isinstance(reasoning, str):
                    reasoning_str = reasoning
                elif isinstance(reasoning, dict):
                    # 将字典转换为字符串表示
                    reasoning_str = json.dumps(reasoning, indent=2)
                else:
                    # 将任何其他类型转换为字符串
                    reasoning_str = str(reasoning)
                
                # 包装长推理文本，使其更具可读性
                wrapped_reasoning = ""
                current_line = ""
                # 使用60个字符的固定宽度以匹配表格列宽
                max_line_length = 60
                for word in reasoning_str.split():
                    if len(current_line) + len(word) + 1 > max_line_length:
                        wrapped_reasoning += current_line + "\n"
                        current_line = word
                    else:
                        if current_line:
                            current_line += " " + word
                        else:
                            current_line = word
                if current_line:
                    wrapped_reasoning += current_line
                
                reasoning_str = wrapped_reasoning

            table_data.append(
                [
                    f"{Fore.CYAN}{agent_name}{Style.RESET_ALL}",
                    f"{signal_color}{signal_type}{Style.RESET_ALL}",
                    f"{Fore.WHITE}{confidence}%{Style.RESET_ALL}",
                    f"{Fore.WHITE}{reasoning_str}{Style.RESET_ALL}",
                ]
            )

        # 根据预定义的顺序对信号进行排序
        table_data = sort_agent_signals(table_data)

        print(f"\n{Fore.WHITE}{Style.BRIGHT}{_('display.agent_analysis', ticker=Fore.CYAN + ticker + Style.RESET_ALL)}")
        print(
            tabulate(
                table_data,
                headers=[
                    f"{Fore.WHITE}{_('display.header.agent')}", 
                    _('display.header.signal'), 
                    _('display.header.confidence'), 
                    _('display.header.reasoning')
                ],
                tablefmt="grid",
                colalign=("left", "center", "right", "left"),
            )
        )

        # 打印交易决策表
        action = decision.get("action", "").upper()
        action_color = {
            "BUY": Fore.GREEN,
            "SELL": Fore.RED,
            "HOLD": Fore.YELLOW,
            "COVER": Fore.GREEN,
            "SHORT": Fore.RED,
        }.get(action, Fore.WHITE)

        # 获取并格式化推理
        reasoning = decision.get("reasoning", "")
        # 包装长推理文本，使其更具可读性
        wrapped_reasoning = ""
        if reasoning:
            current_line = ""
            # 使用60个字符的固定宽度以匹配表格列宽
            max_line_length = 60
            for word in reasoning.split():
                if len(current_line) + len(word) + 1 > max_line_length:
                    wrapped_reasoning += current_line + "\n"
                    current_line = word
                else:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
            if current_line:
                wrapped_reasoning += current_line

        decision_data = [
            [_('display.header.action'), f"{action_color}{action}{Style.RESET_ALL}"],
            [_('display.header.quantity'), f"{action_color}{decision.get('quantity')}{Style.RESET_ALL}"],
            [
                _('display.header.confidence'),
                f"{Fore.WHITE}{decision.get('confidence'):.1f}%{Style.RESET_ALL}",
            ],
            [_('display.header.reasoning'), f"{Fore.WHITE}{wrapped_reasoning}{Style.RESET_ALL}"],
        ]
        
        print(f"\n{Fore.WHITE}{Style.BRIGHT}{_('display.trading_decision', ticker=Fore.CYAN + ticker + Style.RESET_ALL)}")
        print(tabulate(decision_data, tablefmt="grid", colalign=("left", "left")))

    # 打印投资组合摘要
    print(f"\n{Fore.WHITE}{Style.BRIGHT}{_('display.portfolio_summary')}{Style.RESET_ALL}")
    portfolio_data = []
    
    # 提取投资组合管理者的推理（所有股票通用）
    portfolio_manager_reasoning = None
    for ticker, decision in decisions.items():
        if decision.get("reasoning"):
            portfolio_manager_reasoning = decision.get("reasoning")
            break
            
    for ticker, decision in decisions.items():
        action = decision.get("action", "").upper()
        action_color = {
            "BUY": Fore.GREEN,
            "SELL": Fore.RED,
            "HOLD": Fore.YELLOW,
            "COVER": Fore.GREEN,
            "SHORT": Fore.RED,
        }.get(action, Fore.WHITE)
        portfolio_data.append(
            [
                f"{Fore.CYAN}{ticker}{Style.RESET_ALL}",
                f"{action_color}{action}{Style.RESET_ALL}",
                f"{action_color}{decision.get('quantity')}{Style.RESET_ALL}",
                f"{Fore.WHITE}{decision.get('confidence'):.1f}%{Style.RESET_ALL}",
            ]
        )

    headers = [
        f"{Fore.WHITE}{_('display.header.ticker')}", 
        _('display.header.action'), 
        _('display.header.quantity'), 
        _('display.header.confidence')
    ]
    
    # 打印投资组合摘要表
    print(
        tabulate(
            portfolio_data,
            headers=headers,
            tablefmt="grid",
            colalign=("left", "center", "right", "right"),
        )
    )
    
    # 如果可用，打印投资组合管理者的推理
    if portfolio_manager_reasoning:
        # 处理不同类型的推理（字符串、字典等）
        reasoning_str = ""
        if isinstance(portfolio_manager_reasoning, str):
            reasoning_str = portfolio_manager_reasoning
        elif isinstance(portfolio_manager_reasoning, dict):
            # 将字典转换为字符串表示
            reasoning_str = json.dumps(portfolio_manager_reasoning, indent=2)
        else:
            # 将任何其他类型转换为字符串
            reasoning_str = str(portfolio_manager_reasoning)
            
        # 包装长推理文本，使其更具可读性
        wrapped_reasoning = ""
        current_line = ""
        # 使用60个字符的固定宽度以匹配表格列宽
        max_line_length = 60
        for word in reasoning_str.split():
            if len(current_line) + len(word) + 1 > max_line_length:
                wrapped_reasoning += current_line + "\n"
                current_line = word
            else:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
        if current_line:
            wrapped_reasoning += current_line
            
        print(f"\n{Fore.WHITE}{Style.BRIGHT}{_('display.portfolio_strategy')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{wrapped_reasoning}{Style.RESET_ALL}")


def print_backtest_results(table_rows: list) -> None:
    """以格式良好的表格打印回测结果"""
    # 清屏
    os.system("cls" if os.name == "nt" else "clear")

    # 将行分为股票行和摘要行
    ticker_rows = []
    summary_rows = []

    for row in table_rows:
        if isinstance(row[1], str) and "PORTFOLIO SUMMARY" in row[1]:
            summary_rows.append(row)
        else:
            ticker_rows.append(row)

    
    # 显示最新的投资组合摘要
    if summary_rows:
        latest_summary = summary_rows[-1]
        print(f"\n{Fore.WHITE}{Style.BRIGHT}{_('display.portfolio_summary')}{Style.RESET_ALL}")
        
        # 提取值并在转换为浮点数之前删除逗号
        portfolio_value = float(latest_summary[2].replace("$", "").replace(",", ""))
        cash_value = float(latest_summary[3].replace("$", "").replace(",", ""))
        total_return = float(latest_summary[5].replace("%", ""))
        
        # 根据结果设置颜色
        return_color = Fore.GREEN if total_return > 0 else Fore.RED
        
        # 创建表格数据
        summary_data = [
            [_('display.backtest.portfolio_value'), f"${portfolio_value:,.2f}"],
            [_('display.backtest.cash_value'), f"${cash_value:,.2f}"],
            [_('display.backtest.total_return'), f"{return_color}{total_return:.2f}%{Style.RESET_ALL}"],
        ]
        
        # 打印表格
        print(tabulate(summary_data, tablefmt="grid", colalign=("left", "right")))

    # 显示最新的股票保持情况
    print(f"\n{Fore.WHITE}{Style.BRIGHT}{_('display.backtest.holdings')}{Style.RESET_ALL}")
    
    # 如果有股票行，则打印它们
    if ticker_rows:
        holdings_data = []
        for row in ticker_rows:
            ticker = row[0]
            shares = float(row[1])
            cost_basis = float(row[2].replace("$", ""))
            market_value = float(row[3].replace("$", ""))
            profit_loss = float(row[4].replace("$", ""))
            profit_loss_percent = float(row[5].replace("%", ""))
            
            # 确定颜色
            pl_color = Fore.GREEN if profit_loss > 0 else Fore.RED
            
            holdings_data.append([
                f"{Fore.CYAN}{ticker}{Style.RESET_ALL}",
                f"{shares:.0f}",
                f"${cost_basis:.2f}",
                f"${market_value:.2f}",
                f"{pl_color}${profit_loss:.2f}{Style.RESET_ALL}",
                f"{pl_color}{profit_loss_percent:.2f}%{Style.RESET_ALL}",
            ])
            
        # 打印表格
        print(tabulate(
            holdings_data,
            headers=[
                f"{Fore.WHITE}{_('display.backtest.ticker')}", 
                _('display.backtest.shares'), 
                _('display.backtest.cost_basis'), 
                _('display.backtest.market_value'), 
                _('display.backtest.profit_loss'), 
                _('display.backtest.return')
            ],
            tablefmt="grid",
            colalign=("left", "right", "right", "right", "right", "right"),
        ))
    else:
        print(f"{Fore.YELLOW}{_('display.backtest.no_holdings')}{Style.RESET_ALL}")

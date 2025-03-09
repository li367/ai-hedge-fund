from typing import Dict, Optional
from datetime import datetime, timedelta
import numpy as np
from pydantic import BaseModel

class RiskMetrics(BaseModel):
    """风险指标"""
    max_drawdown: float = 0
    current_drawdown: float = 0
    volatility: float = 0
    sharpe_ratio: Optional[float] = None
    win_rate: float = 0
    profit_factor: float = 0
    max_leverage: float = 1.0
    peak_value: float = 0

class RiskManager:
    def __init__(
        self,
        exchange=None,
        max_position_size: float = 0.1,  # 最大仓位比例（相对于总资产）
        max_drawdown: float = 0.2,       # 最大回撤限制
        stop_loss_pct: float = 0.05,     # 止损比例
        take_profit_pct: float = 0.1,    # 止盈比例
        max_leverage: float = 3.0,       # 最大杠杆
        risk_per_trade: float = 0.02,    # 每笔交易风险比例
        volatility_window: int = 20,     # 波动率计算窗口
        min_win_rate: float = 0.4,       # 最小胜率要求
        min_profit_factor: float = 1.5   # 最小盈亏比
    ):
        self.exchange = exchange
        self.max_position_size = max_position_size
        self.max_drawdown = max_drawdown
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_leverage = max_leverage
        self.risk_per_trade = risk_per_trade
        self.volatility_window = volatility_window
        self.min_win_rate = min_win_rate
        self.min_profit_factor = min_profit_factor
        self.metrics = {}  # 按symbol存储风险指标

    async def initialize_metrics(self, symbol: str):
        """初始化风险指标"""
        if symbol not in self.metrics:
            self.metrics[symbol] = RiskMetrics()

    async def update_metrics(self, symbol: str):
        """更新风险指标"""
        await self.initialize_metrics(symbol)
        
        try:
            # 获取历史数据
            klines = await self.exchange.get_kline_data(
                symbol,
                timeframe='1h',
                limit=100
            )
            
            if not klines:
                return
            
            # 计算收益率
            prices = np.array([float(k[4]) for k in klines])  # 收盘价
            returns = np.diff(np.log(prices))
            
            # 计算波动率
            volatility = np.std(returns) * np.sqrt(24 * 365)  # 年化波动率
            
            # 计算夏普比率
            avg_return = np.mean(returns)
            risk_free_rate = 0.02  # 假设无风险利率2%
            sharpe = (avg_return - risk_free_rate) / volatility if volatility != 0 else None
            
            # 获取交易历史
            position = await self.exchange.get_position(symbol)
            
            if position:
                # 更新最大回撤
                unrealized_pnl = float(position['unrealizedPnl'])
                total_value = float(position['initialMargin']) + unrealized_pnl
                peak_value = self.metrics[symbol].peak_value
                
                if total_value > peak_value:
                    self.metrics[symbol].peak_value = total_value
                
                current_drawdown = (peak_value - total_value) / peak_value if peak_value > 0 else 0
                self.metrics[symbol].current_drawdown = current_drawdown
                self.metrics[symbol].max_drawdown = max(
                    self.metrics[symbol].max_drawdown,
                    current_drawdown
                )
            
            # 更新其他指标
            self.metrics[symbol].volatility = volatility
            self.metrics[symbol].sharpe_ratio = sharpe
            
        except Exception as e:
            print(f"更新风险指标失败: {str(e)}")

    def calculate_position_size(self, symbol: str, current_price: float, side: str) -> float:
        """计算仓位大小"""
        try:
            if not self.exchange:
                return 0
                
            # 获取账户余额
            balance = self.exchange.get_balance()
            total_equity = float(balance['total']['USDT'])
            
            # 基于风险的仓位计算
            risk_amount = total_equity * self.risk_per_trade
            
            # 计算止损点数
            stop_loss_points = current_price * self.stop_loss_pct
            
            # 计算仓位大小
            position_size = risk_amount / stop_loss_points if stop_loss_points > 0 else 0
            
            # 检查是否超过最大仓位限制
            max_position_value = total_equity * self.max_position_size
            position_size = min(position_size, max_position_value / current_price)
            
            return position_size
            
        except Exception as e:
            print(f"计算仓位大小失败: {str(e)}")
            return 0

    async def check_trade(self, symbol: str, current_price: float, 
                         current_position_size: float, current_drawdown: float) -> Dict:
        """检查是否可以交易"""
        await self.initialize_metrics(symbol)
        
        # 检查回撤限制
        if current_drawdown >= self.max_drawdown:
            return {
                'can_trade': False,
                'reason': '超过最大回撤限制'
            }
        
        # 检查波动率
        if self.metrics[symbol].volatility > 1.0:  # 年化波动率超过100%
            return {
                'can_trade': False,
                'reason': '市场波动率过高'
            }
        
        # 检查胜率
        if self.metrics[symbol].win_rate < self.min_win_rate:
            return {
                'can_trade': False,
                'reason': '胜率低于最小要求'
            }
        
        # 检查盈亏比
        if self.metrics[symbol].profit_factor < self.min_profit_factor:
            return {
                'can_trade': False,
                'reason': '盈亏比低于最小要求'
            }
        
        # 检查杠杆限制
        if current_position_size * current_price > self.max_leverage:
            return {
                'can_trade': False,
                'reason': '超过最大杠杆限制'
            }
        
        return {
            'can_trade': True,
            'reason': None
        }

    def get_stop_loss_price(self, entry_price: float, side: str) -> float:
        """计算止损价格"""
        if side.upper() == 'BUY':
            return entry_price * (1 - self.stop_loss_pct)
        else:
            return entry_price * (1 + self.stop_loss_pct)

    def get_take_profit_price(self, entry_price: float, side: str) -> float:
        """计算止盈价格"""
        if side.upper() == 'BUY':
            return entry_price * (1 + self.take_profit_pct)
        else:
            return entry_price * (1 - self.take_profit_pct)

    async def check_funding_rate(self, symbol: str) -> Dict:
        """检查资金费率"""
        try:
            if not self.exchange:
                return {
                    'should_adjust': False,
                    'funding_rate': 0
                }
                
            funding_rate = await self.exchange.get_funding_rate(symbol)
            
            # 如果资金费率过高，可能需要调整策略
            if abs(funding_rate['funding_rate']) > 0.001:  # 0.1%
                return {
                    'should_adjust': True,
                    'reason': '资金费率过高',
                    'funding_rate': funding_rate['funding_rate']
                }
            
            return {
                'should_adjust': False,
                'funding_rate': funding_rate['funding_rate']
            }
            
        except Exception as e:
            print(f"检查资金费率失败: {str(e)}")
            return {
                'should_adjust': False,
                'funding_rate': 0
            }
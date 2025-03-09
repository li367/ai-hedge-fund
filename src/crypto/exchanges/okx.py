import ccxt.async_support as ccxt
from typing import Dict, List, Optional, Any
from .base import BaseExchange
import asyncio

class OKXExchange(BaseExchange):
    """OKX交易所接口实现"""

    def __init__(self, api_key: str, secret_key: str, passphrase: str):
        super().__init__(api_key, secret_key, passphrase)
        self.exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': secret_key,
            'password': passphrase,
            'enableRateLimit': True
        })
        self.market_type = 'spot'  # 默认为现货市场

    async def get_balance(self) -> Dict[str, Any]:
        """获取账户余额"""
        try:
            balance = await self.exchange.fetch_balance()
            return balance
        except Exception as e:
            print(f"获取账户余额失败: {str(e)}")
            return {'total': {'USDT': 0}}

    async def get_position(self, symbol: str) -> Dict[str, Any]:
        """获取持仓信息"""
        try:
            positions = await self.exchange.fetch_positions([symbol])
            return positions[0] if positions else None
        except Exception as e:
            print(f"获取持仓信息失败: {str(e)}")
            return None

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取最新行情"""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            print(f"获取行情失败: {str(e)}")
            return {'last': 0}

    async def get_kline_data(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List]:
        """获取K线数据"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return ohlcv
        except Exception as e:
            print(f"获取K线数据失败: {str(e)}")
            return []

    async def place_order(self, symbol: str, side: str, order_type: str,
                         amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """下单"""
        try:
            order = await self.exchange.create_order(
                symbol,
                order_type,
                side,
                amount,
                price
            )
            return order
        except Exception as e:
            print(f"下单失败: {str(e)}")
            return None

    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """取消订单"""
        try:
            return await self.exchange.cancel_order(order_id, symbol)
        except Exception as e:
            print(f"取消订单失败: {str(e)}")
            return None

    async def get_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """获取订单信息"""
        try:
            return await self.exchange.fetch_order(order_id, symbol)
        except Exception as e:
            print(f"获取订单信息失败: {str(e)}")
            return None

    async def get_open_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """获取未成交订单"""
        try:
            return await self.exchange.fetch_open_orders(symbol)
        except Exception as e:
            print(f"获取未成交订单失败: {str(e)}")
            return []

    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """获取资金费率"""
        try:
            funding_rate = await self.exchange.fetch_funding_rate(symbol)
            return {
                'funding_rate': funding_rate['fundingRate'],
                'next_funding_time': funding_rate['nextFundingTime']
            }
        except Exception as e:
            print(f"获取资金费率失败: {str(e)}")
            return {'funding_rate': 0, 'next_funding_time': None}

    async def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """设置杠杆"""
        try:
            return await self.exchange.set_leverage(leverage, symbol)
        except Exception as e:
            print(f"设置杠杆失败: {str(e)}")
            return None

    async def switch_market_type(self, market_type: str) -> None:
        """切换市场类型"""
        if market_type not in ['spot', 'swap', 'futures']:
            raise ValueError("市场类型必须是 'spot', 'swap' 或 'futures'")
        
        self.market_type = market_type
        self.exchange.options['defaultType'] = market_type

    async def get_markets(self) -> List[Dict[str, Any]]:
        """获取市场信息"""
        try:
            markets = await self.exchange.load_markets()
            return [{
                'symbol': market['symbol'],
                'base': market['base'],
                'quote': market['quote'],
                'type': market['type'],
                'active': market['active']
            } for market in markets.values()]
        except Exception as e:
            print(f"获取市场信息失败: {str(e)}")
            return []

    async def close(self) -> None:
        """关闭连接"""
        try:
            await self.exchange.close()
        except Exception as e:
            print(f"关闭连接失败: {str(e)}")

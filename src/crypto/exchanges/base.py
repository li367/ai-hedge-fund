from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

class BaseExchange(ABC):
    """交易所基础接口"""

    def __init__(self, api_key: str, secret_key: str, passphrase: Optional[str] = None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    @abstractmethod
    async def get_balance(self) -> Dict[str, Any]:
        """获取账户余额"""
        pass

    @abstractmethod
    async def get_position(self, symbol: str) -> Dict[str, Any]:
        """获取持仓信息"""
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取最新行情"""
        pass

    @abstractmethod
    async def get_kline_data(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> List[List]:
        """获取K线数据"""
        pass

    @abstractmethod
    async def place_order(self, symbol: str, side: str, order_type: str,
                         amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """下单"""
        pass

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """取消订单"""
        pass

    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """获取订单信息"""
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """获取未成交订单"""
        pass

    @abstractmethod
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """获取资金费率"""
        pass

    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """设置杠杆"""
        pass

    @abstractmethod
    async def switch_market_type(self, market_type: str) -> None:
        """切换市场类型（现货/合约）"""
        pass

    @abstractmethod
    async def get_markets(self) -> List[Dict[str, Any]]:
        """获取市场信息"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        pass
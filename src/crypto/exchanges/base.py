from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pydantic import BaseModel
import ccxt.async_support as ccxt
import asyncio
from datetime import datetime

class OrderRequest(BaseModel):
    symbol: str
    order_type: str  # MARKET, LIMIT
    side: str       # BUY, SELL
    amount: float
    price: Optional[float] = None
    leverage: Optional[float] = 1.0

class OrderResponse(BaseModel):
    exchange_order_id: str
    symbol: str
    order_type: str
    side: str
    amount: float
    price: float
    status: str
    timestamp: datetime

class BaseExchange(ABC):
    def __init__(self, api_key: str, secret_key: str, passphrase: str = None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.exchange = None
        self._initialize_exchange()

    @abstractmethod
    def _initialize_exchange(self):
        """初始化特定交易所实例"""
        pass

    async def get_ticker(self, symbol: str) -> Dict:
        """获取交易对的最新价格信息"""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'last': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume': ticker['baseVolume'],
                'timestamp': ticker['timestamp']
            }
        except Exception as e:
            raise Exception(f"获取Ticker失败: {str(e)}")

    async def get_available_symbols(self, quote_currency: str = None, market_type: str = None) -> List[str]:
        """获取可用的交易对列表
        
        Args:
            quote_currency: 可选的计价货币过滤（如USDT）
            market_type: 可选的市场类型过滤(spot, swap, futures)
            
        Returns:
            交易对列表
        """
        try:
            # 加载市场
            markets = await self.exchange.load_markets()
            symbols = []
            
            # 根据市场类型过滤
            if market_type:
                filtered_markets = {}
                for symbol, market in markets.items():
                    if market_type == 'spot' and market.get('spot', False):
                        filtered_markets[symbol] = market
                    elif market_type == 'swap' and market.get('swap', False):
                        filtered_markets[symbol] = market
                    elif market_type == 'futures' and market.get('futures', False):
                        filtered_markets[symbol] = market
                markets = filtered_markets
            
            # 如果指定了计价货币，则按计价货币过滤
            for symbol, market in markets.items():
                if quote_currency:
                    # 使用CCXT提供的信息直接获取base和quote
                    base = market.get('base', '')  # 基础货币
                    quote = market.get('quote', '')  # 计价货币
                    
                    # 如果市场数据中没有base或quote信息，尝试从symbol中解析
                    if not base or not quote:
                        try:
                            # 对于大多数交易所，交易对格式为 BASE/QUOTE
                            if '/' in symbol:
                                base, quote = symbol.split('/')
                            # 有些交易所使用其他分隔符或格式
                            elif '-' in symbol:
                                parts = symbol.split('-')
                                if len(parts) >= 2:
                                    base, quote = parts[0], parts[-1]
                                    # 处理像 BTC-USDT-SWAP 这样的格式
                                    if quote in ['SWAP', 'PERP', 'futures']:
                                        quote = parts[-2]
                        except Exception:
                            # 如果解析失败，直接跳过此交易对
                            continue
                    
                    # 使用大写进行比较，避免大小写问题
                    if quote.upper() == quote_currency.upper():
                        symbols.append(symbol)
                else:
                    symbols.append(symbol)
            
            return sorted(symbols)
        except Exception as e:
            raise Exception(f"获取交易对列表失败: {str(e)}")

    async def get_popular_symbols(self, top_n: int = 10, quote_currency: str = 'USDT', market_type: str = 'swap') -> List[str]:
        """获取交易量最大的热门交易对
        
        Args:
            top_n: 返回的交易对数量
            quote_currency: 计价货币
            market_type: 市场类型
            
        Returns:
            热门交易对列表
        """
        try:
            # 获取当前市场类型下，符合计价货币的所有交易对
            all_symbols = await self.get_available_symbols(quote_currency, market_type)
            
            # 获取交易量信息
            tickers = []
            for symbol in all_symbols[:min(50, len(all_symbols))]:  # 限制API调用数量
                try:
                    ticker = await self.exchange.fetch_ticker(symbol)
                    tickers.append({
                        'symbol': symbol,
                        'volume': ticker.get('quoteVolume', 0) or ticker.get('baseVolume', 0) or 0
                    })
                except Exception:
                    continue
                
                # 避免API请求过于频繁
                await asyncio.sleep(0.2)
            
            # 按交易量排序
            sorted_tickers = sorted(tickers, key=lambda x: x['volume'], reverse=True)
            
            # 返回交易量最大的top_n个交易对
            return [ticker['symbol'] for ticker in sorted_tickers[:top_n]]
        except Exception as e:
            raise Exception(f"获取热门交易对失败: {str(e)}")

    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """下单接口"""
        try:
            order = await self.exchange.create_order(
                symbol=order_request.symbol,
                type=order_request.order_type.lower(),
                side=order_request.side.lower(),
                amount=order_request.amount,
                price=order_request.price
            )
            
            return OrderResponse(
                exchange_order_id=order['id'],
                symbol=order['symbol'],
                order_type=order['type'],
                side=order['side'],
                amount=order['amount'],
                price=order['price'],
                status=order['status'],
                timestamp=datetime.fromtimestamp(order['timestamp'] / 1000)
            )
        except Exception as e:
            raise Exception(f"下单失败: {str(e)}")

    async def get_balance(self) -> Dict:
        """获取账户余额"""
        try:
            balance = await self.exchange.fetch_balance()
            return balance
        except Exception as e:
            raise Exception(f"获取余额失败: {str(e)}")

    async def get_position(self, symbol: str) -> Dict:
        """获取持仓信息"""
        try:
            positions = await self.exchange.fetch_positions([symbol])
            return positions[0] if positions else None
        except Exception as e:
            raise Exception(f"获取持仓失败: {str(e)}")

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """取消订单"""
        try:
            await self.exchange.cancel_order(order_id, symbol)
            return True
        except Exception as e:
            raise Exception(f"取消订单失败: {str(e)}")

    async def close(self):
        """关闭连接"""
        if self.exchange:
            await self.exchange.close()
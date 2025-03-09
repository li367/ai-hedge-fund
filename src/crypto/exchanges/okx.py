from typing import Dict, Optional, List
import ccxt.async_support as ccxt
from .base import BaseExchange, OrderRequest, OrderResponse
from datetime import datetime
import logging

class OKXExchange(BaseExchange):
    def _initialize_exchange(self):
        """初始化OKX交易所实例"""
        self.exchange = ccxt.okx({
            'apiKey': self.api_key,
            'secret': self.secret_key,
            'password': self.passphrase,  # OKX特定参数
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # 默认现货交易
            }
        })

    async def set_leverage(self, symbol: str, leverage: float, position_side: str = 'both'):
        """设置杠杆倍数"""
        try:
            return await self.exchange.set_leverage(leverage, symbol, params={
                'posSide': position_side
            })
        except Exception as e:
            raise Exception(f"设置杠杆失败: {str(e)}")

    async def switch_market_type(self, market_type: str):
        """切换市场类型（现货/合约）"""
        if market_type not in ['spot', 'swap', 'futures', 'margin']:
            raise ValueError("不支持的市场类型")
        self.exchange.options['defaultType'] = market_type

    async def get_funding_rate(self, symbol: str) -> Dict:
        """获取资金费率"""
        try:
            funding_rate = await self.exchange.fetch_funding_rate(symbol)
            result = {
                'symbol': symbol,
                'funding_rate': funding_rate.get('fundingRate', 0),
                'timestamp': funding_rate.get('timestamp', int(datetime.now().timestamp() * 1000))
            }
            
            # 安全地添加next_funding_time字段
            if 'nextFundingTime' in funding_rate:
                result['next_funding_time'] = funding_rate['nextFundingTime']
            else:
                # 计算一个预估的下次资金费率时间（通常是8小时）
                current_time = int(datetime.now().timestamp() * 1000)  # 毫秒时间戳
                result['next_funding_time'] = current_time + 8 * 60 * 60 * 1000  # 8小时后
                
            return result
        except Exception as e:
            raise Exception(f"获取资金费率失败: {str(e)}")

    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """OKX特定的下单实现"""
        try:
            # 设置杠杆（如果需要）
            if order_request.leverage and order_request.leverage != 1.0:
                await self.set_leverage(order_request.symbol, order_request.leverage)

            # 构建下单参数
            params = {}
            if self.exchange.options['defaultType'] != 'spot':
                params['tdMode'] = 'cross'  # 全仓模式

            order = await self.exchange.create_order(
                symbol=order_request.symbol,
                type=order_request.order_type.lower(),
                side=order_request.side.lower(),
                amount=order_request.amount,
                price=order_request.price,
                params=params
            )
            
            return OrderResponse(
                exchange_order_id=order['id'],
                symbol=order['symbol'],
                order_type=order['type'],
                side=order['side'],
                amount=order['amount'],
                price=order['price'],
                status=order['status'],
                timestamp=order['datetime']
            )
        except Exception as e:
            raise Exception(f"OKX下单失败: {str(e)}")

    async def get_market_depth(self, symbol: str, limit: int = 20) -> Dict:
        """获取市场深度"""
        try:
            orderbook = await self.exchange.fetch_order_book(symbol, limit)
            return {
                'symbol': symbol,
                'bids': orderbook['bids'],
                'asks': orderbook['asks'],
                'timestamp': orderbook['timestamp']
            }
        except Exception as e:
            raise Exception(f"获取市场深度失败: {str(e)}")

    async def get_kline_data(self, symbol: str, timeframe: str = '1m', 
                            since: Optional[int] = None, limit: Optional[int] = None) -> list:
        """获取K线数据"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol, timeframe=timeframe, since=since, limit=limit
            )
            return ohlcv
        except Exception as e:
            raise Exception(f"获取K线数据失败: {str(e)}")

    async def get_active_pairs(self, top_n=5, market_type='swap') -> List[str]:
        """获取活跃的交易对列表
        
        Args:
            top_n: 返回交易对数量
            market_type: 市场类型('swap', 'spot', 'futures')
            
        Returns:
            活跃交易对列表
        """
        try:
            if market_type not in ['swap', 'spot', 'futures']:
                raise ValueError(f"不支持的市场类型: {market_type}")
            
            # 确保交易所设置了正确的市场类型
            self.exchange.options['defaultType'] = market_type
            
            # 获取交易对列表
            markets = await self.exchange.fetch_markets()
            
            # 过滤USDT计价的交易对
            usdt_markets = [
                market for market in markets 
                if market['quote'] == 'USDT' and market[market_type]
            ]
            
            # 为每个交易对获取24小时交易量
            market_volumes = []
            for market in usdt_markets[:min(20, len(usdt_markets))]:  # 限制API调用数量
                try:
                    ticker = await self.exchange.fetch_ticker(market['symbol'])
                    if ticker and 'quoteVolume' in ticker and ticker['quoteVolume']:
                        market_volumes.append({
                            'symbol': market['symbol'],
                            'volume': ticker['quoteVolume']
                        })
                except Exception:
                    continue
            
            # 按交易量排序
            sorted_markets = sorted(market_volumes, key=lambda x: x['volume'], reverse=True)
            
            # 获取前N个交易对
            active_pairs = [market['symbol'] for market in sorted_markets[:top_n]]
            
            return active_pairs
        except Exception as e:
            logging.error(f"获取活跃交易对失败: {e}")
            # 返回默认交易对
            return ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]
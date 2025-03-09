from typing import Dict, Optional, List
from datetime import datetime, timedelta
import json
import os
import logging
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

class MarketAnalysis(BaseModel):
    """市场分析结果"""
    sentiment: float  # 情绪值，范围[-1, 1]
    suggested_action: str  # 建议操作：BUY, SELL, HOLD
    confidence: float  # 置信度，范围[0, 1]
    analysis: str  # 分析理由

class LLMStrategy:
    def __init__(
        self,
        exchange,
        risk_manager,
        symbol: str,
        model_name: str = 'gpt-4',
        model_provider: str = 'openai',
        timeframe: str = '15m',
        sentiment_threshold: float = 0.6,
        use_cache: bool = True,
        cache_expire_minutes: int = 5
    ):
        self.exchange = exchange
        self.risk_manager = risk_manager
        self.symbol = symbol
        self.model_name = model_name
        self.model_provider = model_provider
        self.timeframe = timeframe
        self.sentiment_threshold = sentiment_threshold
        self.use_cache = use_cache
        self.cache_expire_minutes = cache_expire_minutes
        self.cache = {}
        
        # 初始化LLM模型
        self._init_llm()
        
        # 初始化提示模板
        self._init_prompt_template()

    def _init_llm(self):
        """初始化LLM模型"""
        try:
            if self.model_provider == 'openai':
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=self.model_name,
                    temperature=0.7
                )
            elif self.model_provider == 'anthropic':
                from langchain_anthropic import ChatAnthropic
                self.llm = ChatAnthropic(
                    model=self.model_name,
                    temperature=0.7
                )
            elif self.model_provider == 'tongyi':
                from langchain.chat_models import ChatAliCloud
                self.llm = ChatAliCloud(
                    model=self.model_name,
                    temperature=0.7
                )
            else:
                raise ValueError(f"不支持的LLM提供商: {self.model_provider}")
                
        except Exception as e:
            logging.error(f"初始化LLM模型失败: {str(e)}")
            raise

    def _init_prompt_template(self):
        """初始化提示模板"""
        system_template = """你是一个加密货币交易分析师。你的任务是分析市场数据并提供交易建议。

请根据以下数据进行分析：
- 交易对: {symbol}
- K线数据: {klines}
- 资金费率: {funding_rate}
- 当前持仓: {position}

输出格式应为JSON，包含以下字段：
- sentiment: 情绪值，范围[-1, 1]，其中-1表示非常看空，1表示非常看多
- suggested_action: 建议操作，只能是 BUY、SELL 或 HOLD
- confidence: 置信度，范围[0, 1]
- analysis: 分析理由，一段简短的文字说明"""

        human_template = """请分析以下市场数据并给出交易建议：

{market_data}"""

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_template),
            ("human", human_template),
        ])

    async def analyze_market(self, market_data: Dict) -> MarketAnalysis:
        """分析市场数据"""
        try:
            # 检查缓存
            cache_key = json.dumps(market_data)
            if self.use_cache and cache_key in self.cache:
                cached_result, timestamp = self.cache[cache_key]
                if datetime.now() - timestamp < timedelta(minutes=self.cache_expire_minutes):
                    return cached_result

            # 准备提示
            messages = self.prompt.format_messages(
                market_data=json.dumps(market_data, ensure_ascii=False, indent=2)
            )

            # 调用LLM
            response = await self.llm.ainvoke(messages)
            
            # 解析响应
            try:
                result = json.loads(response.content)
                analysis = MarketAnalysis(**result)
                
                # 更新缓存
                if self.use_cache:
                    self.cache[cache_key] = (analysis, datetime.now())
                    
                return analysis
                
            except Exception as e:
                logging.error(f"解析LLM响应失败: {str(e)}")
                # 返回一个保守的默认分析
                return MarketAnalysis(
                    sentiment=0,
                    suggested_action="HOLD",
                    confidence=0,
                    analysis="分析失败，建议观望"
                )
                
        except Exception as e:
            logging.error(f"分析市场数据失败: {str(e)}")
            raise

    async def execute_trade(self, analysis: MarketAnalysis):
        """执行交易"""
        try:
            # 获取当前持仓
            position = await self.exchange.get_position(self.symbol)
            current_position_size = float(position['size']) if position else 0
            
            # 获取当前价格
            ticker = await self.exchange.get_ticker(self.symbol)
            current_price = ticker['last']
            
            # 风险检查
            risk_check = await self.risk_manager.check_trade(
                self.symbol,
                current_price,
                current_position_size,
                0  # 当前回撤
            )
            
            if not risk_check['can_trade']:
                logging.info(f"[{self.symbol}] 风险检查未通过，不执行交易")
                return
            
            # 根据分析结果执行交易
            if analysis.suggested_action == "BUY" and analysis.sentiment > self.sentiment_threshold:
                # 计算交易量
                amount = self.risk_manager.calculate_position_size(
                    self.symbol,
                    current_price,
                    'long'
                )
                
                # 下单
                order = await self.exchange.place_order(
                    symbol=self.symbol,
                    side="buy",
                    order_type="market",
                    amount=amount
                )
                
                if order:
                    logging.info(f"[{self.symbol}] 买入成功: 数量={amount}, 价格={current_price}")
                    
            elif analysis.suggested_action == "SELL" and analysis.sentiment < -self.sentiment_threshold:
                # 计算交易量
                amount = self.risk_manager.calculate_position_size(
                    self.symbol,
                    current_price,
                    'short'
                )
                
                # 下单
                order = await self.exchange.place_order(
                    symbol=self.symbol,
                    side="sell",
                    order_type="market",
                    amount=amount
                )
                
                if order:
                    logging.info(f"[{self.symbol}] 卖出成功: 数量={amount}, 价格={current_price}")
            
            else:
                logging.info(f"[{self.symbol}] 保持观望，不执行交易")
                
        except Exception as e:
            logging.error(f"执行交易失败: {str(e)}")

    async def run(self):
        """运行策略"""
        try:
            # 获取市场数据
            klines = await self.exchange.get_kline_data(
                self.symbol,
                self.timeframe,
                limit=100
            )
            
            position = await self.exchange.get_position(self.symbol)
            funding_rate = await self.exchange.get_funding_rate(self.symbol)
            
            # 准备市场数据
            market_data = {
                'symbol': self.symbol,
                'klines': klines[-10:],  # 只使用最近10根K线
                'position': position,
                'funding_rate': funding_rate
            }
            
            # 分析市场
            analysis = await self.analyze_market(market_data)
            
            # 执行交易
            await self.execute_trade(analysis)
            
            # 更新风险指标
            await self.risk_manager.update_metrics(self.symbol)
            
        except Exception as e:
            logging.error(f"运行策略失败: {str(e)}")

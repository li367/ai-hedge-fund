#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API客户端模块
用于与外部数据服务提供商交互，获取股票价格、指标、新闻和内部交易数据
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Union, Any

import pandas as pd
import requests
from requests.exceptions import RequestException


class APIClient:
    """API客户端，用于与外部数据服务通信"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化API客户端
        
        参数:
            api_key: API密钥，默认从环境变量STOCK_API_KEY获取
            base_url: API基础URL，默认使用配置中的API_BASE_URL
        """
        self.api_key = api_key or os.getenv('STOCK_API_KEY', '')
        self.base_url = base_url or os.getenv('API_BASE_URL', 'https://api.example.com/v1')
        self.logger = logging.getLogger(__name__)
        
        if not self.api_key:
            self.logger.warning("API密钥未设置，可能无法获取某些数据")

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        发送API请求并获取响应
        
        参数:
            endpoint: API端点
            params: 请求参数字典
            
        返回:
            字典形式的API响应
        """
        if params is None:
            params = {}
            
        # 添加API密钥到参数中
        if self.api_key:
            params['apikey'] = self.api_key
            
        url = f"{self.base_url}/{endpoint}"
        
        try:
            self.logger.debug(f"发送请求到 {url} 参数: {params}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except RequestException as e:
            self.logger.error(f"API请求错误 ({url}): {str(e)}")
            raise
        except json.JSONDecodeError:
            self.logger.error(f"解析API响应失败: {response.text[:100]}...")
            raise ValueError("API返回了无效的JSON数据")

    def get_stock_prices(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取股票价格历史数据
        
        参数:
            ticker: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        返回:
            包含日期、开盘价、最高价、最低价、收盘价、成交量和调整收盘价的DataFrame
        """
        try:
            params = {
                'symbol': ticker,
                'from': start_date,
                'to': end_date
            }
            
            data = self._make_request(f"stocks/{ticker}/prices", params)
            
            if not data or 'prices' not in data:
                self.logger.warning(f"没有找到 {ticker} 的价格数据")
                return pd.DataFrame()
                
            df = pd.DataFrame(data['prices'])
            
            # 确保日期列转换为DatetimeIndex
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                
            return df
            
        except Exception as e:
            self.logger.error(f"获取 {ticker} 价格数据时出错: {str(e)}")
            return pd.DataFrame()

    def get_stock_metrics(self, ticker: str) -> pd.DataFrame:
        """
        获取股票基本面指标数据
        
        参数:
            ticker: 股票代码
            
        返回:
            包含各种财务指标的DataFrame
        """
        try:
            data = self._make_request(f"stocks/{ticker}/metrics")
            
            if not data or 'metrics' not in data:
                self.logger.warning(f"没有找到 {ticker} 的指标数据")
                return pd.DataFrame()
                
            # 将嵌套的JSON数据转换为DataFrame
            metrics_list = []
            for category, metrics in data['metrics'].items():
                for name, value in metrics.items():
                    metrics_list.append({
                        'category': category,
                        'metric': name,
                        'value': value
                    })
                    
            return pd.DataFrame(metrics_list)
            
        except Exception as e:
            self.logger.error(f"获取 {ticker} 指标数据时出错: {str(e)}")
            return pd.DataFrame()

    def get_stock_news(self, ticker: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取股票相关新闻
        
        参数:
            ticker: 股票代码
            days: 获取最近多少天的新闻
            
        返回:
            包含新闻标题、来源、URL等信息的列表
        """
        try:
            params = {
                'days': days
            }
            
            data = self._make_request(f"stocks/{ticker}/news", params)
            
            if not data or 'news' not in data:
                self.logger.warning(f"没有找到 {ticker} 的新闻数据")
                return []
                
            return data['news']
            
        except Exception as e:
            self.logger.error(f"获取 {ticker} 新闻数据时出错: {str(e)}")
            return []

    def get_insider_trading(self, ticker: str, months: int = 3) -> pd.DataFrame:
        """
        获取股票内部交易数据
        
        参数:
            ticker: 股票代码
            months: 获取最近多少个月的内部交易数据
            
        返回:
            包含内部交易信息的DataFrame
        """
        try:
            params = {
                'months': months
            }
            
            data = self._make_request(f"stocks/{ticker}/insider", params)
            
            if not data or 'transactions' not in data:
                self.logger.warning(f"没有找到 {ticker} 的内部交易数据")
                return pd.DataFrame()
                
            df = pd.DataFrame(data['transactions'])
            
            # 转换日期列
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                
            return df
            
        except Exception as e:
            self.logger.error(f"获取 {ticker} 内部交易数据时出错: {str(e)}")
            return pd.DataFrame()


# 创建默认API客户端实例
default_client = APIClient() 
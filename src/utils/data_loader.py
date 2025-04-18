#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据加载器模块
提供高效的股票数据加载功能，支持以下特性：
1. 双层缓存系统：内存缓存和磁盘缓存
2. 并行处理：同时加载多个股票数据
3. 内存优化：针对大型数据集自动优化内存使用
4. 支持加载不同类型的数据：价格、指标、新闻、内部交易
"""

import os
import time
import pickle
import hashlib
import logging
import shutil
from typing import List, Dict, Any, Union, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

import numpy as np
import pandas as pd

from src.utils.logger import setup_logger
from src.utils.api_client import APIClient

# 设置日志记录器
logger = setup_logger("data_loader")


class DataLoader:
    """
    优化的数据加载器，提供缓存、并行和内存优化功能

    属性:
        max_workers (int): 并行加载的最大工作线程数
        memory_cache (dict): 内存缓存，保存已加载的数据
        disk_cache_enabled (bool): 是否启用磁盘缓存
        memory_optimization (bool): 是否启用内存优化
        cache_timeout_days (int): 缓存过期时间（天）
        cache_dir (str): 磁盘缓存目录
        api (APIClient): API客户端实例
    """

    def __init__(
        self,
        max_workers: int = 10,
        disk_cache_enabled: bool = True,
        memory_optimization: bool = True,
        cache_timeout_days: int = 7,
        cache_dir: str = None,
    ):
        """
        初始化数据加载器

        参数:
            max_workers: 并行加载的最大工作线程数
            disk_cache_enabled: 是否启用磁盘缓存
            memory_optimization: 是否启用内存优化
            cache_timeout_days: 缓存过期时间（天）
            cache_dir: 磁盘缓存目录，默认为当前目录下的.cache
        """
        self.max_workers = max_workers
        self.memory_cache = {}
        self.disk_cache_enabled = disk_cache_enabled
        self.memory_optimization = memory_optimization
        self.cache_timeout_days = cache_timeout_days
        
        # 设置缓存目录
        if cache_dir is None:
            self.cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".cache")
        else:
            self.cache_dir = cache_dir
            
        # 确保缓存目录存在
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 初始化API客户端
        self.api = APIClient()
        
        logger.info(f"数据加载器初始化完成，缓存目录: {self.cache_dir}")
        
    def _generate_cache_key(self, ticker: str, start_date: str, end_date: str, data_type: str) -> str:
        """
        生成唯一的缓存键
        
        参数:
            ticker: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            data_type: 数据类型 (prices, metrics, news, insider)
            
        返回:
            str: 唯一的缓存键
        """
        key_str = f"{ticker}_{start_date}_{end_date}_{data_type}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_file: str) -> bool:
        """
        检查缓存文件是否有效（未过期）
        
        参数:
            cache_file: 缓存文件路径
            
        返回:
            bool: 如果缓存有效则为True，否则为False
        """
        if not os.path.exists(cache_file):
            return False
            
        # 检查文件修改时间
        mod_time = os.path.getmtime(cache_file)
        mod_date = datetime.fromtimestamp(mod_time)
        now = datetime.now()
        
        # 如果文件在过期时间内，则有效
        return (now - mod_date).days <= self.cache_timeout_days
    
    def _save_to_disk_cache(self, ticker: str, key: str, data: Any) -> None:
        """
        将数据保存到磁盘缓存
        
        参数:
            ticker: 股票代码
            key: 缓存键
            data: 要缓存的数据
        """
        if not self.disk_cache_enabled:
            return
            
        # 创建股票的缓存目录
        ticker_cache_dir = os.path.join(self.cache_dir, ticker)
        os.makedirs(ticker_cache_dir, exist_ok=True)
        
        # 保存数据到文件
        cache_file = os.path.join(ticker_cache_dir, f"{key}.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
            
        logger.debug(f"数据已保存到磁盘缓存: {cache_file}")
    
    def _load_from_disk_cache(self, ticker: str, key: str) -> Optional[Any]:
        """
        从磁盘缓存加载数据
        
        参数:
            ticker: 股票代码
            key: 缓存键
            
        返回:
            缓存的数据，如果不存在或已过期则为None
        """
        if not self.disk_cache_enabled:
            return None
            
        # 构建缓存文件路径
        ticker_cache_dir = os.path.join(self.cache_dir, ticker)
        cache_file = os.path.join(ticker_cache_dir, f"{key}.pkl")
        
        # 检查缓存是否有效
        if not self._is_cache_valid(cache_file):
            return None
            
        # 从文件加载数据
        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
                logger.debug(f"从磁盘缓存加载数据: {cache_file}")
                return data
        except Exception as e:
            logger.warning(f"从磁盘缓存加载数据失败: {e}")
            return None
    
    def _optimize_dataframe_memory(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        优化DataFrame的内存使用
        
        参数:
            df: 要优化的DataFrame
            
        返回:
            优化后的DataFrame
        """
        if not self.memory_optimization or df is None or df.empty:
            return df
            
        # 记录优化前内存使用
        before_mem = df.memory_usage(deep=True).sum()
        
        # 对数值列进行类型转换
        for col in df.columns:
            # 跳过日期类型
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                continue
                
            # 对整数列，使用最小的整数类型
            if pd.api.types.is_integer_dtype(df[col]):
                col_min = df[col].min()
                col_max = df[col].max()
                
                if col_min >= 0:
                    if col_max < 2**8:
                        df[col] = df[col].astype(np.uint8)
                    elif col_max < 2**16:
                        df[col] = df[col].astype(np.uint16)
                    elif col_max < 2**32:
                        df[col] = df[col].astype(np.uint32)
                else:
                    if col_min > -2**7 and col_max < 2**7:
                        df[col] = df[col].astype(np.int8)
                    elif col_min > -2**15 and col_max < 2**15:
                        df[col] = df[col].astype(np.int16)
                    elif col_min > -2**31 and col_max < 2**31:
                        df[col] = df[col].astype(np.int32)
            
            # 对浮点列，尝试使用float32
            elif pd.api.types.is_float_dtype(df[col]):
                # 检查精度损失
                f32_col = df[col].astype(np.float32)
                # 如果转换为float32后与原始数据的差异很小，则使用float32
                if np.allclose(df[col].dropna(), f32_col.dropna(), rtol=1e-4):
                    df[col] = f32_col
                    
        # 记录优化后内存使用
        after_mem = df.memory_usage(deep=True).sum()
        reduction = (before_mem - after_mem) / before_mem * 100
        
        logger.debug(f"DataFrame内存优化: {before_mem/1024/1024:.2f}MB -> {after_mem/1024/1024:.2f}MB "
                    f"(减少 {reduction:.2f}%)")
                    
        return df
    
    def _load_single_stock_data(
        self, 
        ticker: str, 
        start_date: str, 
        end_date: str,
        include_prices: bool = True,
        include_metrics: bool = False,
        include_news: bool = False,
        include_insider: bool = False
    ) -> Dict[str, Any]:
        """
        加载单个股票的数据
        
        参数:
            ticker: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            include_prices: 是否包含价格数据
            include_metrics: 是否包含指标数据
            include_news: 是否包含新闻数据
            include_insider: 是否包含内部交易数据
            
        返回:
            包含请求数据的字典
        """
        result = {}
        
        # 加载价格数据
        if include_prices:
            prices_key = self._generate_cache_key(ticker, start_date, end_date, "prices")
            
            # 尝试从内存缓存获取
            memory_cache_key = f"{ticker}_{prices_key}"
            if memory_cache_key in self.memory_cache:
                prices_data = self.memory_cache[memory_cache_key]
                logger.debug(f"{ticker}: 从内存缓存加载价格数据")
            else:
                # 尝试从磁盘缓存获取
                prices_data = self._load_from_disk_cache(ticker, prices_key)
                
                if prices_data is None:
                    # 从API获取数据
                    logger.info(f"{ticker}: 从API获取价格数据 ({start_date} 至 {end_date})")
                    try:
                        prices_data = self.api.get_stock_prices(ticker, start_date, end_date)
                        
                        # 优化内存使用
                        prices_data = self._optimize_dataframe_memory(prices_data)
                        
                        # 保存到缓存
                        self._save_to_disk_cache(ticker, prices_key, prices_data)
                        self.memory_cache[memory_cache_key] = prices_data
                    except Exception as e:
                        logger.error(f"{ticker}: 获取价格数据失败: {e}")
                        prices_data = pd.DataFrame()
                else:
                    # 保存到内存缓存
                    self.memory_cache[memory_cache_key] = prices_data
                    
            result['prices'] = prices_data
        
        # 加载指标数据
        if include_metrics:
            metrics_key = self._generate_cache_key(ticker, start_date, end_date, "metrics")
            
            # 尝试从内存缓存获取
            memory_cache_key = f"{ticker}_{metrics_key}"
            if memory_cache_key in self.memory_cache:
                metrics_data = self.memory_cache[memory_cache_key]
                logger.debug(f"{ticker}: 从内存缓存加载指标数据")
            else:
                # 尝试从磁盘缓存获取
                metrics_data = self._load_from_disk_cache(ticker, metrics_key)
                
                if metrics_data is None:
                    # 从API获取数据
                    logger.info(f"{ticker}: 从API获取指标数据")
                    try:
                        metrics_data = self.api.get_stock_metrics(ticker)
                        
                        # 优化内存使用
                        metrics_data = self._optimize_dataframe_memory(metrics_data)
                        
                        # 保存到缓存
                        self._save_to_disk_cache(ticker, metrics_key, metrics_data)
                        self.memory_cache[memory_cache_key] = metrics_data
                    except Exception as e:
                        logger.error(f"{ticker}: 获取指标数据失败: {e}")
                        metrics_data = pd.DataFrame()
                else:
                    # 保存到内存缓存
                    self.memory_cache[memory_cache_key] = metrics_data
                    
            result['metrics'] = metrics_data
            
        # 加载新闻数据
        if include_news:
            news_key = self._generate_cache_key(ticker, start_date, end_date, "news")
            
            # 尝试从内存缓存获取
            memory_cache_key = f"{ticker}_{news_key}"
            if memory_cache_key in self.memory_cache:
                news_data = self.memory_cache[memory_cache_key]
                logger.debug(f"{ticker}: 从内存缓存加载新闻数据")
            else:
                # 尝试从磁盘缓存获取
                news_data = self._load_from_disk_cache(ticker, news_key)
                
                if news_data is None:
                    # 从API获取数据
                    logger.info(f"{ticker}: 从API获取新闻数据")
                    try:
                        news_data = self.api.get_stock_news(ticker, start_date, end_date)
                        
                        # 保存到缓存
                        self._save_to_disk_cache(ticker, news_key, news_data)
                        self.memory_cache[memory_cache_key] = news_data
                    except Exception as e:
                        logger.error(f"{ticker}: 获取新闻数据失败: {e}")
                        news_data = []
                else:
                    # 保存到内存缓存
                    self.memory_cache[memory_cache_key] = news_data
                    
            result['news'] = news_data
            
        # 加载内部交易数据
        if include_insider:
            insider_key = self._generate_cache_key(ticker, start_date, end_date, "insider")
            
            # 尝试从内存缓存获取
            memory_cache_key = f"{ticker}_{insider_key}"
            if memory_cache_key in self.memory_cache:
                insider_data = self.memory_cache[memory_cache_key]
                logger.debug(f"{ticker}: 从内存缓存加载内部交易数据")
            else:
                # 尝试从磁盘缓存获取
                insider_data = self._load_from_disk_cache(ticker, insider_key)
                
                if insider_data is None:
                    # 从API获取数据
                    logger.info(f"{ticker}: 从API获取内部交易数据")
                    try:
                        insider_data = self.api.get_insider_trading(ticker, start_date, end_date)
                        
                        # 优化内存使用
                        insider_data = self._optimize_dataframe_memory(insider_data)
                        
                        # 保存到缓存
                        self._save_to_disk_cache(ticker, insider_key, insider_data)
                        self.memory_cache[memory_cache_key] = insider_data
                    except Exception as e:
                        logger.error(f"{ticker}: 获取内部交易数据失败: {e}")
                        insider_data = pd.DataFrame()
                else:
                    # 保存到内存缓存
                    self.memory_cache[memory_cache_key] = insider_data
                    
            result['insider'] = insider_data
            
        return result
    
    def load_stock_data(
        self, 
        tickers: Union[str, List[str]], 
        start_date: str, 
        end_date: str,
        include_prices: bool = True,
        include_metrics: bool = False,
        include_news: bool = False,
        include_insider: bool = False,
        show_progress: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        加载一个或多个股票的数据，支持并行处理
        
        参数:
            tickers: 单个股票代码或股票代码列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            include_prices: 是否包含价格数据
            include_metrics: 是否包含指标数据
            include_news: 是否包含新闻数据
            include_insider: 是否包含内部交易数据
            show_progress: 是否显示进度条
            
        返回:
            包含所有请求数据的字典，格式为 {ticker: {data_type: data}}
        """
        # 确保tickers是列表
        if isinstance(tickers, str):
            tickers = [tickers]
            
        # 如果只有一个股票，不使用并行
        if len(tickers) == 1:
            result = {
                tickers[0]: self._load_single_stock_data(
                    tickers[0], start_date, end_date,
                    include_prices, include_metrics, include_news, include_insider
                )
            }
            return result
            
        # 并行加载多个股票数据
        start_time = time.time()
        result = {}
        
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(tickers))) as executor:
            # 创建任务
            futures = {
                executor.submit(
                    self._load_single_stock_data,
                    ticker, start_date, end_date,
                    include_prices, include_metrics, include_news, include_insider
                ): ticker for ticker in tickers
            }
            
            # 处理结果
            if show_progress:
                iterator = tqdm(as_completed(futures), total=len(futures), desc="加载股票数据")
            else:
                iterator = as_completed(futures)
                
            for future in iterator:
                ticker = futures[future]
                try:
                    data = future.result()
                    result[ticker] = data
                except Exception as e:
                    logger.error(f"{ticker}: 加载数据时出错: {e}")
                    result[ticker] = {}
        
        elapsed_time = time.time() - start_time
        logger.info(f"加载了 {len(tickers)} 只股票的数据，耗时 {elapsed_time:.2f} 秒")
        
        return result
    
    def clear_cache(self, tickers: List[str] = None) -> None:
        """
        清除缓存数据
        
        参数:
            tickers: 要清除缓存的股票代码列表，如为None则清除所有缓存
        """
        # 清除内存缓存
        if tickers is None:
            self.memory_cache.clear()
            logger.info("已清除所有内存缓存")
            
            # 清除磁盘缓存
            if self.disk_cache_enabled and os.path.exists(self.cache_dir):
                for item in os.listdir(self.cache_dir):
                    item_path = os.path.join(self.cache_dir, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                logger.info("已清除所有磁盘缓存")
        else:
            # 清除特定股票的缓存
            for ticker in tickers:
                # 清除内存缓存
                keys_to_delete = [k for k in self.memory_cache.keys() if k.startswith(f"{ticker}_")]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                
                # 清除磁盘缓存
                if self.disk_cache_enabled:
                    ticker_cache_dir = os.path.join(self.cache_dir, ticker)
                    if os.path.exists(ticker_cache_dir):
                        shutil.rmtree(ticker_cache_dir)
                        
            logger.info(f"已清除 {len(tickers)} 只股票的缓存")


def load_stock_data(
    tickers: Union[str, List[str]], 
    start_date: str, 
    end_date: str,
    include_prices: bool = True,
    include_metrics: bool = False,
    include_news: bool = False,
    include_insider: bool = False,
    max_workers: int = 10,
    disk_cache_enabled: bool = True,
    memory_optimization: bool = True,
    cache_timeout_days: int = 7
) -> Dict[str, Dict[str, Any]]:
    """
    便捷函数：加载股票数据
    
    参数:
        tickers: 单个股票代码或股票代码列表
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        include_prices: 是否包含价格数据
        include_metrics: 是否包含指标数据
        include_news: 是否包含新闻数据
        include_insider: 是否包含内部交易数据
        max_workers: 并行加载的最大工作线程数
        disk_cache_enabled: 是否启用磁盘缓存
        memory_optimization: 是否启用内存优化
        cache_timeout_days: 缓存过期时间（天）
        
    返回:
        包含所有请求数据的字典，格式为 {ticker: {data_type: data}}
    """
    loader = DataLoader(
        max_workers=max_workers,
        disk_cache_enabled=disk_cache_enabled, 
        memory_optimization=memory_optimization,
        cache_timeout_days=cache_timeout_days
    )
    
    return loader.load_stock_data(
        tickers, start_date, end_date,
        include_prices, include_metrics, include_news, include_insider
    ) 
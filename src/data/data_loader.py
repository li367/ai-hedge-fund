#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据加载器模块
实现以下功能:
1. 内存缓存 - 减少重复API调用
2. 磁盘缓存 - 持久化数据以减少API调用
3. 并行加载 - 同时处理多个股票数据
4. 内存优化 - 优化大型历史数据集的内存使用
"""

import os
import time
import json
import hashlib
import logging
import datetime
import threading
from typing import Dict, List, Optional, Union, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import numpy as np

from src.utils.api_client import APIClient, default_client


class DataLoader:
    """数据加载器，用于加载和缓存股票数据"""
    
    # 类级别的内存缓存（所有实例共享）
    _memory_cache = {
        'prices': {},  # 价格数据缓存
        'metrics': {}, # 指标数据缓存
        'news': {},    # 新闻数据缓存
        'insider': {}  # 内部交易数据缓存
    }
    
    # 缓存锁，防止多线程访问冲突
    _cache_lock = threading.RLock()
    
    def __init__(
        self, 
        api_client: Optional[APIClient] = None,
        cache_dir: Optional[str] = None,
        max_workers: int = 4,
        memory_cache_enabled: bool = True,
        disk_cache_enabled: bool = True,
        memory_optimization: bool = False,
        cache_timeout_days: int = 1
    ):
        """
        初始化数据加载器
        
        参数:
            api_client: API客户端实例，默认使用全局默认客户端
            cache_dir: 缓存目录路径，默认为'~/.aihf/cache'
            max_workers: 并行加载时的最大工作线程数
            memory_cache_enabled: 是否启用内存缓存
            disk_cache_enabled: 是否启用磁盘缓存
            memory_optimization: 是否启用内存优化（用于大型数据集）
            cache_timeout_days: 缓存过期天数，默认1天
        """
        self.api_client = api_client or default_client
        self.max_workers = max_workers
        self.memory_cache_enabled = memory_cache_enabled
        self.disk_cache_enabled = disk_cache_enabled
        self.memory_optimization = memory_optimization
        self.cache_timeout_days = cache_timeout_days
        
        # 设置日志记录器
        self.logger = logging.getLogger(__name__)
        
        # 设置缓存目录
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            home_dir = Path.home()
            self.cache_dir = home_dir / '.aihf' / 'cache'
            
        # 创建缓存目录
        self._create_cache_directories()
    
    def _create_cache_directories(self) -> None:
        """创建缓存目录结构"""
        try:
            # 创建主缓存目录
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建数据类型子目录
            for data_type in ['prices', 'metrics', 'news', 'insider']:
                (self.cache_dir / data_type).mkdir(exist_ok=True)
                
            self.logger.debug(f"缓存目录创建成功: {self.cache_dir}")
        except Exception as e:
            self.logger.error(f"创建缓存目录时出错: {str(e)}")
            self.disk_cache_enabled = False  # 禁用磁盘缓存
    
    def _generate_cache_key(self, data_type: str, ticker: str, **params) -> str:
        """
        生成缓存键
        
        参数:
            data_type: 数据类型 ('prices', 'metrics', 'news', 'insider')
            ticker: 股票代码
            **params: 其他参数，用于区分不同的请求
            
        返回:
            缓存键
        """
        # 将所有参数排序并组合成字符串
        param_str = ticker.lower()
        
        # 添加其他参数
        if params:
            params_list = sorted([f"{k}={v}" for k, v in params.items()])
            param_str += "_" + "_".join(params_list)
            
        # 对较长的参数字符串使用哈希
        if len(param_str) > 100:
            return f"{ticker.lower()}_{hashlib.md5(param_str.encode()).hexdigest()}"
        
        return param_str
    
    def _get_cache_file_path(self, data_type: str, cache_key: str) -> Path:
        """
        获取缓存文件路径
        
        参数:
            data_type: 数据类型
            cache_key: 缓存键
            
        返回:
            缓存文件路径
        """
        return self.cache_dir / data_type / f"{cache_key}.pkl"
    
    def _save_to_disk_cache(self, data_type: str, cache_key: str, data: Any) -> bool:
        """
        保存数据到磁盘缓存
        
        参数:
            data_type: 数据类型
            cache_key: 缓存键
            data: 要缓存的数据
            
        返回:
            是否成功保存
        """
        if not self.disk_cache_enabled:
            return False
            
        try:
            cache_file = self._get_cache_file_path(data_type, cache_key)
            
            # 创建包含元数据的缓存对象
            cache_data = {
                'timestamp': time.time(),
                'data': data
            }
            
            # 保存到文件
            pd.to_pickle(cache_data, cache_file)
            self.logger.debug(f"数据已保存到磁盘缓存: {cache_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存到磁盘缓存时出错: {str(e)}")
            return False
    
    def _load_from_disk_cache(self, data_type: str, cache_key: str) -> Tuple[bool, Any]:
        """
        从磁盘缓存加载数据
        
        参数:
            data_type: 数据类型
            cache_key: 缓存键
            
        返回:
            (是否成功加载, 加载的数据)
        """
        if not self.disk_cache_enabled:
            return False, None
            
        try:
            cache_file = self._get_cache_file_path(data_type, cache_key)
            
            # 如果缓存文件不存在
            if not cache_file.exists():
                return False, None
                
            # 加载缓存数据
            cache_data = pd.read_pickle(cache_file)
            
            # 检查缓存是否过期
            timestamp = cache_data.get('timestamp', 0)
            cache_age = time.time() - timestamp
            if cache_age > (self.cache_timeout_days * 86400):  # 秒数转换为天
                self.logger.debug(f"缓存已过期: {cache_file}")
                return False, None
                
            self.logger.debug(f"从磁盘缓存加载数据: {cache_file}")
            return True, cache_data.get('data')
            
        except Exception as e:
            self.logger.error(f"从磁盘缓存加载数据时出错: {str(e)}")
            return False, None
    
    def _get_from_memory_cache(self, data_type: str, cache_key: str) -> Tuple[bool, Any]:
        """
        从内存缓存获取数据
        
        参数:
            data_type: 数据类型
            cache_key: 缓存键
            
        返回:
            (是否命中缓存, 缓存的数据)
        """
        if not self.memory_cache_enabled:
            return False, None
            
        # 使用锁保护缓存访问
        with self._cache_lock:
            cache = self._memory_cache.get(data_type, {})
            
            if cache_key in cache:
                cache_item = cache[cache_key]
                
                # 检查缓存是否过期
                timestamp = cache_item.get('timestamp', 0)
                cache_age = time.time() - timestamp
                
                if cache_age <= (self.cache_timeout_days * 86400):  # 秒数转换为天
                    self.logger.debug(f"内存缓存命中: {data_type}/{cache_key}")
                    return True, cache_item.get('data')
                else:
                    self.logger.debug(f"内存缓存已过期: {data_type}/{cache_key}")
            
            return False, None
    
    def _save_to_memory_cache(self, data_type: str, cache_key: str, data: Any) -> None:
        """
        保存数据到内存缓存
        
        参数:
            data_type: 数据类型
            cache_key: 缓存键
            data: 要缓存的数据
        """
        if not self.memory_cache_enabled:
            return
            
        # 使用锁保护缓存访问
        with self._cache_lock:
            if data_type not in self._memory_cache:
                self._memory_cache[data_type] = {}
                
            self._memory_cache[data_type][cache_key] = {
                'timestamp': time.time(),
                'data': data
            }
            
            self.logger.debug(f"数据已保存到内存缓存: {data_type}/{cache_key}")
    
    def _optimize_memory(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        优化DataFrame内存使用
        
        参数:
            df: 要优化的DataFrame
            
        返回:
            优化后的DataFrame
        """
        if not self.memory_optimization or df.empty:
            return df
            
        try:
            # 创建副本以避免修改原始数据
            result = df.copy()
            
            # 优化数值列
            for col in result.select_dtypes(include=['int', 'float']).columns:
                # 将int64降级为较小的int类型
                if result[col].dtype == 'int64':
                    # 检查最大最小值决定使用何种数据类型
                    col_min, col_max = result[col].min(), result[col].max()
                    
                    if col_min > np.iinfo(np.int8).min and col_max < np.iinfo(np.int8).max:
                        result[col] = result[col].astype(np.int8)
                    elif col_min > np.iinfo(np.int16).min and col_max < np.iinfo(np.int16).max:
                        result[col] = result[col].astype(np.int16)
                    elif col_min > np.iinfo(np.int32).min and col_max < np.iinfo(np.int32).max:
                        result[col] = result[col].astype(np.int32)
                
                # 将float64降级为float32
                elif result[col].dtype == 'float64':
                    result[col] = result[col].astype(np.float32)
            
            # 优化对象列，主要针对字符串
            for col in result.select_dtypes(include=['object']).columns:
                # 检查列是否是字符串类型
                if pd.api.types.is_string_dtype(result[col]):
                    # 尝试转换为分类类型
                    num_unique = result[col].nunique()
                    num_total = len(result)
                    
                    # 如果唯一值少于总数的50%，用分类类型更高效
                    if num_unique / num_total < 0.5:
                        result[col] = result[col].astype('category')
            
            self.logger.debug(f"内存使用优化: 从 {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB 减少到 "
                           f"{result.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
            
            return result
            
        except Exception as e:
            self.logger.error(f"优化内存使用时出错: {str(e)}")
            return df
    
    def get_stock_prices(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取股票价格历史数据（带缓存）
        
        参数:
            ticker: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        返回:
            包含价格数据的DataFrame
        """
        # 生成缓存键
        cache_key = self._generate_cache_key('prices', ticker, 
                                            start=start_date, end=end_date)
        
        # 尝试从内存缓存获取
        cache_hit, data = self._get_from_memory_cache('prices', cache_key)
        if cache_hit:
            return data
            
        # 尝试从磁盘缓存获取
        cache_hit, data = self._load_from_disk_cache('prices', cache_key)
        if cache_hit:
            # 如果从磁盘获取成功，也保存到内存缓存
            self._save_to_memory_cache('prices', cache_key, data)
            return data
            
        # 调用API获取数据
        df = self.api_client.get_stock_prices(ticker, start_date, end_date)
        
        # 优化内存使用
        if not df.empty:
            df = self._optimize_memory(df)
            
            # 保存到缓存
            self._save_to_memory_cache('prices', cache_key, df)
            self._save_to_disk_cache('prices', cache_key, df)
            
        return df
    
    def get_stock_metrics(self, ticker: str) -> pd.DataFrame:
        """
        获取股票基本面指标数据（带缓存）
        
        参数:
            ticker: 股票代码
            
        返回:
            包含指标数据的DataFrame
        """
        # 生成缓存键
        cache_key = self._generate_cache_key('metrics', ticker)
        
        # 尝试从内存缓存获取
        cache_hit, data = self._get_from_memory_cache('metrics', cache_key)
        if cache_hit:
            return data
            
        # 尝试从磁盘缓存获取
        cache_hit, data = self._load_from_disk_cache('metrics', cache_key)
        if cache_hit:
            # 如果从磁盘获取成功，也保存到内存缓存
            self._save_to_memory_cache('metrics', cache_key, data)
            return data
            
        # 调用API获取数据
        df = self.api_client.get_stock_metrics(ticker)
        
        # 优化内存使用
        if not df.empty:
            df = self._optimize_memory(df)
            
            # 保存到缓存
            self._save_to_memory_cache('metrics', cache_key, df)
            self._save_to_disk_cache('metrics', cache_key, df)
            
        return df
    
    def load_stocks_data(self, tickers: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        并行加载多个股票的价格数据
        
        参数:
            tickers: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        返回:
            字典，键为股票代码，值为价格数据DataFrame
        """
        result = {}
        
        if not tickers:
            return result
            
        # 如果只有一个股票，直接获取
        if len(tickers) == 1:
            ticker = tickers[0]
            result[ticker] = self.get_stock_prices(ticker, start_date, end_date)
            return result
            
        # 定义工作函数
        def _load_stock_data(ticker):
            try:
                df = self.get_stock_prices(ticker, start_date, end_date)
                return ticker, df
            except Exception as e:
                self.logger.error(f"加载 {ticker} 数据时出错: {str(e)}")
                return ticker, pd.DataFrame()
        
        # 使用线程池并行加载
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(tickers))) as executor:
            # 提交所有任务
            futures = [executor.submit(_load_stock_data, ticker) for ticker in tickers]
            
            # 收集结果
            for future in futures:
                try:
                    ticker, df = future.result()
                    result[ticker] = df
                except Exception as e:
                    self.logger.error(f"处理线程结果时出错: {str(e)}")
                    
        return result
    
    def clear_cache(self, data_type: Optional[str] = None, ticker: Optional[str] = None) -> None:
        """
        清除缓存
        
        参数:
            data_type: 要清除的数据类型，如果为None则清除所有类型
            ticker: 要清除的股票代码，如果为None则清除所有股票
        """
        # 清除内存缓存
        with self._cache_lock:
            if data_type and ticker:
                # 清除特定数据类型和股票的缓存
                if data_type in self._memory_cache:
                    keys_to_remove = []
                    for key in self._memory_cache[data_type]:
                        if key.startswith(ticker.lower()):
                            keys_to_remove.append(key)
                    
                    for key in keys_to_remove:
                        del self._memory_cache[data_type][key]
                        
                    self.logger.debug(f"已清除 {ticker} 的 {data_type} 内存缓存")
                    
            elif data_type:
                # 清除特定数据类型的所有缓存
                if data_type in self._memory_cache:
                    self._memory_cache[data_type] = {}
                    self.logger.debug(f"已清除所有 {data_type} 内存缓存")
                    
            elif ticker:
                # 清除特定股票所有类型的缓存
                for d_type in self._memory_cache:
                    keys_to_remove = []
                    for key in self._memory_cache[d_type]:
                        if key.startswith(ticker.lower()):
                            keys_to_remove.append(key)
                    
                    for key in keys_to_remove:
                        del self._memory_cache[d_type][key]
                        
                self.logger.debug(f"已清除 {ticker} 的所有内存缓存")
                
            else:
                # 清除所有缓存
                for d_type in self._memory_cache:
                    self._memory_cache[d_type] = {}
                    
                self.logger.debug("已清除所有内存缓存")
        
        # 清除磁盘缓存
        if self.disk_cache_enabled:
            try:
                if data_type and ticker:
                    # 清除特定数据类型和股票的缓存
                    cache_dir = self.cache_dir / data_type
                    if cache_dir.exists():
                        for cache_file in cache_dir.glob(f"{ticker.lower()}*"):
                            cache_file.unlink()
                        self.logger.debug(f"已清除 {ticker} 的 {data_type} 磁盘缓存")
                            
                elif data_type:
                    # 清除特定数据类型的所有缓存
                    cache_dir = self.cache_dir / data_type
                    if cache_dir.exists():
                        for cache_file in cache_dir.glob("*"):
                            cache_file.unlink()
                        self.logger.debug(f"已清除所有 {data_type} 磁盘缓存")
                        
                elif ticker:
                    # 清除特定股票所有类型的缓存
                    for d_type in ['prices', 'metrics', 'news', 'insider']:
                        cache_dir = self.cache_dir / d_type
                        if cache_dir.exists():
                            for cache_file in cache_dir.glob(f"{ticker.lower()}*"):
                                cache_file.unlink()
                    self.logger.debug(f"已清除 {ticker} 的所有磁盘缓存")
                    
                else:
                    # 清除所有缓存
                    for d_type in ['prices', 'metrics', 'news', 'insider']:
                        cache_dir = self.cache_dir / d_type
                        if cache_dir.exists():
                            for cache_file in cache_dir.glob("*"):
                                cache_file.unlink()
                    self.logger.debug("已清除所有磁盘缓存")
                    
            except Exception as e:
                self.logger.error(f"清除磁盘缓存时出错: {str(e)}")


# 便捷函数
def load_stock_data(ticker: str, start_date: str, end_date: str, **loader_kwargs) -> pd.DataFrame:
    """
    便捷函数：加载单个股票数据
    
    参数:
        ticker: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        **loader_kwargs: 传递给DataLoader构造函数的其他参数
        
    返回:
        价格数据DataFrame
    """
    loader = DataLoader(**loader_kwargs)
    return loader.get_stock_prices(ticker, start_date, end_date)


def load_multiple_stocks(tickers: List[str], start_date: str, end_date: str, **loader_kwargs) -> Dict[str, pd.DataFrame]:
    """
    便捷函数：并行加载多个股票数据
    
    参数:
        tickers: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        **loader_kwargs: 传递给DataLoader构造函数的其他参数
        
    返回:
        字典，键为股票代码，值为价格数据DataFrame
    """
    loader = DataLoader(**loader_kwargs)
    return loader.load_stocks_data(tickers, start_date, end_date) 
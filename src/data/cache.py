#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
高级缓存系统模块
实现以下功能:
1. 多级缓存 - 内存缓存和磁盘缓存结合
2. 并行访问安全 - 线程锁保护共享资源
3. 内存优化 - 针对大型数据集的内存优化策略
4. 缓存过期机制 - 自动管理缓存生命周期
"""

import os
import time
import json
import hashlib
import logging
import threading
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pickle

import pandas as pd
import numpy as np

from src.data.models import (
    PriceResponse, 
    FinancialMetricsResponse, 
    LineItemResponse, 
    InsiderTradeResponse, 
    CompanyNewsResponse
)


class Cache:
    """
    高级缓存系统，支持内存缓存和磁盘缓存，线程安全，内存优化
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        memory_cache_enabled: bool = True,
        disk_cache_enabled: bool = True,
        cache_timeout_days: int = 1,
        memory_optimization: bool = True,
        max_memory_items: int = 1000
    ):
        """
        初始化缓存系统

        参数:
            cache_dir: 缓存目录路径，默认为'~/.aihf/cache'
            memory_cache_enabled: 是否启用内存缓存
            disk_cache_enabled: 是否启用磁盘缓存
            cache_timeout_days: 缓存过期天数
            memory_optimization: 是否启用内存优化
            max_memory_items: 内存缓存最大条目数
        """
        # 缓存配置
        self.memory_cache_enabled = memory_cache_enabled
        self.disk_cache_enabled = disk_cache_enabled
        self.cache_timeout_days = cache_timeout_days
        self.memory_optimization = memory_optimization
        self.max_memory_items = max_memory_items
        
        # 设置缓存目录
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            home_dir = Path.home()
            self.cache_dir = home_dir / '.aihf' / 'cache'
        
        # 创建缓存目录
        self._create_cache_directories()
        
        # 内存缓存
        self._prices_cache = {}
        self._metrics_cache = {}
        self._line_items_cache = {}
        self._insider_trades_cache = {}
        self._company_news_cache = {}
        
        # 缓存访问次数记录 (用于LRU淘汰策略)
        self._cache_hits = {
            'prices': {},
            'metrics': {},
            'line_items': {},
            'insider_trades': {},
            'company_news': {},
        }
        
        # 缓存锁，防止多线程访问冲突
        self._cache_lock = threading.RLock()
        
        # 初始化日志记录器
        self.logger = logging.getLogger(__name__)
    
    def _create_cache_directories(self) -> None:
        """创建缓存目录结构"""
        try:
            # 创建主缓存目录
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建数据类型子目录
            for data_type in ['prices', 'metrics', 'line_items', 'insider_trades', 'company_news']:
                (self.cache_dir / data_type).mkdir(exist_ok=True)
                
            self.logger.debug(f"缓存目录创建成功: {self.cache_dir}")
        except Exception as e:
            self.logger.error(f"创建缓存目录时出错: {str(e)}")
            self.disk_cache_enabled = False  # 禁用磁盘缓存
    
    def _generate_cache_key(self, data_type: str, ticker: str, **params) -> str:
        """
        生成缓存键

        参数:
            data_type: 数据类型
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
    
    def _merge_data(self, existing_data: List, new_data: List, key_field: str) -> List:
        """
        合并现有数据和新数据，避免重复
        
        参数:
            existing_data: 现有数据列表
            new_data: 新数据列表
            key_field: 用于识别重复项的字段名
            
        返回:
            合并后的数据列表
        """
        if not existing_data:
            return new_data

        if not new_data:
            return existing_data
            
        # 创建现有数据的键集合
        existing_keys = {item.get(key_field) for item in existing_data if hasattr(item, key_field)}
        
        # 过滤掉重复的新数据
        unique_new_data = [item for item in new_data if not hasattr(item, key_field) or item.get(key_field) not in existing_keys]
        
        # 合并数据
        return existing_data + unique_new_data
    
    def _optimize_memory(self, data: Any) -> Any:
        """
        对数据进行内存优化
        
        参数:
            data: 要优化的数据
            
        返回:
            优化后的数据
        """
        if not self.memory_optimization:
            return data
            
        # 对DataFrame进行优化
        if isinstance(data, pd.DataFrame):
            # 优化数值类型列
            for col in data.select_dtypes(include=['float64']).columns:
                data[col] = pd.to_numeric(data[col], downcast='float')
                
            for col in data.select_dtypes(include=['int64']).columns:
                data[col] = pd.to_numeric(data[col], downcast='integer')
                
            # 优化对象类型列 (字符串)
            for col in data.select_dtypes(include=['object']).columns:
                if data[col].nunique() / len(data) < 0.5:  # 如果唯一值比例低于50%
                    data[col] = data[col].astype('category')
                    
        return data
    
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
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
                
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
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # 检查缓存是否过期
            timestamp = cache_data.get('timestamp', 0)
            cache_age = time.time() - timestamp
            if cache_age > (self.cache_timeout_days * 86400):  # 秒数转换为天
                self.logger.debug(f"磁盘缓存已过期: {cache_file}")
                return False, None
                
            # 返回缓存数据
            data = cache_data.get('data')
            self.logger.debug(f"从磁盘缓存加载数据: {cache_file}")
            return True, data
            
        except Exception as e:
            self.logger.error(f"从磁盘缓存加载数据时出错: {str(e)}")
            return False, None
    
    def _enforce_memory_limits(self, cache_dict: Dict, cache_type: str) -> None:
        """
        确保内存缓存不超过限制
        
        参数:
            cache_dict: 缓存字典
            cache_type: 缓存类型名称
        """
        if len(cache_dict) <= self.max_memory_items:
            return
            
        # 使用LRU策略淘汰最少使用的缓存项
        hits = self._cache_hits[cache_type]
        
        # 按访问次数排序
        sorted_keys = sorted(cache_dict.keys(), key=lambda k: hits.get(k, 0))
        
        # 移除最少使用的项，直到达到限制
        keys_to_remove = sorted_keys[:len(cache_dict) - self.max_memory_items]
        for key in keys_to_remove:
            if key in cache_dict:
                del cache_dict[key]
            if key in hits:
                del hits[key]
                
        self.logger.debug(f"已从 {cache_type} 缓存中移除 {len(keys_to_remove)} 项")
    
    def _update_cache_hit(self, cache_type: str, key: str) -> None:
        """
        更新缓存命中计数
        
        参数:
            cache_type: 缓存类型
            key: 缓存键
        """
        with self._cache_lock:
            self._cache_hits[cache_type][key] = self._cache_hits[cache_type].get(key, 0) + 1
    
    def get_prices(self, ticker: str, start_date: str, end_date: str) -> Optional[PriceResponse]:
        """
        获取价格数据，优先从缓存获取
        
        参数:
            ticker: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        返回:
            价格数据响应对象，如果缓存未命中则返回None
        """
        cache_key = self._generate_cache_key('prices', ticker, start_date=start_date, end_date=end_date)
        
        # 先尝试从内存缓存获取
        if self.memory_cache_enabled:
            with self._cache_lock:
                if cache_key in self._prices_cache:
                    self._update_cache_hit('prices', cache_key)
                    return self._prices_cache[cache_key]
        
        # 再尝试从磁盘缓存获取
        if self.disk_cache_enabled:
            success, data = self._load_from_disk_cache('prices', cache_key)
            if success:
                # 更新内存缓存
                if self.memory_cache_enabled:
                    with self._cache_lock:
                        self._prices_cache[cache_key] = data
                        self._update_cache_hit('prices', cache_key)
                        self._enforce_memory_limits(self._prices_cache, 'prices')
                return data
                
        return None
    
    def set_prices(self, ticker: str, start_date: str, end_date: str, data: PriceResponse) -> None:
        """
        设置价格数据缓存
        
        参数:
            ticker: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            data: 价格数据响应对象
        """
        cache_key = self._generate_cache_key('prices', ticker, start_date=start_date, end_date=end_date)
        
        # 优化数据
        if self.memory_optimization:
            data = self._optimize_memory(data)
        
        # 更新内存缓存
        if self.memory_cache_enabled:
            with self._cache_lock:
                self._prices_cache[cache_key] = data
                self._update_cache_hit('prices', cache_key)
                self._enforce_memory_limits(self._prices_cache, 'prices')
        
        # 更新磁盘缓存
        if self.disk_cache_enabled:
            self._save_to_disk_cache('prices', cache_key, data)
    
    def get_metrics(self, ticker: str) -> Optional[FinancialMetricsResponse]:
        """
        获取财务指标数据，优先从缓存获取
        
        参数:
            ticker: 股票代码
            
        返回:
            财务指标数据响应对象，如果缓存未命中则返回None
        """
        cache_key = self._generate_cache_key('metrics', ticker)
        
        # 先尝试从内存缓存获取
        if self.memory_cache_enabled:
            with self._cache_lock:
                if cache_key in self._metrics_cache:
                    self._update_cache_hit('metrics', cache_key)
                    return self._metrics_cache[cache_key]
        
        # 再尝试从磁盘缓存获取
        if self.disk_cache_enabled:
            success, data = self._load_from_disk_cache('metrics', cache_key)
            if success:
                # 更新内存缓存
                if self.memory_cache_enabled:
                    with self._cache_lock:
                        self._metrics_cache[cache_key] = data
                        self._update_cache_hit('metrics', cache_key)
                        self._enforce_memory_limits(self._metrics_cache, 'metrics')
                return data
                
        return None
    
    def set_metrics(self, ticker: str, data: FinancialMetricsResponse) -> None:
        """
        设置财务指标数据缓存
        
        参数:
            ticker: 股票代码
            data: 财务指标数据响应对象
        """
        cache_key = self._generate_cache_key('metrics', ticker)
        
        # 优化数据
        if self.memory_optimization:
            data = self._optimize_memory(data)
        
        # 更新内存缓存
        if self.memory_cache_enabled:
            with self._cache_lock:
                self._metrics_cache[cache_key] = data
                self._update_cache_hit('metrics', cache_key)
                self._enforce_memory_limits(self._metrics_cache, 'metrics')
        
        # 更新磁盘缓存
        if self.disk_cache_enabled:
            self._save_to_disk_cache('metrics', cache_key, data)
    
    def get_line_items(self, ticker: str, **query_params) -> Optional[LineItemResponse]:
        """
        获取财务项目数据，优先从缓存获取
        
        参数:
            ticker: 股票代码
            **query_params: 查询参数
            
        返回:
            财务项目数据响应对象，如果缓存未命中则返回None
        """
        cache_key = self._generate_cache_key('line_items', ticker, **query_params)
        
        # 先尝试从内存缓存获取
        if self.memory_cache_enabled:
            with self._cache_lock:
                if cache_key in self._line_items_cache:
                    self._update_cache_hit('line_items', cache_key)
                    return self._line_items_cache[cache_key]
        
        # 再尝试从磁盘缓存获取
        if self.disk_cache_enabled:
            success, data = self._load_from_disk_cache('line_items', cache_key)
            if success:
                # 更新内存缓存
                if self.memory_cache_enabled:
                    with self._cache_lock:
                        self._line_items_cache[cache_key] = data
                        self._update_cache_hit('line_items', cache_key)
                        self._enforce_memory_limits(self._line_items_cache, 'line_items')
                return data
                
        return None
    
    def set_line_items(self, ticker: str, data: LineItemResponse, **query_params) -> None:
        """
        设置财务项目数据缓存
        
        参数:
            ticker: 股票代码
            data: 财务项目数据响应对象
            **query_params: 查询参数
        """
        cache_key = self._generate_cache_key('line_items', ticker, **query_params)
        
        # 优化数据
        if self.memory_optimization:
            data = self._optimize_memory(data)
        
        # 更新内存缓存
        if self.memory_cache_enabled:
            with self._cache_lock:
                self._line_items_cache[cache_key] = data
                self._update_cache_hit('line_items', cache_key)
                self._enforce_memory_limits(self._line_items_cache, 'line_items')
        
        # 更新磁盘缓存
        if self.disk_cache_enabled:
            self._save_to_disk_cache('line_items', cache_key, data)
    
    def get_insider_trades(self, ticker: str) -> Optional[InsiderTradeResponse]:
        """
        获取内部交易数据，优先从缓存获取
        
        参数:
            ticker: 股票代码
            
        返回:
            内部交易数据响应对象，如果缓存未命中则返回None
        """
        cache_key = self._generate_cache_key('insider_trades', ticker)
        
        # 先尝试从内存缓存获取
        if self.memory_cache_enabled:
            with self._cache_lock:
                if cache_key in self._insider_trades_cache:
                    self._update_cache_hit('insider_trades', cache_key)
                    return self._insider_trades_cache[cache_key]
        
        # 再尝试从磁盘缓存获取
        if self.disk_cache_enabled:
            success, data = self._load_from_disk_cache('insider_trades', cache_key)
            if success:
                # 更新内存缓存
                if self.memory_cache_enabled:
                    with self._cache_lock:
                        self._insider_trades_cache[cache_key] = data
                        self._update_cache_hit('insider_trades', cache_key)
                        self._enforce_memory_limits(self._insider_trades_cache, 'insider_trades')
                return data
                
        return None
    
    def set_insider_trades(self, ticker: str, data: InsiderTradeResponse) -> None:
        """
        设置内部交易数据缓存
        
        参数:
            ticker: 股票代码
            data: 内部交易数据响应对象
        """
        cache_key = self._generate_cache_key('insider_trades', ticker)
        
        # 优化数据
        if self.memory_optimization:
            data = self._optimize_memory(data)
        
        # 更新内存缓存
        if self.memory_cache_enabled:
            with self._cache_lock:
                self._insider_trades_cache[cache_key] = data
                self._update_cache_hit('insider_trades', cache_key)
                self._enforce_memory_limits(self._insider_trades_cache, 'insider_trades')
        
        # 更新磁盘缓存
        if self.disk_cache_enabled:
            self._save_to_disk_cache('insider_trades', cache_key, data)
    
    def get_company_news(self, ticker: str, days: int = 30) -> Optional[CompanyNewsResponse]:
        """
        获取公司新闻数据，优先从缓存获取
        
        参数:
            ticker: 股票代码
            days: 新闻天数
            
        返回:
            公司新闻数据响应对象，如果缓存未命中则返回None
        """
        cache_key = self._generate_cache_key('company_news', ticker, days=days)
        
        # 先尝试从内存缓存获取
        if self.memory_cache_enabled:
            with self._cache_lock:
                if cache_key in self._company_news_cache:
                    self._update_cache_hit('company_news', cache_key)
                    return self._company_news_cache[cache_key]
        
        # 再尝试从磁盘缓存获取
        if self.disk_cache_enabled:
            success, data = self._load_from_disk_cache('company_news', cache_key)
            if success:
                # 更新内存缓存
                if self.memory_cache_enabled:
                    with self._cache_lock:
                        self._company_news_cache[cache_key] = data
                        self._update_cache_hit('company_news', cache_key)
                        self._enforce_memory_limits(self._company_news_cache, 'company_news')
                return data
                
        return None
    
    def set_company_news(self, ticker: str, data: CompanyNewsResponse, days: int = 30) -> None:
        """
        设置公司新闻数据缓存
        
        参数:
            ticker: 股票代码
            data: 公司新闻数据响应对象
            days: 新闻天数
        """
        cache_key = self._generate_cache_key('company_news', ticker, days=days)
        
        # 优化数据
        if self.memory_optimization:
            data = self._optimize_memory(data)
        
        # 更新内存缓存
        if self.memory_cache_enabled:
            with self._cache_lock:
                self._company_news_cache[cache_key] = data
                self._update_cache_hit('company_news', cache_key)
                self._enforce_memory_limits(self._company_news_cache, 'company_news')
        
        # 更新磁盘缓存
        if self.disk_cache_enabled:
            self._save_to_disk_cache('company_news', cache_key, data)
    
    def clear_cache(self, data_type: Optional[str] = None, ticker: Optional[str] = None) -> None:
        """
        清除缓存数据
        
        参数:
            data_type: 可选，要清除的数据类型
            ticker: 可选，要清除的股票代码
        """
        with self._cache_lock:
            # 确定要清除的数据类型
            data_types = []
            if data_type:
                data_types.append(data_type)
            else:
                data_types = ['prices', 'metrics', 'line_items', 'insider_trades', 'company_news']
            
            # 清除内存缓存
            if self.memory_cache_enabled:
                for dt in data_types:
                    cache_dict = getattr(self, f"_{dt}_cache", {})
                    if ticker:
                        # 清除特定股票的缓存
                        keys_to_remove = [k for k in cache_dict if k.startswith(ticker.lower())]
                        for k in keys_to_remove:
                            if k in cache_dict:
                                del cache_dict[k]
                    else:
                        # 清除所有缓存
                        cache_dict.clear()
                    
                    # 清除对应的缓存命中记录
                    if dt in self._cache_hits:
                        if ticker:
                            keys_to_remove = [k for k in self._cache_hits[dt] if k.startswith(ticker.lower())]
                            for k in keys_to_remove:
                                if k in self._cache_hits[dt]:
                                    del self._cache_hits[dt][k]
                        else:
                            self._cache_hits[dt].clear()
            
            # 清除磁盘缓存
            if self.disk_cache_enabled:
                for dt in data_types:
                    cache_dir = self.cache_dir / dt
                    if cache_dir.exists():
                        if ticker:
                            # 清除特定股票的缓存文件
                            for file in cache_dir.glob(f"{ticker.lower()}*.pkl"):
                                try:
                                    file.unlink()
                                except Exception as e:
                                    self.logger.error(f"删除缓存文件时出错: {str(e)}")
                        else:
                            # 清除所有缓存文件
                            for file in cache_dir.glob("*.pkl"):
                                try:
                                    file.unlink()
                                except Exception as e:
                                    self.logger.error(f"删除缓存文件时出错: {str(e)}")


# 全局缓存实例
_cache = None


def get_cache() -> Cache:
    """
    获取全局缓存实例
    
    返回:
        缓存实例
    """
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache

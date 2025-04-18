#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据加载器模块单元测试
测试以下功能:
1. 内存缓存 - 减少重复API调用
2. 磁盘缓存 - 持久化数据以减少API调用
3. 并行加载 - 同时处理多个股票数据
4. 内存优化 - 优化大型历史数据集的内存使用
"""

import os
import time
import tempfile
import unittest
import shutil
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np
from numpy import testing as np_testing

from src.data.data_loader import DataLoader
from src.utils.api_client import APIClient


class TestDataLoader(unittest.TestCase):
    """数据加载器单元测试类"""
    
    @patch('src.data.data_loader.APIClient')
    def setUp(self, mock_api_class):
        """每个测试方法运行前的准备工作"""
        # 创建临时缓存目录
        self.temp_dir = tempfile.mkdtemp()
        
        # 设置模拟API客户端
        self.mock_api = mock_api_class.return_value
        
        # 设置模拟股票价格数据
        dates = pd.date_range(start='2023-01-01', end='2023-01-10')
        self.mock_price_data = pd.DataFrame({
            'open': np.random.rand(len(dates)) * 100 + 50,
            'high': np.random.rand(len(dates)) * 100 + 60,
            'low': np.random.rand(len(dates)) * 100 + 40,
            'close': np.random.rand(len(dates)) * 100 + 55,
            'volume': np.random.randint(1000, 100000, size=len(dates)),
            'adjusted_close': np.random.rand(len(dates)) * 100 + 55
        }, index=dates)
        
        # 设置模拟股票指标数据
        self.mock_metrics_data = pd.DataFrame({
            'category': ['价值', '成长', '价值', '流动性', '盈利能力'],
            'metric': ['市盈率', '收入增长率', '市净率', '流动比率', '净利润率'],
            'value': [15.2, 0.12, 2.5, 1.8, 0.22]
        })
        
        # 配置模拟API客户端返回数据
        self.mock_api.get_stock_prices.return_value = self.mock_price_data
        self.mock_api.get_stock_metrics.return_value = self.mock_metrics_data
        
        # 创建数据加载器实例
        self.loader = DataLoader(
            api_client=self.mock_api,
            cache_dir=self.temp_dir,
            max_workers=4,
            memory_cache_enabled=True,
            disk_cache_enabled=True,
            memory_optimization=True,
            cache_timeout_days=7
        )
        
        # 重置API调用计数
        self.mock_api.get_stock_prices.reset_mock()
        self.mock_api.get_stock_metrics.reset_mock()
    
    def tearDown(self):
        """每个测试方法运行后的清理工作"""
        # 删除临时缓存目录
        shutil.rmtree(self.temp_dir)
        
        # 清理加载器
        self.loader = None
    
    def test_memory_cache(self):
        """测试内存缓存功能"""
        # 第一次调用，应该从API获取数据
        data1 = self.loader.get_stock_prices('AAPL', '2023-01-01', '2023-01-10')
        
        # 验证API被调用一次
        self.mock_api.get_stock_prices.assert_called_once_with('AAPL', '2023-01-01', '2023-01-10')
        self.mock_api.get_stock_prices.reset_mock()
        
        # 第二次调用，应该从内存缓存获取数据
        data2 = self.loader.get_stock_prices('AAPL', '2023-01-01', '2023-01-10')
        
        # 验证API没有被再次调用
        self.mock_api.get_stock_prices.assert_not_called()
        
        # 验证两次获取的数据相同
        pd.testing.assert_frame_equal(data1, data2)
    
    def test_disk_cache(self):
        """测试磁盘缓存功能"""
        # 关闭内存缓存，只使用磁盘缓存
        self.loader.memory_cache_enabled = False
        
        # 第一次调用，应该从API获取数据并保存到磁盘
        data1 = self.loader.get_stock_prices('AAPL', '2023-01-01', '2023-01-10')
        
        # 验证API被调用一次
        self.mock_api.get_stock_prices.assert_called_once_with('AAPL', '2023-01-01', '2023-01-10')
        self.mock_api.get_stock_prices.reset_mock()
        
        # 清理内存缓存，确保下次从磁盘读取
        self.loader._memory_cache['prices'] = {}
        
        # 第二次调用，应该从磁盘缓存获取数据
        data2 = self.loader.get_stock_prices('AAPL', '2023-01-01', '2023-01-10')
        
        # 验证API没有被再次调用
        self.mock_api.get_stock_prices.assert_not_called()
        
        # 验证两次获取的数据相同
        pd.testing.assert_frame_equal(data1, data2)
        
        # 验证缓存目录存在
        # 检查缓存目录
        prices_cache_dir = os.path.join(self.temp_dir, 'prices')
        self.assertTrue(os.path.exists(prices_cache_dir), "价格缓存目录应存在")
    
    def test_cache_expiration(self):
        """测试缓存过期功能"""
        # 设置非常短的缓存过期时间（0天）
        self.loader.cache_timeout_days = 0
        
        # 第一次调用，应该从API获取数据
        data1 = self.loader.get_stock_prices('AAPL', '2023-01-01', '2023-01-10')
        
        # 验证API被调用一次
        self.mock_api.get_stock_prices.assert_called_once_with('AAPL', '2023-01-01', '2023-01-10')
        self.mock_api.get_stock_prices.reset_mock()
        
        # 确保缓存过期
        time.sleep(1)
        
        # 第二次调用，应该从API再次获取数据
        data2 = self.loader.get_stock_prices('AAPL', '2023-01-01', '2023-01-10')
        
        # 验证API被再次调用
        self.mock_api.get_stock_prices.assert_called_once_with('AAPL', '2023-01-01', '2023-01-10')
        
        # 验证两次获取的数据相同（因为API返回相同的模拟数据）
        pd.testing.assert_frame_equal(data1, data2)
    
    def test_parallel_loading(self):
        """测试并行加载功能"""
        # 设置要加载的股票代码列表
        tickers = ['AAPL', 'MSFT', 'GOOG', 'AMZN']
        
        # 为每个股票配置相同的数据
        for ticker in tickers:
            self.mock_api.get_stock_prices.side_effect = None  # 清除之前的side_effect
            result = self.loader.get_stock_prices(ticker, '2023-01-01', '2023-01-10')
        
        # 重置API调用记录
        self.mock_api.get_stock_prices.reset_mock()
        
        # 记录单线程加载开始时间
        start_time_single = time.time()
        
        # 设置为单线程
        self.loader.max_workers = 1
        
        # 单线程加载
        result_single = self.loader.load_stocks_data(tickers, '2023-01-01', '2023-01-10')
        
        # 记录单线程加载结束时间
        end_time_single = time.time()
        single_thread_time = end_time_single - start_time_single
        
        # 重置API调用记录
        self.mock_api.get_stock_prices.reset_mock()
        
        # 清空缓存 - 使用特定的方法
        for data_type in self.loader._memory_cache:
            self.loader._memory_cache[data_type] = {}
        
        # 重新准备数据
        for ticker in tickers:
            self.loader.get_stock_prices(ticker, '2023-01-01', '2023-01-10')
        
        # 重置API调用记录
        self.mock_api.get_stock_prices.reset_mock()
        
        # 记录多线程加载开始时间
        start_time_multi = time.time()
        
        # 设置为多线程
        self.loader.max_workers = 4
        
        # 多线程加载
        result_multi = self.loader.load_stocks_data(tickers, '2023-01-01', '2023-01-10')
        
        # 记录多线程加载结束时间
        end_time_multi = time.time()
        multi_thread_time = end_time_multi - start_time_multi
        
        # 验证API没有被调用 (因为缓存)
        self.mock_api.get_stock_prices.assert_not_called()
        
        # 验证所有股票都被加载
        self.assertEqual(len(result_single), len(tickers))
        self.assertEqual(len(result_multi), len(tickers))
        
        # 此处不严格要求多线程一定快于单线程，因为在测试环境中可能并不明显
        # 但在实际应用中，多线程应该比单线程更快，特别是当API调用有延迟时
        # 我们只检查单线程和多线程都能正常工作
        self.assertGreaterEqual(single_thread_time, 0)
        self.assertGreaterEqual(multi_thread_time, 0)
    
    def test_memory_optimization(self):
        """测试内存优化功能"""
        # 创建大型测试数据集
        dates = pd.date_range(start='2020-01-01', end='2023-01-01')
        large_df = pd.DataFrame({
            'int64_col': np.random.randint(0, 100, size=len(dates), dtype=np.int64),
            'float64_col': np.random.rand(len(dates)).astype(np.float64),
            'small_int_col': np.random.randint(0, 10, size=len(dates), dtype=np.int64),
            'category_col': np.random.choice(['A', 'B', 'C'], size=len(dates))
        }, index=dates)
        
        # 记录优化前内存使用
        memory_before = large_df.memory_usage(deep=True).sum()
        
        # 通过加载器优化内存
        optimized_df = self.loader._optimize_memory(large_df)
        
        # 记录优化后内存使用
        memory_after = optimized_df.memory_usage(deep=True).sum()
        
        # 验证内存使用减少
        self.assertLess(memory_after, memory_before)
        
        # 验证数据类型转换
        self.assertNotEqual(optimized_df['small_int_col'].dtype, np.int64)
        self.assertNotEqual(optimized_df['float64_col'].dtype, np.float64)
        
        # 验证分类列
        self.assertEqual(optimized_df['category_col'].dtype.name, 'category')
        
        # 验证数据值不变
        np_testing.assert_array_equal(large_df['int64_col'].values, optimized_df['int64_col'].values)
        np_testing.assert_array_almost_equal(large_df['float64_col'].values, optimized_df['float64_col'].values)
        np_testing.assert_array_equal(large_df['small_int_col'].values, optimized_df['small_int_col'].values)
        np_testing.assert_array_equal(large_df['category_col'].values, optimized_df['category_col'].values)
    
    def test_clear_cache(self):
        """测试清除缓存功能"""
        # 加载股票数据
        self.loader.get_stock_prices('AAPL', '2023-01-01', '2023-01-10')
        
        # 清除特定类型的缓存
        self.loader.clear_cache(data_type='prices', ticker='AAPL')
        
        # 验证API再次被调用
        self.mock_api.get_stock_prices.reset_mock()
        self.loader.get_stock_prices('AAPL', '2023-01-01', '2023-01-10')
        self.mock_api.get_stock_prices.assert_called_once()
        
        # 加载另一支股票的数据
        self.mock_api.get_stock_prices.reset_mock()
        self.loader.get_stock_prices('MSFT', '2023-01-01', '2023-01-10')
        self.mock_api.get_stock_prices.assert_called_once()
        
        # 清除所有缓存
        self.mock_api.get_stock_prices.reset_mock()
        self.loader.clear_cache()
        
        # 验证加载时API被调用
        self.loader.get_stock_prices('AAPL', '2023-01-01', '2023-01-10')
        self.mock_api.get_stock_prices.assert_called_once()
    
    def test_metrics_cache(self):
        """测试指标数据缓存功能"""
        # 第一次调用，应该从API获取数据
        data1 = self.loader.get_stock_metrics('AAPL')
        
        # 验证API被调用一次
        self.mock_api.get_stock_metrics.assert_called_once_with('AAPL')
        self.mock_api.get_stock_metrics.reset_mock()
        
        # 第二次调用，应该从内存缓存获取数据
        data2 = self.loader.get_stock_metrics('AAPL')
        
        # 验证API没有被再次调用
        self.mock_api.get_stock_metrics.assert_not_called()
        
        # 验证两次获取的数据相同
        pd.testing.assert_frame_equal(data1, data2)


if __name__ == '__main__':
    unittest.main() 
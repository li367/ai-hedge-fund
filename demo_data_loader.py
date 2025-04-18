#!/usr/bin/env python
"""
数据加载器演示脚本

演示新数据加载器的功能:
1. 并行加载多只股票数据
2. 内存和磁盘缓存
3. 内存优化

运行方式:
python demo_data_loader.py
"""

import time
import os
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

from src.utils.data_loader import DataLoader, load_stock_data
from src.utils.logger import setup_logger

# 加载环境变量
load_dotenv()

# 设置日志记录器
logger = setup_logger("demo", level="INFO", log_to_console=True)


def main():
    """演示数据加载器的主函数"""
    # 定义测试参数
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    logger.info(f"演示数据加载器 - 加载{len(tickers)}只股票的数据")
    logger.info(f"时间范围: {start_date} 至 {end_date}")
    
    # 创建数据加载器的实例
    logger.info("创建数据加载器 (8线程, 启用磁盘缓存和内存优化)")
    data_loader = DataLoader(max_workers=8, disk_cache_enabled=True, memory_optimization=True)
    
    # 测试1: 首次加载数据 (无缓存)
    logger.info("\n=== 测试1: 首次加载数据 (无缓存) ===")
    start_time = time.time()
    results = data_loader.load_stock_data(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        include_prices=True,
        include_metrics=True,
        include_news=True,
        include_insider=True
    )
    first_load_time = time.time() - start_time
    logger.info(f"首次加载完成，耗时: {first_load_time:.2f}秒")
    
    # 打印数据摘要
    print_results_summary(results)
    
    # 测试2: 第二次加载数据 (使用缓存)
    logger.info("\n=== 测试2: 第二次加载数据 (使用缓存) ===")
    start_time = time.time()
    cached_results = data_loader.load_stock_data(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        include_prices=True,
        include_metrics=True,
        include_news=True,
        include_insider=True
    )
    cached_load_time = time.time() - start_time
    logger.info(f"第二次加载完成，耗时: {cached_load_time:.2f}秒")
    logger.info(f"缓存加速比: {first_load_time / cached_load_time:.2f}x")
    
    # 测试3: 加载单只股票并检查内存使用
    logger.info("\n=== 测试3: 内存优化对比 ===")
    
    # 创建不使用内存优化的加载器
    no_opt_loader = DataLoader(memory_optimization=False)
    
    # 使用优化的加载器
    start_time = time.time()
    opt_result = data_loader.load_stock_data(
        tickers=["AAPL"],
        start_date=start_date,
        end_date=end_date,
        include_prices=True,
        include_metrics=True
    )
    opt_time = time.time() - start_time
    
    # 使用未优化的加载器
    start_time = time.time()
    no_opt_result = no_opt_loader.load_stock_data(
        tickers=["AAPL"],
        start_date=start_date,
        end_date=end_date,
        include_prices=True,
        include_metrics=True
    )
    no_opt_time = time.time() - start_time
    
    # 计算内存使用情况
    opt_memory = opt_result["AAPL"].memory_usage(deep=True).sum() / (1024 * 1024)  # MB
    no_opt_memory = no_opt_result["AAPL"].memory_usage(deep=True).sum() / (1024 * 1024)  # MB
    
    logger.info(f"优化后的内存使用: {opt_memory:.2f} MB, 加载时间: {opt_time:.2f}秒")
    logger.info(f"未优化的内存使用: {no_opt_memory:.2f} MB, 加载时间: {no_opt_time:.2f}秒")
    logger.info(f"内存节省: {(1 - opt_memory / no_opt_memory) * 100:.2f}%")
    
    # 测试4: 使用便捷函数加载数据
    logger.info("\n=== 测试4: 使用便捷函数加载数据 ===")
    start_time = time.time()
    easy_results = load_stock_data(
        tickers="NVDA",
        start_date=start_date,
        end_date=end_date
    )
    easy_load_time = time.time() - start_time
    logger.info(f"便捷函数加载完成，耗时: {easy_load_time:.2f}秒")
    
    logger.info("\n演示完成!")


def print_results_summary(results):
    """打印数据加载结果摘要"""
    logger.info("=== 数据加载结果摘要 ===")
    
    for ticker, df in results.items():
        # 获取基本信息
        rows = len(df)
        cols = len(df.columns)
        memory = df.memory_usage(deep=True).sum() / (1024 * 1024)  # MB
        
        logger.info(f"{ticker}: {rows}行 x {cols}列, 内存: {memory:.2f} MB")
        
        # 显示列名
        logger.info(f"  列: {', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}")
        
        # 显示前两行数据
        if not df.empty:
            with pd.option_context('display.max_columns', 10):
                logger.info(f"  前两行数据:\n{df.head(2).to_string()}")
        
        logger.info("")


if __name__ == "__main__":
    main() 
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
单元测试运行脚本
可以运行指定的测试或全部测试
"""

import os
import sys
import unittest
import argparse
import logging


def setup_logging():
    """设置日志记录"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


def discover_tests(test_dir=None, pattern='test_*.py'):
    """
    发现测试文件
    
    参数:
        test_dir: 测试目录，默认为tests
        pattern: 测试文件匹配模式
        
    返回:
        测试套件
    """
    if test_dir is None:
        test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    
    # 确保测试目录存在
    if not os.path.exists(test_dir):
        logging.error(f"测试目录不存在: {test_dir}")
        sys.exit(1)
    
    # 发现测试
    return unittest.defaultTestLoader.discover(test_dir, pattern=pattern)


def run_specific_test(test_name):
    """
    运行指定的测试
    
    参数:
        test_name: 测试模块名称，如 test_data_loader
        
    返回:
        测试结果
    """
    test_dir = os.path.join(os.path.dirname(__file__), 'tests')
    test_module = f"{test_name}"
    
    # 检查测试文件是否存在
    test_file = os.path.join(test_dir, f"{test_module}.py")
    if not os.path.exists(test_file):
        logging.error(f"测试文件不存在: {test_file}")
        sys.exit(1)
    
    # 加载测试
    return unittest.defaultTestLoader.loadTestsFromName(f"tests.{test_module}")


def main():
    """主函数"""
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='运行AI对冲基金项目的单元测试')
    parser.add_argument('-t', '--test', help='要运行的特定测试模块，例如 test_data_loader')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细输出')
    parser.add_argument('-d', '--directory', help='指定测试目录')
    args = parser.parse_args()
    
    # 设置日志
    setup_logging()
    
    # 设置测试运行器
    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    
    if args.test:
        # 运行特定测试
        logging.info(f"正在运行测试模块: {args.test}")
        suite = run_specific_test(args.test)
    else:
        # 运行所有测试
        logging.info("正在运行所有测试")
        suite = discover_tests(args.directory)
    
    # 运行测试
    result = runner.run(suite)
    
    # 输出测试结果摘要
    logging.info(f"测试运行完成，总计: {result.testsRun}, 失败: {len(result.failures)}, 错误: {len(result.errors)}")
    
    # 如果有失败或错误，返回非零退出码
    if result.failures or result.errors:
        sys.exit(1)


if __name__ == '__main__':
    main() 
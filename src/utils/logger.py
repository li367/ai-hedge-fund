import logging
import os
from datetime import datetime

def setup_logger():
    """设置日志配置"""
    # 创建 logs 目录
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 设置日志格式
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 生成日志文件名
    log_file = f"logs/trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # 配置日志处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    console_handler = logging.StreamHandler()
    
    # 设置格式
    formatter = logging.Formatter(log_format, date_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 配置日志级别
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )
    
    # 设置第三方库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('ccxt').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    
    logging.info('日志系统初始化完成')

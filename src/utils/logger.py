import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# 日志级别映射
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

# 默认日志格式
DEFAULT_LOG_FORMAT = "[%(asctime)s][%(name)s][%(levelname)s] %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 设置日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")


def setup_logger(name, level="info", log_to_console=True, log_to_file=True, 
                file_name=None, max_bytes=10*1024*1024, backup_count=5):
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别 ('debug', 'info', 'warning', 'error', 'critical')
        log_to_console: 是否输出到控制台
        log_to_file: 是否输出到文件
        file_name: 日志文件名，默认为{name}.log
        max_bytes: 单个日志文件最大大小
        backup_count: 备份日志文件数量
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 获取日志级别
    log_level = LOG_LEVELS.get(level.lower(), logging.INFO)
    
    # 创建记录器
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 防止重复添加处理器
    if logger.handlers:
        return logger
    
    # 设置日志格式
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
    
    # 添加控制台处理器
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)
    
    # 添加文件处理器
    if log_to_file:
        # 确保日志目录存在
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        
        # 设置日志文件
        if file_name is None:
            file_name = f"{name}.log"
        log_file = os.path.join(LOG_DIR, file_name)
        
        # 创建文件处理器
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)
    
    return logger


# 创建默认日志记录器
default_logger = setup_logger("ai-hedge-fund")


def get_logger(name=None):
    """
    获取指定名称的日志记录器，如果没有指定则返回默认记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        logging.Logger: 日志记录器
    """
    if name is None:
        return default_logger
    return setup_logger(name) 
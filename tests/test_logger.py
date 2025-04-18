import os
import unittest
import logging
from unittest.mock import patch, MagicMock
import tempfile
import sys
from logging.handlers import RotatingFileHandler

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.logger import setup_logger, get_logger


class TestLogger(unittest.TestCase):
    """测试日志模块功能"""
    
    def setUp(self):
        """准备测试环境"""
        # 创建临时日志目录
        self.temp_dir = tempfile.TemporaryDirectory()
        # 备份原始日志配置
        self.original_log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
        self.original_handlers = logging.getLogger().handlers.copy()
        self.original_level = logging.getLogger().level
        
        # 清空现有处理器
        logging.getLogger().handlers = []

    def tearDown(self):
        """清理测试环境"""
        # 恢复原始日志配置
        logging.getLogger().handlers = self.original_handlers
        logging.getLogger().setLevel(self.original_level)
        
        # 关闭所有日志处理器，防止文件被锁定
        import logging as _logging
        _logging.shutdown()
        
        # 清理临时文件
        self.temp_dir.cleanup()

    def test_setup_logger_file_creation(self):
        """测试日志设置创建文件"""
        # 使用临时目录作为日志目录
        with patch('src.utils.logger.LOG_DIR', self.temp_dir.name):
            # 设置日志器
            logger = setup_logger('test_logger')
            
            # 验证日志对象
            self.assertIsNotNone(logger)
            self.assertEqual(logger.name, 'test_logger')
            
            # 验证文件处理器存在
            has_file_handler = False
            for handler in logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    has_file_handler = True
                    # 验证日志文件路径
                    self.assertTrue(handler.baseFilename.startswith(self.temp_dir.name))
                    
            self.assertTrue(has_file_handler, "应创建文件处理器")
            
            # 写入日志消息
            test_message = "测试日志消息"
            logger.info(test_message)
            
            # 验证日志文件内容
            log_files = [f for f in os.listdir(self.temp_dir.name) if f.endswith('.log')]
            self.assertGreater(len(log_files), 0, "应创建日志文件")
            
            # 检查日志内容
            with open(os.path.join(self.temp_dir.name, log_files[0]), 'r', encoding='utf-8') as f:
                log_content = f.read()
                self.assertIn(test_message, log_content)
    
    def test_get_logger(self):
        """测试获取日志记录器"""
        # 获取默认日志记录器
        default_logger = get_logger()
        self.assertIsNotNone(default_logger)
        self.assertEqual(default_logger.name, "ai-hedge-fund")
        
        # 获取指定名称的日志记录器
        custom_logger = get_logger("custom")
        self.assertIsNotNone(custom_logger)
        self.assertEqual(custom_logger.name, "custom")
        
        # 验证两个记录器不同
        self.assertNotEqual(default_logger, custom_logger)

    def test_logger_levels(self):
        """测试日志级别设置"""
        # 测试不同日志级别
        debug_logger = setup_logger("debug_test", level="debug")
        self.assertEqual(debug_logger.level, logging.DEBUG)
        
        info_logger = setup_logger("info_test", level="info")
        self.assertEqual(info_logger.level, logging.INFO)
        
        warning_logger = setup_logger("warning_test", level="warning")
        self.assertEqual(warning_logger.level, logging.WARNING)
        
        error_logger = setup_logger("error_test", level="error")
        self.assertEqual(error_logger.level, logging.ERROR)
        
        critical_logger = setup_logger("critical_test", level="critical")
        self.assertEqual(critical_logger.level, logging.CRITICAL)
        
        # 测试无效日志级别默认为INFO
        invalid_logger = setup_logger("invalid_test", level="invalid")
        self.assertEqual(invalid_logger.level, logging.INFO)
    
    def test_console_only_logger(self):
        """测试仅控制台输出的日志记录器"""
        logger = setup_logger("console_only", log_to_file=False)
        
        # 验证没有文件处理器
        has_file_handler = False
        for handler in logger.handlers:
            if isinstance(handler, RotatingFileHandler):
                has_file_handler = True
                break
        
        self.assertFalse(has_file_handler, "不应有文件处理器")
        
        # 验证有控制台处理器
        has_console_handler = False
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                has_console_handler = True
                break
        
        self.assertTrue(has_console_handler, "应有控制台处理器")
    
    def test_file_only_logger(self):
        """测试仅文件输出的日志记录器"""
        with patch('src.utils.logger.LOG_DIR', self.temp_dir.name):
            logger = setup_logger("file_only", log_to_console=False)
            
            # 验证有文件处理器
            has_file_handler = False
            for handler in logger.handlers:
                if isinstance(handler, RotatingFileHandler):
                    has_file_handler = True
                    break
            
            self.assertTrue(has_file_handler, "应有文件处理器")
            
            # 验证没有控制台处理器
            has_console_handler = False
            for handler in logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
                    has_console_handler = True
                    break
            
            self.assertFalse(has_console_handler, "不应有控制台处理器")

if __name__ == '__main__':
    unittest.main() 
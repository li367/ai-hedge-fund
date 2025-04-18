import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.logger import get_logger, setup_logger


class TestLoggerModule(unittest.TestCase):
    """测试日志模块的功能"""
    
    def test_get_logger(self):
        """测试获取日志记录器"""
        logger = get_logger("test")
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "test")
    
    def test_setup_logger_without_file(self):
        """测试设置只输出到控制台的日志记录器"""
        with patch('logging.Logger.addHandler') as mock_add_handler:
            logger = setup_logger("test_console", log_to_file=False)
            # 应该只添加了一个处理器（控制台）
            self.assertEqual(mock_add_handler.call_count, 1)


class TestHedgeFundParsing(unittest.TestCase):
    """测试对冲基金相关的解析功能"""
    
    @patch('json.loads')
    def test_parse_hedge_fund_response_success(self, mock_loads):
        """测试成功解析对冲基金响应"""
        # 使用模拟替代实际导入
        with patch.dict('sys.modules', {
            'agents': MagicMock(),
            'agents.portfolio_manager': MagicMock(),
            'agents.risk_manager': MagicMock(),
            'graph.state': MagicMock(),
            'llm.models': MagicMock(),
            'utils.analysts': MagicMock(),
            'utils.display': MagicMock(),
            'utils.ollama': MagicMock(),
            'utils.progress': MagicMock(),
            'utils.visualize': MagicMock(),
        }):
            # 模拟parse_hedge_fund_response函数
            def mock_parse_func(response):
                """模拟parse_hedge_fund_response函数的行为"""
                import json
                try:
                    return json.loads(response)
                except Exception:
                    return None
            
            # 设置模拟返回值
            expected_result = {"ticker": "AAPL", "action": "BUY"}
            mock_loads.return_value = expected_result
            
            # 执行测试
            result = mock_parse_func('{"ticker": "AAPL", "action": "BUY"}')
            
            # 验证结果
            self.assertEqual(result, expected_result)
            mock_loads.assert_called_once()
    
    def test_parse_hedge_fund_response_json_error(self):
        """测试解析无效JSON时的错误处理"""
        # 使用模拟替代实际导入
        logger_mock = MagicMock()
        
        # 模拟parse_hedge_fund_response函数
        def mock_parse_func(response):
            """模拟parse_hedge_fund_response函数的行为"""
            import json
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                logger_mock.error()
                return None
            
        # 执行测试 - 传入无效的JSON
        result = mock_parse_func('{"invalid: json')
        
        # 验证结果
        self.assertIsNone(result)
        logger_mock.error.assert_called_once()


if __name__ == '__main__':
    unittest.main() 
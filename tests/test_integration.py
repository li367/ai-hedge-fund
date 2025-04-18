import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入集成测试所需组件
from src.graph.workflow import build_workflow
from src.graph.state import AgentState
from src.backtester import Backtester

# 导入新的数据加载器
from src.utils.data_loader import DataLoader, load_stock_data

# 模拟data_loader模块
sys.modules['src.utils.data_loader'] = MagicMock()
sys.modules['src.utils.data_loader'].load_stock_data = MagicMock()


class TestIntegrationWorkflow(unittest.TestCase):
    """测试代理协作的集成工作流程"""
    
    def setUp(self):
        """准备测试环境和模拟数据"""
        # 模拟语言模型响应
        self.llm_patcher = patch('langchain.chat_models.ChatOpenAI')
        self.mock_llm_class = self.llm_patcher.start()
        
        # 创建一个模拟的LLM实例
        self.mock_llm = MagicMock()
        self.mock_llm.invoke.return_value = MagicMock(content=
            '{"signal": "BULLISH", "confidence": 80, "reasoning": "测试推理"}'
        )
        self.mock_llm_class.return_value = self.mock_llm
        
        # 模拟数据加载器
        self.data_loader_patcher = patch('src.utils.data_loader.load_stock_data')
        self.mock_load_data = self.data_loader_patcher.start()
        self.mock_load_data.return_value = {
            'AAPL': MagicMock(to_dict=lambda: {
                'Open': [150.0, 151.0, 152.0],
                'High': [155.0, 156.0, 157.0],
                'Low': [148.0, 149.0, 150.0],
                'Close': [153.0, 154.0, 155.0],
                'Volume': [1000000, 1100000, 1200000]
            }),
            'MSFT': MagicMock(to_dict=lambda: {
                'Open': [250.0, 251.0, 252.0],
                'High': [255.0, 256.0, 257.0],
                'Low': [248.0, 249.0, 250.0],
                'Close': [253.0, 254.0, 255.0],
                'Volume': [2000000, 2100000, 2200000]
            })
        }

    def tearDown(self):
        """清理测试环境"""
        self.llm_patcher.stop()
        self.data_loader_patcher.stop()

    @patch('langchain.callbacks.manager.CallbackManagerForRetrieverRun')
    @patch('src.agents.portfolio_manager.get_llm')
    @patch('src.agents.risk_manager.get_llm')
    @patch('src.agents.warren_buffett.get_llm')
    @patch('src.agents.technicals.get_llm')
    def test_workflow_integration(self, mock_tech, mock_wb, mock_rm, mock_pm, mock_callback):
        """测试完整工作流程集成"""
        # 为各代理模拟LLM响应
        mock_tech.return_value = MagicMock(invoke=MagicMock(return_value=
            '{"signal": "BULLISH", "confidence": 70, "reasoning": "技术指标向好"}'
        ))
        mock_wb.return_value = MagicMock(invoke=MagicMock(return_value=
            '{"signal": "BULLISH", "confidence": 85, "reasoning": "长期价值突出"}'
        ))
        mock_rm.return_value = MagicMock(invoke=MagicMock(return_value=
            '{"signal": "BULLISH", "confidence": 75, "risk_level": "LOW", "reasoning": "风险可控"}'
        ))
        mock_pm.return_value = MagicMock(invoke=MagicMock(return_value=
            '{"AAPL": {"action": "BUY", "quantity": 10, "confidence": 80}, "MSFT": {"action": "HOLD", "quantity": 0, "confidence": 60}}'
        ))
        
        # 构建工作流
        workflow = build_workflow(show_reasoning=False)
        self.assertIsNotNone(workflow, "工作流构建失败")
        
        # 创建初始状态
        state = AgentState(
            messages=[],
            data={
                "tickers": ["AAPL", "MSFT"],
                "portfolio": {
                    "cash": 100000.0,
                    "positions": {
                        "AAPL": {"long": 0, "short": 0, "long_cost_basis": 0.0, "short_cost_basis": 0.0},
                        "MSFT": {"long": 0, "short": 0, "long_cost_basis": 0.0, "short_cost_basis": 0.0}
                    },
                    "realized_gains": {
                        "AAPL": {"long": 0.0, "short": 0.0},
                        "MSFT": {"long": 0.0, "short": 0.0}
                    }
                },
                "start_date": "2023-01-01",
                "end_date": "2023-01-03",
                "analyst_signals": {}
            },
            metadata={
                "show_reasoning": False,
                "model_name": "gpt-4-o",
                "model_provider": "OpenAI"
            }
        )
        
        # 执行工作流
        try:
            final_state = workflow.invoke(state)
            
            # 验证最终状态包含所有代理的信号
            self.assertIn("analyst_signals", final_state.data)
            self.assertIn("warren_buffett_agent", final_state.data["analyst_signals"])
            self.assertIn("technicals_agent", final_state.data["analyst_signals"])
            self.assertIn("risk_management_agent", final_state.data["analyst_signals"])
            
            # 验证投资组合变化
            self.assertGreater(len(final_state.messages), 0)
            
        except Exception as e:
            self.fail(f"工作流执行失败: {str(e)}")


class TestBacktestIntegration(unittest.TestCase):
    """测试回测系统集成"""
    
    def setUp(self):
        """准备回测测试环境"""
        # 模拟数据加载
        self.data_loader_patcher = patch('src.utils.data_loader.load_stock_data')
        self.mock_load_data = self.data_loader_patcher.start()
        
        # 提供模拟的股票数据
        self.mock_data = {
            'AAPL': MagicMock(to_dict=lambda: {
                'Open': [150.0, 151.0, 152.0],
                'High': [155.0, 156.0, 157.0],
                'Low': [148.0, 149.0, 150.0],
                'Close': [153.0, 154.0, 155.0],
                'Volume': [1000000, 1100000, 1200000]
            }),
            'MSFT': MagicMock(to_dict=lambda: {
                'Open': [250.0, 251.0, 252.0],
                'High': [255.0, 256.0, 257.0],
                'Low': [248.0, 249.0, 250.0],
                'Close': [253.0, 254.0, 255.0],
                'Volume': [2000000, 2100000, 2200000]
            })
        }
        self.mock_load_data.return_value = self.mock_data
        
        # 模拟工作流
        self.workflow_patcher = patch('src.graph.workflow.build_workflow')
        self.mock_build_workflow = self.workflow_patcher.start()
        
        # 创建一个模拟的工作流对象
        mock_workflow = MagicMock()
        
        # 模拟工作流执行结果
        def mock_invoke(state):
            new_state = AgentState(
                messages=state.messages + [MagicMock(content="执行了交易决策")],
                data={
                    **state.data,
                    "analyst_signals": {
                        "warren_buffett_agent": {
                            "AAPL": {"signal": "BULLISH", "confidence": 85}
                        },
                        "portfolio_management_agent": {
                            "actions": {
                                "AAPL": {"action": "BUY", "quantity": 10}
                            }
                        }
                    }
                },
                metadata=state.metadata
            )
            return new_state
        
        mock_workflow.invoke = mock_invoke
        self.mock_build_workflow.return_value = mock_workflow

    def tearDown(self):
        """清理测试环境"""
        self.data_loader_patcher.stop()
        self.workflow_patcher.stop()

    def test_backtester_integration(self):
        """测试回测器的端到端集成"""
        # 实例化回测器
        backtester = Backtester(
            tickers=['AAPL', 'MSFT'],
            start_date='2023-01-01',
            end_date='2023-01-03',
            initial_capital=100000,
            model_name='gpt-4-o',
            model_provider='OpenAI',
            show_reasoning=False
        )
        
        # 运行回测
        results = backtester.run_backtest()
        
        # 验证回测结果
        self.assertIsNotNone(results, "回测结果不应为空")
        self.assertIn("summary", results, "回测结果应包含摘要")
        self.assertIn("daily_results", results, "回测结果应包含每日结果")
        
        # 验证结果格式
        daily_results = results["daily_results"]
        self.assertGreater(len(daily_results), 0, "每日结果应至少包含一天的数据")
        
        # 验证第一天的结果包含必要字段
        first_day = daily_results[0]
        self.assertIn("date", first_day)
        self.assertIn("portfolio_value", first_day)
        self.assertIn("cash", first_day)


if __name__ == '__main__':
    unittest.main() 
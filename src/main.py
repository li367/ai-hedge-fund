import os
import asyncio
from dotenv import load_dotenv
from utils.logger import setup_logger
import logging

# 导入加密货币交易所和策略
from crypto.exchanges.okx import OKXExchange
from crypto.strategies.llm_strategy import LLMStrategy
from crypto.risk_manager import RiskManager

async def run_strategy():
    # 获取环境变量
    api_key = os.getenv('OKX_API_KEY')
    secret_key = os.getenv('OKX_SECRET_KEY')
    passphrase = os.getenv('OKX_PASSPHRASE')
    
    # 初始化交易所变量
    exchange = None
    
    try:
        if not all([api_key, secret_key, passphrase]):
            logging.error("缺少OKX API配置，请在.env文件中设置OKX_API_KEY, OKX_SECRET_KEY和OKX_PASSPHRASE")
            return

        # 检查是否有LLM API密钥
        openai_key = os.getenv('OPENAI_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        tongyi_key = os.getenv('TONGYI_API_KEY')
        llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        llm_model = os.getenv('LLM_MODEL', 'gpt-4')
        
        # 检查是否使用Groq（该功能可能未安装）
        if llm_provider.lower() == 'groq':
            try:
                # 检查是否安装了langchain_groq
                import importlib.util
                groq_spec = importlib.util.find_spec('langchain_groq')
                if groq_spec is None:
                    logging.warning("检测到Groq提供商，但langchain_groq未安装。切换到通义模型。")
                    llm_provider = 'tongyi'
                    llm_model = 'qwen-turbo'
            except ImportError:
                logging.warning("检测到Groq提供商，但langchain_groq未安装。切换到通义模型。")
                llm_provider = 'tongyi'
                llm_model = 'qwen-turbo'
        
        logging.info(f"使用LLM提供商: {llm_provider}, 模型: {llm_model}")
        
        if (llm_provider == 'openai' and (not openai_key or openai_key == 'your-openai-api-key')) or \
           (llm_provider == 'anthropic' and (not anthropic_key or anthropic_key == 'your-anthropic-api-key')) or \
           (llm_provider == 'tongyi' and (not tongyi_key or tongyi_key == 'your-tongyi-api-key')):
            logging.warning(f"注意：缺少{llm_provider.upper()} API密钥，系统将使用模拟数据运行")
        
        # 特别处理通义模型
        if llm_provider == 'tongyi':
            logging.info(f"通义API配置检查：API密钥长度={len(tongyi_key) if tongyi_key else 0}")
            if tongyi_key and tongyi_key != 'your-tongyi-api-key':
                logging.info("通义API密钥已配置")
                # 测试通义API连接
                try:
                    import requests
                    test_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
                    test_payload = {
                        "model": llm_model,
                        "messages": [{"role": "user", "content": "测试连接"}]
                    }
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {tongyi_key}"
                    }
                    logging.info("正在测试通义API连接...")
                    response = requests.post(test_url, json=test_payload, headers=headers)
                    if response.status_code == 200:
                        logging.info("通义API连接测试成功!")
                    else:
                        logging.warning(f"通义API连接测试失败: {response.status_code} - {response.text}")
                except Exception as e:
                    logging.error(f"通义API连接测试出错: {str(e)}")
        
        # 交易模式 - 模拟或实盘
        trading_mode = os.getenv('TRADING_MODE', 'simulation').lower()
        is_simulation = trading_mode != 'live'
        
        if is_simulation:
            logging.warning("当前为模拟交易模式，不会执行实际交易")
        else:
            logging.warning("⚠️ 当前为实盘交易模式，将执行实际交易！")
        
        # 初始化交易所接口
        exchange = OKXExchange(
            api_key=api_key,
            secret_key=secret_key,
            passphrase=passphrase
        )
        
        # 设置市场类型为永续合约
        await exchange.switch_market_type('swap')
        
        # 初始化风险管理器
        risk_manager = RiskManager(
            exchange=exchange,
            max_position_size=float(os.getenv('MAX_POSITION_SIZE', 0.1)),
            max_drawdown=float(os.getenv('MAX_DRAWDOWN', 0.2)),
            stop_loss_pct=float(os.getenv('STOP_LOSS_PERCENTAGE', 0.05)) / 100,
            take_profit_pct=float(os.getenv('TAKE_PROFIT_PERCENTAGE', 0.1)) / 100,
            max_leverage=float(os.getenv('MAX_LEVERAGE', 3.0)),
            risk_per_trade=float(os.getenv('RISK_PER_TRADE', 0.02))
        )
        
        # 获取交易对
        symbols = await get_trading_symbols(exchange)
        
        if not symbols:
            logging.error("未找到有效的交易对，请检查配置")
            return
        
        logging.info(f"将分析以下交易对: {', '.join(symbols)}")
        
        # 创建策略列表
        strategies = []
        
        # 初始化每个交易对的策略
        for symbol in symbols:
            logging.info(f"初始化交易对 {symbol} 的LLM策略: 提供商={llm_provider}, 模型={llm_model}")
            
            # 读取缓存配置
            use_cache = os.getenv('USE_LLM_CACHE', 'true').lower() == 'true'
            cache_expire_minutes = int(os.getenv('CACHE_EXPIRE_MINUTES', '5'))
            logging.info(f"LLM缓存设置: 启用={use_cache}, 过期时间={cache_expire_minutes}分钟")
            
            strategy = LLMStrategy(
                exchange=exchange,
                risk_manager=risk_manager,
                symbol=symbol,
                model_name=llm_model,
                model_provider=llm_provider,
                timeframe=os.getenv('TIMEFRAME', '15m'),
                sentiment_threshold=float(os.getenv('SENTIMENT_THRESHOLD', 0.6)),
                use_cache=use_cache,
                cache_expire_minutes=cache_expire_minutes
            )
            
            # 如果是模拟模式，修改execute_trade方法以避免实际下单
            if is_simulation:
                original_execute_trade = strategy.execute_trade
                
                async def simulation_execute_trade(analysis, strategy_instance=strategy):
                    # 获取当前持仓
                    position = await exchange.get_position(strategy_instance.symbol)
                    current_position_size = float(position['size']) if position else 0
                    
                    # 获取当前价格
                    ticker = await exchange.get_ticker(strategy_instance.symbol)
                    current_price = ticker['last']
                    
                    # 风险检查
                    risk_check = await risk_manager.check_trade(
                        strategy_instance.symbol,
                        current_price,
                        current_position_size,
                        0  # 当前回撤
                    )
                    
                    if not risk_check['can_trade']:
                        logging.info(f"[{strategy_instance.symbol}] 风险检查未通过，不执行交易")
                        return
                        
                    # 模拟交易
                    if analysis.suggested_action == "BUY" and analysis.sentiment > 0:
                        amount = risk_manager.calculate_position_size(
                            strategy_instance.symbol,
                            current_price,
                            'long'
                        )
                        logging.info(f"[模拟交易] 买入 {strategy_instance.symbol}: 数量={amount}, 价格={current_price}")
                        
                    elif analysis.suggested_action == "SELL" and analysis.sentiment < 0:
                        amount = risk_manager.calculate_position_size(
                            strategy_instance.symbol,
                            current_price,
                            'short'
                        )
                        logging.info(f"[模拟交易] 卖出 {strategy_instance.symbol}: 数量={amount}, 价格={current_price}")
                    
                    else:
                        logging.info(f"[模拟交易] {strategy_instance.symbol} 保持观望，不执行交易")
                        
                # 替换为模拟交易函数
                strategy.execute_trade = simulation_execute_trade
            
            strategies.append(strategy)
        
        # 并行运行所有策略
        await run_multiple_strategies(strategies)
        
    except Exception as e:
        logging.error(f"运行策略时出错: {str(e)}")
    finally:
        # 确保交易所资源被正确关闭
        if exchange:
            logging.info("正在关闭交易所连接...")
            try:
                await exchange.close()
                logging.info("交易所连接已关闭")
            except Exception as close_error:
                logging.error(f"关闭交易所连接时出错: {str(close_error)}")

async def run_multiple_strategies(strategies):
    """并行运行多个交易策略"""
    tasks = []
    
    for strategy in strategies:
        # 为每个策略创建一个任务
        task = asyncio.create_task(run_strategy_with_error_handling(strategy))
        tasks.append(task)
    
    # 等待所有策略完成或被取消
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logging.info("正在取消所有策略任务...")
        # 如果任务被取消，确保所有子任务也被取消
        for task in tasks:
            if not task.done():
                task.cancel()
        # 等待所有任务被取消
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        # 重新抛出异常以通知上层函数
        raise

async def run_strategy_with_error_handling(strategy):
    """运行单个策略并处理可能的错误"""
    try:
        logging.info(f"开始分析交易对: {strategy.symbol}")
        await strategy.run()
    except Exception as e:
        logging.error(f"运行交易对 {strategy.symbol} 策略时出错: {str(e)}")

async def get_trading_symbols(exchange):
    """获取要交易的交易对列表"""
    symbols = []
    
    # 方法1：检查环境变量中是否指定了交易对列表
    symbols_str = os.getenv('TRADING_SYMBOLS')
    if symbols_str:
        # 从环境变量中解析交易对列表
        symbols = [s.strip() for s in symbols_str.split(',')]
        logging.info(f"从环境变量加载交易对: {symbols}")
        return symbols
    
    # 方法2：从交易所获取所有可用的永续合约交易对
    try:
        markets = await exchange.get_markets()
        for market in markets:
            if market['type'] == 'swap' and market['quote'] == 'USDT':
                symbols.append(market['symbol'])
        
        # 如果找到了交易对，返回前5个用于测试
        if symbols:
            symbols = symbols[:5]  # 限制交易对数量
            logging.info(f"从交易所获取到的交易对: {symbols}")
            return symbols
        
    except Exception as e:
        logging.error(f"获取交易对时出错: {str(e)}")
    
    # 如果上述方法都失败，返回默认交易对列表
    default_symbols = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP']
    logging.warning(f"使用默认交易对列表: {default_symbols}")
    return default_symbols

def main():
    # 加载环境变量
    load_dotenv()
    
    # 设置日志
    setup_logger()
    
    try:
        # 运行异步主程序
        asyncio.run(run_strategy())
    except KeyboardInterrupt:
        logging.info("检测到用户中断，正在清理资源...")
        cleanup_resources()
    except Exception as e:
        logging.error(f"程序运行时出错: {str(e)}")
        cleanup_resources()

def cleanup_resources():
    """清理资源"""
    try:
        # 关闭所有异步任务
        for task in asyncio.all_tasks():
            task.cancel()
        
        # 关闭事件循环
        loop = asyncio.get_event_loop()
        loop.stop()
        loop.close()
    except Exception as e:
        logging.error(f"清理资源时出错: {str(e)}")

if __name__ == "__main__":
    main()

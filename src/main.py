from dotenv import load_dotenv
from data.fetcher import DataFetcher
from models.trader import AITrader
from utils.logger import setup_logger

def main():
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    logger = setup_logger()
    
    # Initialize components
    data_fetcher = DataFetcher()
    trader = AITrader()
    
    # Main trading loop
    try:
        logger.info("Starting AI Hedge Fund trading system...")
        # Add your trading logic here
        pass
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")

if __name__ == "__main__":
    main()
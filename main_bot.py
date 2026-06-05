import asyncio
import os
import time
import ccxt.async_support as ccxt
# allow minimal octobot_commons imports
os.environ["USE_MINIMAL_LIBS"] = "true"

import octobot_commons.symbols as symbols
import triangular_arbitrage.detector as detector

# Global State
BOT_STATE = {
    "is_running": False,
    "config": {
        "api_key": "gdiOPa2WbPib1V8aaRZEXtuuEYT461oafe6ITj2cj9aTgEUzFoN6Owe0sxI4kU4P",
        "secret_key": "dmV2883fuwZgLxPzX1qQJs2iPWpfgF3v32xbqEW8tM887JniNEmJgROLbGyjKYLE",
        "starting_amount": 100.0,
        "min_profit_threshold": 1.005
    },
    "stats": {
        "total_profit_usdt": 0.0,
        "trades_executed": 0,
        "last_scan_time": None,
        "start_time": None,
        "ping_ms": 0,
        "active_pairs": 0
    },
    "trades_history": []
}

async def run_bot_loop():
    print("Initializing Binance Testnet...")
    exchange = ccxt.binance({
        'apiKey': BOT_STATE["config"]["api_key"],
        'secret': BOT_STATE["config"]["secret_key"],
        'enableRateLimit': True,
    })
    exchange.set_sandbox_mode(True)
    
    try:
        await exchange.load_markets()
        BOT_STATE["stats"]["active_pairs"] = len(exchange.markets)
        BOT_STATE["stats"]["start_time"] = time.time()
    except Exception as e:
        print(f"Failed to load markets: {e}")
        BOT_STATE["is_running"] = False
        await exchange.close()
        return

    try:
        while BOT_STATE["is_running"]:
            try:
                loop_start = time.time()
                print("Scanning for opportunities...")
                BOT_STATE["stats"]["last_scan_time"] = time.time()
                
                best_opportunities, best_profit = await detector.run_detection_loop(exchange, max_cycle=4)
                BOT_STATE["stats"]["ping_ms"] = int((time.time() - loop_start) * 1000)
                
                if best_opportunities is not None:
                    total_profit_percentage = round((best_profit - 1) * 100, 5)
                    print(f"New {total_profit_percentage}% opportunity detected.")
                    
                    if best_profit > BOT_STATE["config"]["min_profit_threshold"]:
                        print("Profit threshold met. Executing trades...")
                        starting_amount = BOT_STATE["config"]["starting_amount"]
                        success, final_amount, order_ids = await detector.execute_arbitrage_cycle(exchange, best_opportunities, starting_amount)
                        
                        if success:
                            profit_usdt = final_amount - starting_amount
                            BOT_STATE["stats"]["total_profit_usdt"] += profit_usdt
                            BOT_STATE["stats"]["trades_executed"] += 1
                            
                            path_str = " -> ".join([opp['symbol'] for opp in best_opportunities])
                            
                            trade_record = {
                                "id": len(BOT_STATE["trades_history"]) + 1,
                                "timestamp": time.time(),
                                "path": path_str,
                                "profit_percentage": total_profit_percentage,
                                "profit_usdt": profit_usdt,
                                "order_ids": order_ids
                            }
                            BOT_STATE["trades_history"].insert(0, trade_record)
                            # Keep only last 100 trades to save memory
                            if len(BOT_STATE["trades_history"]) > 100:
                                BOT_STATE["trades_history"].pop()
                    else:
                        print(f"Profit ({total_profit_percentage}%) too low. Skipping.")
                else:
                    print("No opportunity detected")
                    
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Error during iteration: {e}")
                await asyncio.sleep(5)
    except Exception as e:
        print(f"Fatal error in main loop: {e}")
    finally:
        BOT_STATE["is_running"] = False
        await exchange.close()

if __name__ == "__main__":
    print("Run using: uvicorn server:app --reload")

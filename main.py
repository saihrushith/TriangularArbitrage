import asyncio
import os
import ccxt.async_support as ccxt
# allow minimal octobot_commons imports
os.environ["USE_MINIMAL_LIBS"] = "true"

import octobot_commons.symbols as symbols
import triangular_arbitrage.detector as detector

API_KEY = "gdiOPa2WbPib1V8aaRZEXtuuEYT461oafe6ITj2cj9aTgEUzFoN6Owe0sxI4kU4P"
SECRET_KEY = "dmV2883fuwZgLxPzX1qQJs2iPWpfgF3v32xbqEW8tM887JniNEmJgROLbGyjKYLE"
STARTING_AMOUNT = 100.0

async def main_loop():
    print("Initializing Binance Testnet...")
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': SECRET_KEY,
        'enableRateLimit': True,
    })
    exchange.set_sandbox_mode(True)
    
    # Load markets once at startup
    await exchange.load_markets()
    
    try:
        while True:
            print("Scanning for opportunities...")
            best_opportunities, best_profit = await detector.run_detection_loop(exchange, max_cycle=3)
            
            if best_opportunities is not None:
                total_profit_percentage = round((best_profit - 1) * 100, 5)
                print("-------------------------------------------")
                print(f"New {total_profit_percentage}% opportunity:")
                for i, opportunity in enumerate(best_opportunities):
                    order_side = 'buy' if opportunity.reversed else 'sell'
                    print(f"{i + 1}. {order_side} {opportunity.symbol.base} "
                          f"{'with' if order_side == 'buy' else 'for'} "
                          f"{opportunity.symbol.quote} at {opportunity.last_price:.5f}")
                print("-------------------------------------------")
                
                if best_profit > 1.005:
                    print("Profit is > 0.5%. Executing trades...")
                    await detector.execute_arbitrage_cycle(exchange, best_opportunities, STARTING_AMOUNT)
                else:
                    print(f"Profit ({total_profit_percentage}%) is too low to cover fees (>0.5% needed). Skipping execution.")
            else:
                print("No opportunity detected")
                
            await asyncio.sleep(2)
    except Exception as e:
        print(f"Error in main loop: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main_loop())

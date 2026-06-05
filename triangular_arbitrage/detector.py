# pylint: disable=W0702, C0325

import ccxt.async_support as ccxt
from typing import List, Tuple, Dict, Any
import networkx as nx

import octobot_commons.symbols as symbols
import octobot_commons.constants as constants


async def fetch_tickers(exchange):
    return await exchange.fetch_tickers() if exchange.has['fetchTickers'] else {}

def get_symbol_from_key(key_symbol: str) -> symbols.Symbol:
    try:
        return symbols.parse_symbol(key_symbol)
    except:
        return None

def is_delisted_symbols(exchange_time, ticker,
                        threshold=1 * constants.DAYS_TO_SECONDS * constants.MSECONDS_TO_SECONDS) -> bool:
    ticker_time = ticker['timestamp']
    return ticker_time is not None and not (exchange_time - ticker_time <= threshold)


def get_last_prices(exchange_time, tickers, ignored_symbols, whitelisted_symbols=None):
    valid_tickers = {}
    for key, ticker in tickers.items():
        sym = get_symbol_from_key(key)
        if sym is None: continue
        if not sym.is_spot(): continue
        if str(sym) in ignored_symbols: continue
        if whitelisted_symbols and str(sym) not in whitelisted_symbols: continue
        if is_delisted_symbols(exchange_time, ticker): continue
        
        # Must have valid bid and ask to perform arbitrage
        bid = ticker.get('bid')
        ask = ticker.get('ask')
        if bid and ask and bid > 0 and ask > 0:
            valid_tickers[str(sym)] = {
                'symbol': sym,
                'bid': float(bid),
                'ask': float(ask)
            }
    return valid_tickers


def get_best_opportunity(tickers: Dict[str, Any], max_cycle: int = 4) -> Tuple[List[Dict[str, Any]], float]:
    graph = nx.DiGraph()

    for key, ticker in tickers.items():
        base = ticker['symbol'].base
        quote = ticker['symbol'].quote
        
        # We hold Base, we want Quote -> SELL Base for Quote
        # We receive 'bid' amount of Quote per 1 Base
        graph.add_edge(base, quote, 
                       step={'symbol': key, 'side': 'sell', 'price': ticker['bid'], 'multiplier': ticker['bid']})
        
        # We hold Quote, we want Base -> BUY Base with Quote
        # We pay 'ask' amount of Quote per 1 Base -> We receive (1 / ask) Base per 1 Quote
        graph.add_edge(quote, base, 
                       step={'symbol': key, 'side': 'buy', 'price': ticker['ask'], 'multiplier': 1.0 / ticker['ask']})

    best_profit = 1.0
    best_cycle = None

    start_node = "USDT"
    if start_node not in graph:
        return None, 1.0

    def dfs(current_node, start_node, depth, max_depth, path, profit):
        nonlocal best_profit, best_cycle
        
        if depth > 1 and current_node == start_node:
            if profit > best_profit:
                best_profit = profit
                best_cycle = path[:]
            return

        if depth == max_depth:
            return

        for neighbor in graph.neighbors(current_node):
            if neighbor != start_node and neighbor in [n for n, _ in path]:
                continue # prevent sub-loops, only complete the cycle to start_node
                
            edge_data = graph[current_node][neighbor]['step']
            path.append((current_node, edge_data))
            dfs(neighbor, start_node, depth + 1, max_depth, path, profit * edge_data['multiplier'])
            path.pop()

    dfs(start_node, start_node, 0, max_cycle, [], 1.0)

    if best_cycle is not None:
        best_cycle_steps = [step for _, step in best_cycle]
        return best_cycle_steps, best_profit

    return None, 1.0


async def get_exchange_data(exchange):
    tickers = await fetch_tickers(exchange)
    filtered_tickers = {
        symbol: ticker
        for symbol, ticker in tickers.items()
        if exchange.markets.get(symbol, {}).get(
            "active", True
        ) is True
    }
    exchange_time = exchange.milliseconds()
    return filtered_tickers, exchange_time


async def get_exchange_last_prices(exchange, ignored_symbols, whitelisted_symbols=None):
    tickers, exchange_time = await get_exchange_data(exchange)
    last_prices = get_last_prices(exchange_time, tickers, ignored_symbols, whitelisted_symbols)
    return last_prices


async def run_detection_loop(exchange, ignored_symbols=None, whitelisted_symbols=None, max_cycle=10):
    last_prices = await get_exchange_last_prices(exchange, ignored_symbols or [], whitelisted_symbols)
    best_opportunity, best_profit = get_best_opportunity(last_prices, max_cycle=max_cycle)
    return best_opportunity, best_profit


async def execute_arbitrage_cycle(exchange, cycle, starting_amount):
    current_amount = starting_amount
    order_ids = []
    success = True
    for step in cycle:
        symbol = step['symbol']
        side = step['side']
        price = step['price']
        
        print(f"-> Executing {side} for {symbol} at ~{price}...")
        try:
            if side == 'buy':
                amount_base = current_amount / price
                amount_base = exchange.amount_to_precision(symbol, amount_base)
                order = await exchange.create_market_order(symbol, 'buy', float(amount_base))
                current_amount = float(amount_base) # Update current balance to base coin amount
            else:
                amount_base = exchange.amount_to_precision(symbol, current_amount)
                order = await exchange.create_market_order(symbol, 'sell', float(amount_base))
                current_amount = float(amount_base) * price # Update current balance to quote coin amount
                
            print(f"   Order placed successfully! ID: {order.get('id', 'N/A')}")
            order_ids.append(order.get('id', 'N/A'))
        except Exception as e:
            print(f"   Failed to execute {side} on {symbol}: {e}")
            success = False
            break
            
    return success, current_amount, order_ids

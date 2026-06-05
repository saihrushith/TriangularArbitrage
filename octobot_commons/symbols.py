class Symbol:
    def __init__(self, symbol_str):
        self.symbol = symbol_str
        parts = symbol_str.split('/')
        self.base = parts[0] if len(parts) > 0 else ""
        self.quote = parts[1] if len(parts) > 1 else ""

    def __str__(self):
        return self.symbol

    def is_spot(self):
        return ':' not in self.symbol and '-' not in self.symbol

def parse_symbol(symbol_str):
    return Symbol(symbol_str)

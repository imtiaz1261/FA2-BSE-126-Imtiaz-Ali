"""
tools/stock_tool.py
----------------------
get_stock_price(symbol) -- current/latest stock price for a ticker
symbol, via yfinance (free, no API key -- pulls from Yahoo Finance).
"""

from errors import ToolExecutionError

# --------------------------------------------------------------------------
# Tool schema (OpenAI / Groq function-calling format)
# --------------------------------------------------------------------------
SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_stock_price",
        "description": (
            "Get the latest stock price for a given ticker symbol. "
            "Use this whenever the user asks about a stock's price, "
            "value, or how a company's shares are doing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "The stock ticker symbol, e.g. 'AAPL' for Apple or 'TSLA' for Tesla.",
                },
            },
            "required": ["symbol"],
        },
    },
}


def get_stock_price(symbol: str) -> dict:
    """
    Execute the stock price lookup. Returns a plain dict of structured data.
    Raises ToolExecutionError for an unknown/invalid ticker or a data-fetch failure.
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ToolExecutionError("yfinance is not installed. Run: pip install yfinance") from exc

    symbol = symbol.strip().upper()

    try:
        ticker = yf.Ticker(symbol)
        fast_info = ticker.fast_info
        price = fast_info.get("lastPrice") if hasattr(fast_info, "get") else fast_info.last_price
        currency = fast_info.get("currency") if hasattr(fast_info, "get") else fast_info.currency
    except Exception as exc:
        raise ToolExecutionError(f"Failed to fetch stock data for '{symbol}': {exc}") from exc

    if price is None:
        raise ToolExecutionError(
            f"No price data found for ticker '{symbol}' -- it may be an invalid or delisted symbol."
        )

    return {
        "symbol": symbol,
        "price": round(float(price), 2),
        "currency": currency or "USD",
    }

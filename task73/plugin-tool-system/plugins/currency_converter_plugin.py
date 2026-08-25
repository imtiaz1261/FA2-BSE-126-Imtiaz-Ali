"""
plugins/currency_converter_plugin.py
---------------------------------------
Sample plugin: currency conversion via the Frankfurter API (free, no
API key -- European Central Bank reference rates).
"""

import requests

from core.base_plugin import BasePlugin, PluginExecutionError


class CurrencyConverterPlugin(BasePlugin):
    name = "currency_converter"
    description = "Convert an amount from one currency to another using current exchange rates."
    input_schema = {
        "type": "object",
        "properties": {
            "amount": {"type": "number", "description": "The amount to convert."},
            "from_currency": {"type": "string", "description": "3-letter source currency code, e.g. 'USD'."},
            "to_currency": {"type": "string", "description": "3-letter target currency code, e.g. 'EUR'."},
        },
        "required": ["amount", "from_currency", "to_currency"],
    }

    def execute(self, amount: float, from_currency: str, to_currency: str) -> str:
        from_currency = from_currency.strip().upper()
        to_currency = to_currency.strip().upper()

        try:
            resp = requests.get(
                "https://api.frankfurter.app/latest",
                params={"amount": amount, "from": from_currency, "to": to_currency},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            raise PluginExecutionError(f"Could not reach the currency exchange service: {exc}")

        rates = data.get("rates", {})
        if to_currency not in rates:
            raise PluginExecutionError(
                f"Could not convert '{from_currency}' to '{to_currency}' -- check the currency codes are valid."
            )

        converted = rates[to_currency]
        return f"{amount} {from_currency} = {round(converted, 2)} {to_currency} (as of {data.get('date')})"

"""Static metadata for the supported top-10 cryptocurrencies.

Centralized so both the `/cryptos` listing endpoint and the mock posts provider
share the same canonical list. Symbols are Binance trading pair symbols
(quoted in USDT) so they can be passed directly to the klines endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CryptoMeta:
    symbol: str
    name: str
    base_asset: str


SUPPORTED_CRYPTOS: tuple[CryptoMeta, ...] = (
    CryptoMeta("BTCUSDT", "Bitcoin", "BTC"),
    CryptoMeta("ETHUSDT", "Ethereum", "ETH"),
    CryptoMeta("BNBUSDT", "BNB", "BNB"),
    CryptoMeta("SOLUSDT", "Solana", "SOL"),
    CryptoMeta("XRPUSDT", "XRP", "XRP"),
    CryptoMeta("ADAUSDT", "Cardano", "ADA"),
    CryptoMeta("DOGEUSDT", "Dogecoin", "DOGE"),
    CryptoMeta("AVAXUSDT", "Avalanche", "AVAX"),
    CryptoMeta("DOTUSDT", "Polkadot", "DOT"),
    CryptoMeta("TRXUSDT", "TRON", "TRX"),
)

SUPPORTED_SYMBOLS: frozenset[str] = frozenset(c.symbol for c in SUPPORTED_CRYPTOS)


def get_crypto(symbol: str) -> CryptoMeta | None:
    upper = symbol.upper()
    for meta in SUPPORTED_CRYPTOS:
        if meta.symbol == upper:
            return meta
    return None

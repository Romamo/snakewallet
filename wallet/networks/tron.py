from typing import NamedTuple

from wallet.types import Token


class TronTokens(NamedTuple):
    USDT = Token(address='TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t', symbol='USDT', decimals=6)

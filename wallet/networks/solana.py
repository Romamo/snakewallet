from typing import NamedTuple

from wallet.types import Token


class SolanaTokens(NamedTuple):
    USDC = Token(address='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', symbol='USDC', decimals=6)

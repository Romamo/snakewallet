from typing import TypedDict, NamedTuple

from wallet.types import Token


class SepoliaTokens(NamedTuple):
    USDC = Token(address='0xd98B590ebE0a3eD8C144170bA4122D402182976f', symbol='USDC', decimals=6)

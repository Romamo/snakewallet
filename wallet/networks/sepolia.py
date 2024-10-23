from typing import NamedTuple

from wallet.types import Token


class SepoliaTokens(NamedTuple):
    USDC = Token(address='0xd98B590ebE0a3eD8C144170bA4122D402182976f', symbol='USDC', decimals=6)
    USDT = Token(address='0x7169d38820dfd117c3fa1f22a697dba58d90ba06', symbol='USDT', decimals=6)
    zkTCRO = Token(address='0x49cE7551514f3c2Bf44B50442765Bb112d0e8204', symbol='zkTCRO', decimals=6)

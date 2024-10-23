from typing import NamedTuple

from wallet.types import Token


class PlumeTokens(NamedTuple):
    GOON = Token(name='Goon Testnet Token',
                 symbol='GOON',
                 address='0xbA22114ec75f0D55C34A5E5A3cf384484Ad9e733',
                 decimals=18)

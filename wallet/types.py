import json
from typing import TypedDict, NewType, Union, NamedTuple, List

from pydantic import BaseModel

URI = NewType("URI", str)


class Network(NamedTuple):
    adapter: str
    rpc: Union[URI, List[URI]]
    chain_id: int = None
    symbol: str = None
    decimals: int = 18
    # id: int = None
    name: str = None
    url: str = None
    explorer: str = None
    faucet: str = None
    testnet: bool = False
    block_explorer: str = None
    coin_id: int = None  # https://github.com/trustwallet/wallet-core/blob/master/registry.json
    pancakeswap_id: str = None


class EthereumNetwork(Network):
    adapter: str = 'w3'
    # chain: int
    # adapter: str = 'w3'
    # rpc: URI = URI('https://eth.llama.com/')


class Token(NamedTuple):
    address: str
    symbol: str
    decimals: int
    name: str = None

    _DEFAULT_ABI = [{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf",
                     "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view",
                     "type": "function"}]

    def get_abi(self):
        try:
            with open(f'wallet/abi/{self.address}.json') as f:
                return json.load(f)
        except FileNotFoundError:
            return self._DEFAULT_ABI

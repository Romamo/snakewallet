import json
from typing import Optional

from pydantic import BaseModel


class Contract(BaseModel):
    address: str
    abi: Optional[list] = None

    _DEFAULT_ABI = [{"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf",
                     "outputs": [{"name": "", "type": "uint256"}], "payable": False, "stateMutability": "view",
                     "type": "function"}]

    def get_abi(self, path: str = None) -> list:
        if not self.abi:
            with open(f'{path or "wallet/abi/"}{self.address}.json') as f:
                self.abi = json.load(f)
        return self.abi

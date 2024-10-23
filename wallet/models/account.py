from typing import Union, Optional

import base58
from hexbytes import HexBytes
from pydantic import BaseModel


class Account(BaseModel):
    address: Optional[str] = None
    private_key: Optional[bytes] = None

    @property
    def address_bytes(self):
        return self.address  # bytes.fromhex(self.address[2:])

    @staticmethod
    def create(address: str = None, private_key: Union[str, bytes] = None):
        if not private_key and len(address) == 64:
            private_key = address
            address = None

        # if isinstance(address, str):
        #     # base58
        #     if len(address) == 44:
        #         address = base58.b58decode(address.encode())
        #     else:
        #         address = bytes.fromhex(address)
        if isinstance(private_key, str):
            private_key = HexBytes(private_key)
        return Account(address=address, private_key=private_key)

    #
    # @staticmethod
    # def from_private_key(key: Union[str, bytes]):
    #     if isinstance(key, str):
    #         key = bytes.fromhex(key)
    #     acct = eth_account.from_key(private_key)
    #
    #     return Account(address=eth_account.address, private_key=key.hex())

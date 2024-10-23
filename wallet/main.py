from decimal import Decimal
from typing import Union

from eth_typing import HexStr
from hexbytes import HexBytes

from .adapters import create_adapter
from .models import Contract
from .models.account import Account
from .types import Token


class Wallet:
    # provider_options: dict = None,
    def __init__(self, network=None, testnet=None, rpc=None, chain_id=None, **kwargs):
        if not network and not testnet:
            raise ValueError("Either network or testnet must be provided")

        self._network = network or testnet
        # if rpc:
        #     self._network.rpc = rpc
        # if chain_id:
        #     self._network.chain_id = chain_id
        self._adapter = create_adapter(network or testnet, rpc, chain_id, **kwargs)

    @property
    def adapter(self):
        return self._adapter

    @property
    def client(self):
        return self._adapter._client

    def get_network(self):
        return self._network

    def create_account(self, text: Union[str, bytes]) -> Account:
        if isinstance(text, str):
            text = text.strip()
        return self._adapter.create_account(text)

    def create_contract(self, contract_address: Union[Token, str, bytes], abi: list = None) -> Contract:
        if isinstance(contract_address, Token):
            contract_address = contract_address.address
        return self._adapter.create_contract(contract_address, abi)

    def get_balance(self, address: Union[str, bytes], token: Token = None, decimals=None) -> Decimal:
        account = self.create_account(address)
        # if token:
        #     contract = self.create_contract(contract)
        balance = self._adapter.get_balance(account, token=token)
        if decimals:
            return balance.quantize(Decimal(f"1e-{decimals}"))
        return balance

    def generate_account(self, **kwargs) -> Account:
        return self._adapter.generate_account(**kwargs)

    def send(self, private_key: Union[str, bytes], address, amount: Union[float, Decimal]):
        sender = self._adapter.create_account(private_key)
        account = self._adapter.create_account(address)
        return self._adapter.send(sender, account, amount)

    def transfer(self, private_key: Union[str, bytes], address, token: Token, amount: Union[float, Decimal]):
        sender = self._adapter.create_account(private_key)
        account = self._adapter.create_account(address)
        return self._adapter.transfer(sender, account, amount)

    def sign(self, sender: Union[str, bytes], message: Union[str, bytes]) -> str:
        if isinstance(message, str):
            message = message.encode('utf-8')
        sender = self._adapter.create_account(sender)
        return self._adapter.sign(sender, message)

    def approve(self, sender: Union[str, bytes], spender: Union[str, bytes], contract: Union[str, bytes], amount: Union[float, Decimal]):
        sender = self._adapter.create_account(sender)
        spender = self._adapter.create_account(spender)
        return self._adapter.approve(sender, spender, contract, amount)

    def estimate(self, contract: Union[Token, Contract, str, bytes],
                 method: str,
                 amount: Union[float, Decimal], **kwargs):
        if isinstance(contract, Token):
            if amount:
                amount = int(amount * 10 ** contract.decimals)
            contract = self.create_contract(contract)
        elif not isinstance(contract, Contract):
            contract = self.create_contract(contract)
        return self._adapter.estimate(contract, method, amount, **kwargs)

    def call(self, contract: Union[Contract, str, bytes], method: str, args):
        if not isinstance(contract, Contract):
            contract = self.create_contract(contract)
        return self._adapter.call(contract, method, args)

    def deploy_account(self, private_key: str):
        return self._adapter.deploy_account(private_key)

    def decode_response(self, contract: Union[Contract, str, bytes], method: str, response: str):
        if not isinstance(contract, Contract):
            contract = self.create_contract(contract)
        return self._adapter.decode_response(contract, method, HexBytes(response))

    def decode_call(self, contract: Union[Contract, str, bytes], data: str, response: str = None):
        if not isinstance(contract, Contract):
            contract = self.create_contract(contract)
        function, args = self._adapter.decode_calldata(contract, HexStr(data))

        if response:
            output = self._adapter.decode_response(contract, function, HexBytes(response))
        else:
            output = None

        return function, args, output

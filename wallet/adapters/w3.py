import decimal
import itertools
import json
from decimal import Decimal
from functools import partial
from typing import Union, Dict

import requests
import web3
from eth_abi.exceptions import DecodingError
from eth_account.messages import defunct_hash_message
from eth_typing import Decodable, HexStr, ABIFunction
from eth_utils import get_abi_output_types
from hexbytes import HexBytes
from web3 import Web3
from eth_account import Account as EthAccount
from web3._utils.normalizers import (
    BASE_RETURN_NORMALIZERS,
    normalize_abi,
    normalize_address,
    normalize_bytecode,
)
from web3._utils.abi import map_abi_data
from web3.contract.utils import ACCEPTABLE_EMPTY_STRINGS
# from web3._utils.normalizers import BASE_RETURN_NORMALIZERS
# from web3._utils import normalizers
# from web3._utils.abi import get_abi_output_types, map_abi_data
# from web3._utils.normalizers import BASE_RETURN_NORMALIZERS
# from web3.contract import ACCEPTABLE_EMPTY_STRINGS
from web3.exceptions import BadFunctionCallOutput

from wallet.adapters.base import AdapterBase
from wallet.adapters.exceptions import AlreadyKnownTransaction
from wallet.models import Contract, Transaction
from wallet.models.account import Account
from wallet.types import Token

EthAccount.enable_unaudited_hdwallet_features()


class W3Adapter(AdapterBase):
    def __init__(self, endpoint_uri, chain_id, decimals=None, **kwargs):
        if isinstance(endpoint_uri, list):
            endpoint_uri = endpoint_uri[0]
        self._client = Web3(Web3.HTTPProvider(endpoint_uri))
        self._chain_id = chain_id
        self._decimals = decimals or 18

    @staticmethod
    def create_account(text: Union[str, bytes]) -> Account:
        """
        Create an account from an address, private key or mnemonic
        :param text:
        :return:
        """
        if isinstance(text, bytes) or len(text) in [64, 66]:
            acct = EthAccount.from_key(text)
            return Account.create(address=acct.address, private_key=acct.key)
        elif ' ' in text:
            acct = EthAccount.from_mnemonic(text)
            return Account.create(address=acct.address, private_key=acct.key)
        return Account.create(address=text)

    def _get_account(self, account: Account):
        return self._client.eth.account.from_key(account.private_key)

    def _get_contract(self, contract_address):
        abi = self.get_abi(contract_address)
        return self._client.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)

    def generate_account(self, extra_entropy="") -> Account:
        eth_account = self._client.eth.account.create(extra_entropy)
        return Account.create(address=eth_account.address, private_key=eth_account.key)

    def get_balance(self, account: Account, contract: Contract = None, token: Token = None) -> Decimal:
        if token:
            eth_contract = self._client.eth.contract(address=Web3.to_checksum_address(token.address), abi=token.get_abi())
            balance = eth_contract.functions.balanceOf(account.address_bytes).call()
            return balance / 10 ** token.decimals

        if contract:
            eth_contract = self._client.eth.contract(address=Web3.to_checksum_address(contract.address), abi=contract.get_abi())
            balance = eth_contract.functions.balanceOf(account.address_bytes).call()
            return balance / 10 ** self._decimals

        try:
            balance = self._client.eth.get_balance(account.address_bytes)
            return balance / 10 ** self._decimals
        except requests.exceptions.ReadTimeout as e:
            print(e)

    def build_transaction(self, sender: Account, account: Account, amount: Decimal) -> dict:
        sender_account = self._client.eth.account.from_key(sender.private_key)
        transaction = {
            'chainId': self._chain_id,
            'from': sender_account.address,
            'to': account.address,
            'value': int(amount * 10 ** self._decimals),
            'nonce': self._client.eth.get_transaction_count(sender_account.address),
        }
        return transaction

    def estimate_gas(self, transaction: dict):
        return self._client.eth.estimate_gas(transaction)

    def sign_transaction(self, sender: Account, transaction: dict) -> HexBytes:
        sender_account = self._client.eth.account.from_key(sender.private_key)
        return self._client.eth.account.sign_transaction(transaction, sender_account.key).rawTransaction

    def send(self, sender: Account, account: Account, amount: Decimal) -> str:
        # sender_account = self._client.eth.account.from_key(sender.private_key)
        transaction = self.build_transaction(sender, account, amount)
        transaction['gas'] = 21000 or self.estimate_gas(transaction)
        transaction['gasPrice'] = self._client.to_wei('10', 'gwei')

        # transaction = {
        #     # 'maxFeePerGas': 1,
        #     # 'maxPriorityFeePerGas': 1,
        # }
        # gas = self._client.eth.estimate_gas(transaction)

        # 2. Sign tx with a private key
        # signed = self._client.eth.account.sign_transaction(transaction, sender_account.key)

        rawTransaction = self.sign_transaction(sender, transaction)

        # 3. Send the signed transaction
        try:
            tx_hash = self._client.eth.send_raw_transaction(rawTransaction)
        except ValueError as e:
            raise AlreadyKnownTransaction(e)
        return tx_hash.hex()

    def transfer(self, sender: Account, receiver: Account, token: Token,
                 amount: Union[int, float, str, decimal.Decimal]) -> str:
        sender_account = self._client.eth.account.from_key(sender.private_key)
        contract = self.create_contract(token.address)

        token_amount = self._client.to_wei(amount, 'ether')

        nonce = self._client.eth.getTransactionCount(sender.address)

        transaction = contract.functions.transfer(receiver.address, token_amount).build_transaction({
            'chainId': self._client.eth.chain_id,
            'gas': 2000000,  # Adjust the gas limit as needed
            'gasPrice': self._client.eth.gas_price,  # Adjust the gas price as needed or use w3.eth.generate_gas_price()
            'nonce': nonce,
        })

        # Sign the transaction with the private key
        signed_txn = self._client.eth.account.sign_transaction(transaction, sender_account.private_key)

        # Attempt to send the transaction
        try:
            tx_hash = self._client.eth.send_raw_transaction(signed_txn.rawTransaction)
            print(f"Transaction sent! Hash: {tx_hash.hex()}")
        except Exception as e:
            print(f"Error sending transaction: {e}")
            raise Exception(f"Error sending transaction: {e}")
        return tx_hash.hex()

    def approve(self, sender: Account, spender: Account, token: Token, amount: Decimal) -> str:
        contract = self.create_contract(token.address)

        # spender = spender_address
        max_amount = self._client.toWei(2 ** 64 - 1, 'ether')
        nonce = self._client.eth.getTransactionCount(sender.address)

        tx = contract.functions.approve(spender.address, max_amount).buildTransaction({
            'from': sender.address,
            'nonce': nonce
        })

        signed_tx = self._client.eth.account.signTransaction(tx, sender.private_key)
        tx_hash = self._client.eth.sendRawTransaction(signed_tx.rawTransaction)

        return self._client.toHex(tx_hash)

    def sign(self, sender: Account, message: bytes) -> str:
        # sender_account = self._client.eth.account.from_key(sender.private_key)

        signable_message = defunct_hash_message(message)

        signature = self._client.eth.account._sign_hash(signable_message, private_key=sender.private_key)

        return signature.signature.hex()
    #
    # def build_transaction2(self, account: Account, contract: Contract, method: str, params: dict) -> Transaction:
    #     # eth_contract = pass
    #
    #     try:
    #         unsent_contract_tx = eth_contract.functions.unstake().build_transaction({
    #             "from": account.address_bytes,
    #             "nonce": self._client.eth.get_transaction_count(account.address_bytes),
    #         })
    #     except web3.exceptions.ContractLogicError as e:
    #         print(e, e.message)
    #         return False

    def decode_calldata(self, contract: Contract, data: HexStr):
        contract_eth = self._client.eth.contract(address=Web3.toChecksumAddress(contract.address), abi=contract.get_abi())
        decoded_input = contract_eth.decode_function_input(data)
        function, args = decoded_input

        # output_names = [o['name'] for o in function_abi['outputs']]
        # outputs = function_abi['outputs']
        #
        # contract_eth.in
        # a = self.map_output(function.abi['inputs'][0], args['calls'][0])
        mapped_input = self.map_output(function.abi['inputs'][0], args)
        return function, mapped_input

    def decode_response(self, contract: Contract, function: Union[str, ABIFunction], return_data: Decodable):
        if isinstance(function, str):
            contract_eth = self._client.eth.contract(address=Web3.toChecksumAddress(contract.address), abi=contract.get_abi())
            # fn_abi = getattr(contract_eth.functions, method)
            function = contract_eth.find_functions_by_name(function)[0]

        output_types = get_abi_output_types(function.abi)

        try:
            output_data = self._client.codec.decode(output_types, return_data)
        except DecodingError as e:
            # Provide a more helpful error message than the one provided by
            # eth-abi-utils
            is_missing_code_error = (
                    return_data in ACCEPTABLE_EMPTY_STRINGS
                    and self._client.eth.get_code(contract.address) in ACCEPTABLE_EMPTY_STRINGS)
            if is_missing_code_error:
                msg = (
                    "Could not transact with/call contract function, is contract "
                    "deployed correctly and chain synced?"
                )
            else:
                msg = (
                    f"Could not decode contract function call to {function} with "
                    f"return data: {str(return_data)}, output_types: {output_types}"
                )
            raise BadFunctionCallOutput(msg) from e

        # normalizers = {
        #     'abi': normalize_abi,
        #     # 'address': partial(normalize_address, kwargs['web3'].ens),
        #     'bytecode': normalize_bytecode,
        #     'bytecode_runtime': normalize_bytecode,
        # }

        _normalizers = itertools.chain(
            BASE_RETURN_NORMALIZERS,
            (),
        )
        normalized_data = map_abi_data(_normalizers, output_types, output_data)

        # if len(normalized_data) == 1:
        #     return normalized_data[0]
        # else:
        #     return normalized_data
        #
        return self.decode_response2(contract, function, normalized_data[0] if len(normalized_data) == 1 else normalized_data)

    def map_output(self, output: Union[Dict, str], output_value):
        if isinstance(output_value, tuple):
            output_value = list(output_value)
        if isinstance(output, dict) and output['type'] in ['tuple[]'] and isinstance(output_value, dict):
            if isinstance(output_value[output['name']], tuple):
                output_value[output['name']] = list(output_value[output['name']])
            for i, r in enumerate(output_value[output['name']]):
                output_value[output['name']][i] = self.map_output(output, r)
            return output_value
        elif isinstance(output, dict) and output['type'] in ['tuple', 'tuple[]']:
            tuple_components = output['components']
            for i, component in enumerate(tuple_components):
                if component.get('components'):
                    output_value[i] = self.map_output(component, output_value[i])
            tuple_types = [component['type'] for component in tuple_components]
            tuple_names = [component['name'] for component in tuple_components]
            decoded_tuple = [self.map_output(t, v) for t, v in zip(tuple_types, output_value)]
            return dict(zip(tuple_names, decoded_tuple))
        else:
            return output_value

    def decode_response2(self, contract: Contract, function: Union[str, ABIFunction], response: list):
        if isinstance(function, str):
            function_abi = next((f for f in contract.abi if f['type'] == 'function' and f['name'] == function), None)
            output_names = [o['name'] for o in function_abi['outputs']]
            outputs = function_abi['outputs']
        else:
            output_names = [o['name'] for o in function.abi['outputs']]
            outputs = function.abi['outputs']
        if isinstance(response, (list, tuple)):
            ret = []
            for r in response:
                if len(outputs) == 1:
                    a = self.map_output(outputs[0], r)
                else:
                    decoded_response = [self.map_output(o, v) for o, v in zip(outputs, response)]
                    a = dict(zip(output_names, decoded_response))
                ret.append(a)
            return ret
        else:
            if len(outputs) == 1:
                return self.map_output(outputs[0], response)
            else:
                decoded_response = [self.map_output(o, v) for o, v in zip(outputs, response)]
                return dict(zip(output_names, decoded_response))

    def call(self, contract: Contract, method: str, args):
        contract_eth = self._client.eth.contract(address=Web3.toChecksumAddress(contract.address), abi=contract.abi)
        function = getattr(contract_eth.functions, method)

        response = function(args).call()

        return self.decode_response(contract, method, response)

    def deploy_account(self, private_key: str) -> bool:
        return True


def create_adapter(network, rpc: str = None, chain_id: int = None, **kwargs):
    return W3Adapter(rpc or network.rpc, chain_id=chain_id or network.chain_id, **kwargs)

from typing import Union

import math
import tronpy
import trontxsize as trontxsize
from tronpy import Tron, Contract as TronContract
from tronpy.abi import trx_abi
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
from tronpy.tron import TAddress, Transaction

from wallet.adapters.base import AdapterBase
from wallet.adapters.exceptions import AddressNotFound
from wallet.models import Contract
from wallet.types import Token

TRC20_ENERGY_UNIT_PRICE = 420
TRC20_FEE_LIMIT_FACTOR = 1.1
RECEIPT_RETRY_INTERVAL = 5
RECEIPT_RETRY_ATTEMPTS = 3
TRX_NET_FEE = 3_000_000
TRC20_FEE_LIMIT = 30_000_000


class TronAdapter(AdapterBase):
    _decimals = 6

    def __init__(self, endpoint_uri, chain_id, decimals=None, provider_options: dict = None):
        if isinstance(endpoint_uri, list):
            endpoint_uri = endpoint_uri[0]
        self._client = Tron(HTTPProvider(endpoint_uri, **provider_options))

        # self._chain_id = chain_id
        # self._decimals = decimals or 18

    def create_account(self, text: Union[str, bytes]) -> TAddress:
        if isinstance(text, str):
            text = text.strip()
        return self._client.to_hex_address(text)

    def get_balance(self, address: TAddress, token: Token = None) -> int:
        if not token:
            try:
                account = self._client.get_account(address)
            except tronpy.exceptions.AddressNotFound:
                raise AddressNotFound
            return account['balance'] / 10 ** self._decimals
        contract = TronContract(token.address, abi=token.get_abi(), client=self._client)
        return contract.functions.balanceOf(address) / 10 ** token.decimals

    def get_energy(self, address: TAddress) -> int:
        account = self._client.get_account_resource(address)
        return account.get('EnergyLimit', 0)

    def estimate(self, contract: Contract, method: str, amount: int,
                 owner_address: TAddress, address_recipient: TAddress) -> dict:
        contract_tron = TronContract(contract.address, abi=contract.get_abi())
        parameter = contract_tron.functions[method]._prepare_parameter(address_recipient, amount)
        try:
            energy_data = self._client.trigger_constant_contract(self._client.to_hex_address(owner_address),
                                                              contract.address,
                                                              contract_tron.functions[method].function_signature,
                                                              parameter)
            energy_required = energy_data['energy_used']
        except tronpy.exceptions.TvmError as e:
            if e.args[0] == 'REVERT opcode executed':
                # Looks like address_recipient has no TRX
                energy_required = 31895
            else:
                raise e
        try:
            account_info = self._client.get_account_resource(owner_address)
        except tronpy.exceptions.AddressNotFound:
            account_info = {}

        energy_limit = account_info.get('EnergyLimit', 0)
        energy_used = account_info.get('EnergyUsed', 0)

        energy_fee = self.get_energy_fee(energy_required, energy_limit, energy_used)

        tx = self.build_tx(PrivateKey.random(), address_recipient, amount)

        bandwidth_required = self.get_bandwidth_required(tx)
        bandwidth_fee = self.get_bandwidth_fee(tx, account_info, bandwidth_required)

        return {
            'energy_required': energy_required,
            'energy_used': energy_used,
            'energy_limit': energy_limit,
            'energy_available': energy_limit-energy_used,
            'energy_lack': energy_required-(energy_limit-energy_used),
            'energy_fee': energy_fee,
            'bandwidth_required': bandwidth_required,
            'bandwidth_available': account_info.get('freeNetLimit', 0) - account_info.get('freeNetUsed', 0),
            'bandwidth_fee': bandwidth_fee,
            'total_fee': math.ceil((bandwidth_fee + energy_fee) * TRC20_FEE_LIMIT_FACTOR)
        }

    def get_energy_fee(self, energy_needed: float, energy_limit: float, energy_used: float) -> int:
        current_account_energy = energy_limit - energy_used
        energy_fee = max(energy_needed - current_account_energy, 0) * TRC20_ENERGY_UNIT_PRICE
        return math.ceil(energy_fee)

    def get_bandwidth_required(self, tx: Transaction) -> int:
        return trontxsize.get_tx_size({'signature': tx._signature, 'raw_data': tx._raw_data})

    def get_bandwidth_fee(self, tx: Transaction, account_info: dict, bandwidth_required) -> int:
        try:
            # account_info = self._client.get_account_resource(address)
            free_net_limit = account_info.get('freeNetLimit', 0)
            net_limit = account_info.get('NetLimit', 0)
            free_net_used = account_info.get('freeNetUsed', 0)
            net_used = account_info.get('NetUsed', 0)
            total_bandwidth = free_net_limit + net_limit
            total_bandwidth_used = net_used + free_net_used
            current_account_bandwidth = total_bandwidth - total_bandwidth_used

            # how_many_bandwidth_need = trontxsize.get_tx_size({'signature': tx._signature, 'raw_data': tx._raw_data})
            if current_account_bandwidth < bandwidth_required:
                bandwidth_fee = (bandwidth_required + 3) * 1000
            else:
                bandwidth_fee = 0
            # bandwidth_fee = max((how_many_bandwidth_need - current_account_bandwidth) * 1000, 0)
            return math.ceil(bandwidth_fee * TRC20_FEE_LIMIT_FACTOR)  # TRX_NET_FEE
        except Exception:
            # log.exception('An error occurred while calculating bandwidth_fee')
            return TRX_NET_FEE

    def get_fee_limit(self, owner_address: str, to_address: str, amount: int, contract_address: str, tx: dict[str, any] = None) -> int:
        """
        Calculations are based on an article from Stack Overflow
        (https://stackoverflow.com/questions/67172564/how-to-estimate-trc20-token-transfer-gas-fee)

        https://github.com/Polygant/OpenCEX-backend/blob/d27cd7cf7c0a72bb25442ae7eae031a3f8b16389/cryptocoins/coins/trx/utils.py#L14
        """

        try:
            parameter = trx_abi.encode_abi(['address', 'uint256'], [to_address, amount]).hex()
            account_info = self._client.get_account_resource(addr=owner_address)
            energy_data = self._client.trigger_constant_contract(
                owner_address=owner_address,
                contract_address=contract_address,
                function_selector='transfer(address,uint256)',
                parameter=parameter
            )
            required_energy = energy_data['energy_used']
            energy_limit = account_info.get('EnergyLimit', 0)
            energy_used = account_info.get('EnergyUsed', 0)

            energy_fee = self.get_energy_fee(required_energy, energy_limit, energy_used)
            bandwidth_fee = self.get_bandwidth_fee(tx, owner_address)

            return math.ceil((bandwidth_fee + energy_fee) * TRC20_FEE_LIMIT_FACTOR)
        except Exception:
            return TRC20_FEE_LIMIT

    def build_tx(self, sender_key: Union[bytes, PrivateKey, str], address_recipient, amount, **kwargs) -> Transaction:
        if isinstance(sender_key, bytes):
            sender_key = PrivateKey(sender_key)
        elif isinstance(sender_key, str):
            sender_key = PrivateKey(bytes.fromhex(sender_key))
        from_address = sender_key.public_key.to_base58check_address()
        return self._client.trx.transfer(from_address, address_recipient, amount).memo("").build().sign(sender_key)

    def get_transactions(self, address, address_to):
        address_to = self._client.to_hex_address(address_to)
        info = self._client.provider.make_request(f"v1/accounts/{address}/transactions")
        print(info)


def create_adapter(network, rpc: str = None, chain_id: int = None, **kwargs):
    return TronAdapter(rpc or network.rpc, chain_id=chain_id or network.chain_id, **kwargs)

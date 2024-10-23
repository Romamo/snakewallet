from decimal import Decimal
from typing import Union, Optional, Dict

import solana
from solana.rpc import types, core
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solana.transaction import Transaction

from wallet.models import Account
from solana.rpc.api import Client

from wallet.types import Token


class SolanaAdapter:
    def __init__(self, endpoint_uri, decimals=None, extra_headers: Optional[Dict[str, str]] = None):
        self._client = AsyncClient(endpoint_uri, extra_headers=extra_headers)
        self._decimals = decimals or 9

    def create_account(self, address: Union[str, bytes]) -> Account:
        if len(address) == 88:
            keypair = Keypair.from_base58_string(address)
            return Account(address=str(keypair.pubkey()), private_key=address)
        return Account.create(address=address)

    @classmethod
    def _get_keypair(cls, account: Account) -> Keypair:
        if len(account.private_key) == 32:
            return Keypair.from_bytes(account.private_key)
        if len(account.private_key) == 64:
            return Keypair.from_seed(bytes.fromhex(account.private_key))
        if len(account.private_key) == 88:
            return Keypair.from_base58_string(account.private_key.decode())
        # mnemo = Mnemonic("english")
        # seed = mnemo.to_seed("enact denial cave suspect number general august deer outdoor fatal mistake local")
        # payer = Keypair.from_bytes(seed)
        raise NotImplementedError()

    @classmethod
    def _get_pubkey(cls, account: Union[str, Account]) -> Pubkey:
        if isinstance(account, Account):
            if not account.address:
                return cls._get_keypair(account).pubkey()
            address = account.address
        else:
            address = account
        return Pubkey.from_string(address)

    def get_balance(self, account: Account, token: Token = None):
        if token:
            balance = self._client.get_token_accounts_by_owner_json_parsed(
                self._get_pubkey(account),
                opts=solana.rpc.types.TokenAccountOpts(mint=self._get_pubkey(token.address)))
            return Decimal(balance.value[0].account.data.parsed['info']['tokenAmount']['uiAmount'])
        else:
            balance = self._client.get_balance(self._get_pubkey(account))
            return Decimal(balance.value / 10 ** self._decimals)

    def build_transaction(self, sender: Account, account: Account, amount: Decimal):
        return Transaction().add(transfer(TransferParams(
            from_pubkey=self._get_pubkey(sender),
            to_pubkey=self._get_pubkey(account),
            lamports=int(amount * 10 ** self._decimals))
        ))

    def send(self, sender: Account, account: Account, amount, skip_confirmation=False) -> str:
        transaction = self.build_transaction(sender, account, amount)

        try:
            response = self._client.send_transaction(transaction,
                                                     self._get_keypair(sender),
                                                     opts=types.TxOpts(skip_confirmation=skip_confirmation))
        except solana.rpc.core.RPCException as e:
            print(e)
            raise e

        return str(response.value)

    def deploy_account(self, address_key: str, payer_key: str):
        address = self.get_keypair(address_key)

        payer = self.get_keypair(payer_key)

        # new_account = Account()
        # request_airdrop = self._client.request_airdrop(address_pubkey, 1000000000)
        # a = self._client.get_balance(address_pubkey)
        fee = self._client.get_minimum_balance_for_rent_exemption(0)

        params = CreateAccountParams(
            from_pubkey=payer.pubkey(),
            to_pubkey=address.pubkey(),
            lamports=fee.value,
            space=0, owner=SYSTEM_PROGRAM_ID)

        create_tx = create_account(params)
        txn = Transaction()
        txn.add(
            create_tx
        )
        # opts = TxOpts(skip_confirmation=False)
        # print ("Please wait for confirmation ...")
        # poor_account = Keypair()
        # payer spends lamports for creation
        try:
            self._client.send_transaction(txn, payer, address)
        except solana.rpc.core.RPCException as e:
            print(e)

        return True

def create_adapter(network, rpc: str = None, chain: int = None, decimals: int = None, **kwargs):
    return SolanaAdapter(rpc or network.rpc, decimals, **kwargs)

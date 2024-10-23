from decimal import Decimal
from typing import List, Union, Dict

import backoff
import base58
import solana
from solana.constants import SYSTEM_PROGRAM_ID
from solana.rpc import types
from solana.rpc.api import Client

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.rpc.errors import SendTransactionPreflightFailureMessage
from solders.signature import Signature
from solders.system_program import create_account, CreateAccountParams, transfer, TransferParams
from solana.transaction import Transaction
from solders.transaction_status import TransactionConfirmationStatus

from .base import ClientBase
from .exceptions import PreflightError, TransactionError


class SolanaClient(ClientBase):
    _DECIMALS = 9

    def __init__(self):
        super().__init__()
        self._client = Client(self._ENDPOINT)

    def get_balance(self, address: str) -> Decimal:
        pubkey = Pubkey.from_string(address)
        balance = self._client.get_balance(pubkey)
        return Decimal(balance.value / 10 ** self._DECIMALS)

    def get_account_info(self, address: str):
        pubkey = Pubkey.from_string(address)
        info = self._client.get_account_info(pubkey)
        return info

    def generate_wallet(self) -> (str, str):
        keypair = Keypair()
        return str(keypair.pubkey()), keypair.secret().hex()

    @classmethod
    def get_keypair(cls, key: str) -> Keypair:
        if len(key) == 64:
            return Keypair.from_seed(bytes.fromhex(key))
        if len(key) == 87:
            return Keypair.from_base58_string(key)
        # mnemo = Mnemonic("english")
        # seed = mnemo.to_seed("enact denial cave suspect number general august deer outdoor fatal mistake local")
        # payer = Keypair.from_bytes(seed)
        raise NotImplementedError()

    @classmethod
    def convert_base58(cls, key: str) -> str:
        keypair = cls.get_keypair(key)
        private_key_bytes = keypair.secret()
        public_key_bytes = bytes(keypair.pubkey())
        encoded_keypair = private_key_bytes + public_key_bytes
        return base58.b58encode(encoded_keypair).decode()

    def create_account(self, address_key: str, payer_key: str):
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

    @backoff.on_exception(backoff.expo, solana.exceptions.SolanaRpcException, max_time=60)
    def is_confirmed(self, signatures: Union[str, List[str]]) -> bool:
        if isinstance(signatures, str):
            signatures = [signatures]
        signatures_solana = [Signature.from_string(signature) for signature in signatures]
        response = self._client.get_signature_statuses(signatures_solana)
        if response.value[0]:
            return response.value[0].confirmation_status in [TransactionConfirmationStatus.Confirmed, TransactionConfirmationStatus.Finalized]

    def send(self, sender_key, receiver_address, amount, skip_confirmation=True) -> str:
        sender = self.get_keypair(sender_key)
        receiver = Pubkey.from_string(receiver_address)

        transaction = Transaction().add(transfer(TransferParams(
            from_pubkey=sender.pubkey(),
            to_pubkey=receiver,
            lamports=int(amount * 10 ** self._DECIMALS))
        ))

        try:
            response = self._client.send_transaction(transaction, sender,
                                                     opts=types.TxOpts(skip_confirmation=skip_confirmation))
        except (solana.exceptions.SolanaRpcException, solana.rpc.core.RPCException) as e:
            print(e.__class__.__name__)
            raise TransactionError(e)

        return str(response.value)

    def sign(self, sender_key, message) -> str:
        sender = self.get_keypair(sender_key)
        message_bytes = message.encode()  # Convert the message to bytes
        signature = sender.sign_message(message_bytes)
        return bytes(signature).hex()

    def send_raw_transaction(self, sender_key, raw_transaction: bytes, skip_confirmation: bool=True, skip_preflight: bool=False) -> str:
        """
        Returns the transaction id
        :param sender_key:
        :param raw_transaction:
        :param skip_confirmation:
        :return:
        """
        sender = self.get_keypair(sender_key)

        txn = Transaction.deserialize(raw_transaction)

        txn.sign_partial(sender)
        # print(txn.signatures)
                # signed = await wallet.signTransaction(transaction);

        txn_bytes = txn.serialize()

        try:
            response = self._client.send_raw_transaction(txn_bytes,
                                                         opts=types.TxOpts(skip_confirmation=skip_confirmation,
                                                                           skip_preflight=skip_preflight))
        except solana.rpc.core.UnconfirmedTxError as e:
            print(e)
            raise TransactionError(e)
        except solana.exceptions.SolanaRpcException as e:
            print(e)
            raise TransactionError(e)
        except solana.rpc.core.RPCException as e:
            print(e)
            if isinstance(e.args[0], SendTransactionPreflightFailureMessage):
                raise PreflightError(e.args[0])
            print(e.args[0].data.logs)
            raise e

        return base58.b58encode(bytes(response.value)).decode()

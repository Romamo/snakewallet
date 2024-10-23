import datetime
import os
import time

from itrx import Client as ItrxClient
import qrcode
from tronscan import Client as TronscanClient

from wallet.adapters.exceptions import AddressNotFound
from wallet.main import Wallet
from wallet.networks import Networks
from wallet.types import Token

TRONGRID_KEY = os.getenv('TRONGRID_KEY')


class SendTronAction:
    def generate_qr_code(self, address, amount, token=None, memo=''):
        if token is None:
            token = Networks.Tron
        if token == Networks.Tron:
            asset = f'c{token.coin_id}'
        else:
            asset = f'c{Networks.Tron.coin_id}_t{token.address}'

        filename = f'data/qr_{address}_{amount}.png'
        # data = f'tron:{rent_address}?amount={rent_amount}'

        data = f'https://link.trustwallet.com/send?asset={asset}&address={address}&amount={amount}&memo={memo}'
        qr = qrcode.QRCode()
        qr.add_data(data)
        qr.make()
        img = qr.make_image(fill_color="black", back_color="white")

        # Save the QR code image
        img.save(filename)
        return filename

    def get_energy_price(self, energy_amount):
        client = ItrxClient()
        return client.get_price(energy_amount)

    def rent_energy(self, address, energy_amount):
        client = ItrxClient()
        order_id = client.create_order(address, energy_amount)
        return order_id


    def send(self, address_sender, address_recipient, amount, token: Token = None, dry_run=False):
        # Future templates:
        # send to {} ...
        # send {amount} from {}...
        # send {amount} from {} to {}
        """
        1. Select sending wallet (history, command, template)
        2. Check recipient
            a. Check the required number of resources to send the token
            b. Check TRX and USDT balance
            c. AML check
            d. Check for transactions in history
        3. Check the balance and resources of the sender
        4. Calculate the cost of the transaction, resources
        5. Issue a message and confirmation: history, balance, required resources, transaction cost
            Request confirmation: there were no transactions

        :param address_sender:
        :param address_recipient:
        :param amount:
        :return:
        """
        print(f"Planning to send {amount} USDT from {address_sender} to {address_recipient}...")

        wallet = Wallet(Networks.Tron, provider_options={'api_key': TRONGRID_KEY})

        print()
        # print("Checking sending address...")
        balance = wallet.get_balance(address_sender, token)
        if balance > amount:
            print(f"OK Sender has enough {token.symbol if token else 'native token'} to send")
        else:
            print(f"ERR Sender has not enough {token.symbol} to send")
            return

        # print("Checking recipient address...")

        try:
            balance_trx = wallet.get_balance(address_recipient)
        except AddressNotFound:
            balance_trx = None
        balance = wallet.get_balance(address_recipient, token)

        tronscan = TronscanClient()
        transactions = tronscan.get_trc20_and_trc721_transfers(from_address=address_sender,
                                                               contract_address=token.address,
                                                               to_address=address_recipient)
        history = []
        tronscan_risky = None
        for t in transactions['token_transfers']:
            if t['to_address'] == address_recipient:
                history.append(
                    f"{(datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(t['block_ts'] / 1000)).days} days ago({datetime.datetime.fromtimestamp(t['block_ts'] / 1000)}) sent {int(t['quant']) / 10 ** token.decimals} {token.symbol} https://tronscan.io/#/transaction/{t['transaction_id']}")

        if address_recipient in transactions['normalAddressInfo'] and \
                transactions['normalAddressInfo'][address_recipient][
                    'risk']:
            # print("!!! Tronscan marked this address as risky !!!")
            tronscan_risky = True

        if balance_trx is None and balance:
            balance_trx = 0.0
        if balance or balance_trx:
            print(f"OK Recipient balance: {int(balance)} {token.symbol}, {int(balance_trx)} TRX")
        else:
            print(
                f"WARN Recipient balance: {int(balance)} {token.symbol}, {int(balance_trx) if balance_trx else balance_trx} TRX")

        # print(f"Recipient info:\n\tBalance: {int(balance)} {token.symbol}, {int(balance_trx)} TRX")
        if tronscan_risky:
            print(f"WARN Tronscan marked recipient as risky: YES")
        # else:
        #     print(f"OK Tronscan marked as risky: NO")

        print(f"\tAML check: NOT IMPLEMENTED")
        if history:
            print(f"OK Found transaction history:")
            for r in history[:3]:
                print(f"\t\t{r}")
        else:
            print(f"WARN No transactions found")

        print()
        print("Calculating resources required to send token...")

        # contract = wallet.create_contract(TronTokens.USDT.address)
        estimate_resources = wallet.estimate(token, 'transfer',
                                             amount=amount,
                                             owner_address=address_sender,
                                             address_recipient=address_recipient,
                                             )

        print(
            f"Energy required: {estimate_resources['energy_required']}. Available: {estimate_resources['energy_available']}")
        print(
            f"Bandwidth required: {estimate_resources['bandwidth_required']}. Available: {estimate_resources['bandwidth_available']}")
        if estimate_resources['bandwidth_required'] > estimate_resources['bandwidth_available']:
            print(f"WARN Not enough bandwidth to send token")

        # print(f"Energy used: {estimate_resources['energy_used']} ")
        # print(f"Energy limit: {estimate_resources['energy_limit']} ")
        # print(f"Energy available: {estimate_resources['energy_available']} ")
        # print(f"Energy lack: {estimate_resources['energy_lack']} ")
        print(f"Energy fee: {estimate_resources['energy_fee'] / 10 ** Networks.Tron.decimals} ")
        print(f"Bandwidth fee: {estimate_resources['bandwidth_fee']} ")
        print(f"Total fee: {estimate_resources['total_fee'] / 10 ** Networks.Tron.decimals} ")
        if dry_run is False:
            if estimate_resources['energy_lack'] > 0:
                # print()
                # answer = input("Rent energy to send token?[Y/n]")
                # if answer.lower() == 'n':
                #     return

                if estimate_resources['energy_required'] > 32000:
                    energy_required = 65000
                else:
                    energy_required = 32000
                energy_required = estimate_resources['energy_required']
                rent_amount = self.get_energy_price(estimate_resources['energy_required'])

                answer = input(f"Rent {energy_required} energy for {rent_amount} TRX from ITRX.IO?[Y/n]")
                if answer.lower == 'n':
                    return

                order_id = self.rent_energy(address_sender, energy_required)
                if not order_id:
                    print("Failed renting energy")
                    return

                print("Waiting for energy...")
                while True:
                    time.sleep(5)
                    energy_available = wallet.adapter.get_energy(address_sender)
                    print(f"Energy at {address_sender}: {energy_available}")
                    if energy_available >= energy_required:
                        break

                #
                # # trongas.ai
                # rent_amount = 2.85
                # rent_address = 'TXk5rGgGsycAXYtz9RMddZY2geMxr5oDS4'
                # # filename = f'data/qr_{rent_address}_{rent_amount}.png'
                # # data = f'tron:{rent_address}?amount={rent_amount}'
                #
                # filename = self.generate_qr_code(rent_address, rent_amount, token=None)
                # print(f"Open {address_sender} and pay for renting energy using qr code {filename}")
                # answer = input("Press [Enter] if you paid for energy")
                # if answer == '':
                #     print("Waiting for energy...")
                #     while True:
                #         time.sleep(5)
                #         energy_available = wallet.adapter.get_energy(address_sender)
                #         print(f"Energy at {address_sender}: {energy_available}")
                #         if energy_available >= energy_required:
                #             break
                # else:
                #     print("Renting energy canceled")
                #     return

            print("OK Sender has energy. Sending token...")
            filename = self.generate_qr_code(address_recipient, amount, token=token)
            print(f"> Open {address_sender} and send {amount} {token.symbol} using qr code {filename}")

            # print(estimate_resources)

            # a = wallet.client.get_fee_limit()
            # a = wallet.client.get_account_resource(address_sender)
            # print()
            # account_info = wallet.client.get_account_resource(address_sender)
            #
            # # https://github.com/Polygant/OpenCEX-backend/blob/d27cd7cf7c0a72bb25442ae7eae031a3f8b16389/cryptocoins/coins/trx/utils.py#L45
            # # print(f"Balance: {account.balance}")
            # # print(f"Energy: {account.energy}")
            # # required_energy = energy_data['energy_used']
            # energy_limit = account_info.get('EnergyLimit', 0)
            # energy_used = account_info.get('EnergyUsed', 0)
            #
            # energy_fee = get_energy_fee(required_energy, energy_limit, energy_used)
            # bandwidth_fee = get_bandwidth_fee(tx, owner_address)

            # return math.ceil((bandwidth_fee + energy_fee) * TRC20_FEE_LIMIT_FACTOR)
        print()

# Snakewallet

Multichain python wallet 

## Installation

To install the package, use pip:

```sh
pip install git+https://github.com/Romamo/snakewallet.git
```
Or
```sh
pip install git+https://github.com/Romamo/snakewallet.git#egg=snakewallet[solana]
pip install git+https://github.com/Romamo/snakewallet.git#egg=snakewallet[ethereum]
pip install git+https://github.com/Romamo/snakewallet.git#egg=snakewallet[tron]
```

## Usage

```python
from wallet import Wallet
from wallet.networks import Networks

address_key = "0x..."
wallet = Wallet(network=Networks.Ethereum)
account = wallet.create_account(address_key)
balance = wallet.get_balance(address_key)
print(balance)

address_tron = "T..."
wallet = Wallet(network=Networks.Tron)
balance = wallet.get_balance(address_tron)
print(balance)
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
```

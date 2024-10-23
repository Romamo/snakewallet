from wallet.networks import TronTokens

from wallet.actions.send_tron import SendTronAction

action = SendTronAction()
response = action.send('sender address', 'recipient address', 1000, TronTokens.USDT)

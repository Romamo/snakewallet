from typing import NamedTuple

from wallet.types import Network, URI

from .sepolia import SepoliaTokens
from .tron import TronTokens

__all__ = ['Networks', 'SepoliaTokens', 'TronTokens']


class Networks(NamedTuple):
    Ethereum = Network(name='Ethereum',
                       rpc=URI('https://eth.llamarpc.com'),
                       chain_id=1,
                       symbol='ETH',
                       adapter='w3'
                       )
    Tron = Network(name='TRON',
                       rpc=URI('https://api.trongrid.io'),
                       decimals=6,
                       # chain_id=1,
                       symbol='TRX',
                       adapter='tron',
                       coin_id=195
                       )
    BNB = Network(name='Binance Smart Chain',
                  rpc=URI('https://bsc-dataseed.binance.org/'),
                  chain_id=56,
                  symbol='BNB',
                  adapter='w3',
                  decimals=18,
                  url='https://www.binance.org/en/smartChain',
                  explorer='https://bscscan.com/',
                  faucet='https://testnet.binance.org/faucet-smart',
                  pancakeswap_id='bsc'
                  )
    Arbitrum = Network(name='Arbitrum',
                          rpc=URI('https://arb1.arbitrum.io/rpc'),
                          chain_id=42161,
                          symbol='ETH',
                          adapter='w3',
                          url='https://offchainlabs.com/',
                          explorer='https://arbiscan.io/',
                       pancakeswap_id='arb'
                          )
    Linea = Network(name='Linea',
                    rpc=URI('https://rpc.linea.io'),
                    chain_id=59144,
                    symbol='ETH',
                    decimals=18,
                    url='https://linea.io',
                    explorer='https://explorer.linea.io/',
                    adapter='w3',
                    pancakeswap_id='linea'
                    )

    Solana = Network(name='Solana',
                     rpc=URI('https://api.mainnet-beta.solana.com'),
                     adapter='solana')

    # Testnets
    Holesky = Network(name='Holesky',
                      rpc=[URI('https://ethereum-holesky-rpc.publicnode.com/'), URI('https://rpc.holesky.ethpandaops.io')],
                      chain_id=17000,
                      symbol='ETH',
                      decimals=18,
                      url='https://github.com/eth-clients/holesky',
                      explorer='https://holesky.etherscan.io/',
                      faucet='https://cloud.google.com/application/web3/faucet/ethereum/holesky',
                      testnet=True,
                      adapter='w3'
                      )

    Sepolia = Network(name='Sepolia',
                      rpc=[URI('https://rpc.sepolia.org'), URI('https://rpc.sepolia.dev')],
                      chain_id=11155111,
                      symbol='ETH',
                      decimals=18,
                      url='https://github.com/eth-clients/sepolia',
                      faucet='https://cloud.google.com/application/web3/faucet/ethereum/sepolia',
                      testnet=True,
                      adapter='w3'
                      )

    Sonic = Network(name='Sonic Devnet',
                    rpc=URI('https://devnet.sonic.game'),
                    testnet=True,
                    adapter='solana'
                    )

    Photonchain = Network(name='Photon Aurora Testnet',
                          rpc=URI('https://rpc-test2.photonchain.io'),
                          chain_id=55551,
                          symbol='PTON',
                          testnet=True,
                          adapter='w3',
                          url='https://docs.photonchain.io/testnet/aurora-testnet-guide',
                          explorer='https://testnet2.photonchain.io'
                          )

    Plume_testnet = Network(name='Plume Testnet',
                          rpc=URI('https://testnet-rpc.plumenetwork.xyz/http'),
                          chain_id=161221135,
                          symbol='ETH',
                          block_explorer='https://testnet-explorer.plumenetwork.xyz/',
                          testnet=True,
                          adapter='w3',
                          url='https://docs.photonchain.io/testnet/aurora-testnet-guide'
                          )
    Movement_evm_testnet = Network(
        name='Movement EVM Testnet',
        rpc=URI('https://mevm.devnet.imola.movementlabs.xyz'),
        chain_id=30732,
        symbol='MOVE',
        # block_explorer='https://testnet-explorer.movement.network/',
        testnet=True,
        adapter='w3',
        url='https://explorer.movementlabs.xyz'
        )
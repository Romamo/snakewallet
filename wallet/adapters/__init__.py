import importlib

# from wallet.adapters.w3 import W3Adapter

__all__ = ['create_adapter']


def create_adapter(network=None, rpc: str = None, chain: int = None, **kwargs):
    module = importlib.import_module(f"wallet.adapters.{network.adapter}")
    return module.create_adapter(network, rpc, chain, **kwargs)

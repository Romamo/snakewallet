from wallet.models import Contract


class AdapterBase:
    @staticmethod
    def create_contract(contract: str, abi: list = None):
        return Contract(address=contract, abi=abi)

class ClientBase:
    _ENDPOINT = None
    _DECIMALS = 6

    def __init__(self):
        self._client = None

    def generate_wallet(self):
        raise NotImplementedError()

    def create_wallet(self, private_key):
        raise NotImplementedError()

    def get_balance(self, address: str):
        raise NotImplementedError()

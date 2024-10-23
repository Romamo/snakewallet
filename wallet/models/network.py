from pydantic import BaseModel


class Network(BaseModel):
    adapter: str
    rpc: str
    chain: int

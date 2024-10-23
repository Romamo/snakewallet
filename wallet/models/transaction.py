from pydantic import BaseModel


class Transaction(BaseModel):
    address: str

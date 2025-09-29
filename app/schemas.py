from pydantic import BaseModel


class DriverParams(BaseModel):
    phoneNumber : str
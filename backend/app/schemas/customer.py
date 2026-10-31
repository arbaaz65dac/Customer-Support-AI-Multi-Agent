from pydantic import BaseModel, ConfigDict, EmailStr, Field

from typing import Literal


# Input schema: accepts a password only during registration.
class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


# Output schema: never returns password_hash.
class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: Literal["admin", "customer"] = "customer"


class AdminCustomerResponse(CustomerResponse):
    role: Literal["admin", "customer"]
    active: bool


class CustomerActiveUpdate(BaseModel):
    active: bool
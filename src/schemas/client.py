from pydantic import BaseModel, ConfigDict
from typing import Optional
from src.schemas.user import UserResponse

class ClientBase(BaseModel):
    score: Optional[int] = None

class ClientCreate(ClientBase):
    user_id: int

class ClientResponse(ClientBase):
    id: int
    user_id: int
    blocked: bool
    user: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)

class SyncClientSchema(BaseModel):
    telegram_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = "client"
    lang: Optional[str] = "uz"
    client_id: Optional[int] = None
    referred_by_id: Optional[int] = None

class ClientRequestStatusUpdate(BaseModel):
    status: str

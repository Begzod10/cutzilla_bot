from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    login: str
    password: str
    telegram_id: Optional[int] = None

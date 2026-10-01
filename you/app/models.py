from typing import Optional
from pydantic import BaseModel


class Facts(BaseModel):
    """The only things Gemini is allowed to pull out of her speech."""
    is_pregnant_or_new_mother: Optional[bool] = None
    living_children: Optional[int] = None
    has_own_bank_account: Optional[bool] = None


class Heard(BaseModel):
    facts: Facts
    wants_repeat: bool = False
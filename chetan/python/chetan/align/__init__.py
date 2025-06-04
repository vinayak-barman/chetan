from typing import Literal
from pydantic import BaseModel

class Rule(BaseModel):
    id: str
    description: str
    
    nature: str = Literal["embrace", "avoid"]
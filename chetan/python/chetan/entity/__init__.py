from typing import List, Optional, Type
from pydantic import BaseModel

class Entity(BaseModel):
    id: str
    name: Optional[str] = None
    description: str
    

class Connection(BaseModel):
    source: Entity
    target: Entity

    description: Optional[str] = None

    structured_protocols: List[Type[BaseModel]] = []
    

    
# from typing import Dict, List
# from pydantic import BaseModel

# from chetan.align import Rule

# from chetan.agent import Agent
# from chetan.entity.user import Human

# class Entity:
#     pass

# class Persona(BaseModel):
#     id: str
#     role: str
#     description: str
#     rules: List[Rule]
    
# class SystemEntities():
#     agents: Dict[str, Agent] = {}
#     humans: Dict[str, Human] = {}
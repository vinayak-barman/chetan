from abc import ABC, abstractmethod
from typing import Dict, Self
from chetan.entity import Connection

class System(ABC):
    connections: Dict[str, Connection] = {}
    
    def __init__(self, mgr):
        self.mgr = mgr
        
    @abstractmethod
    def create(self, *args, **kwargs) -> Self:
        ...
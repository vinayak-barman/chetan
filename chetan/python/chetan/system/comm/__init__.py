from typing import Optional
from chetan import CommunicationManager
from chetan.types.json import JsonSchema
from chetan.agent.module import AgentLoopModule
from chetan.tools import toolfn


class CommunicationModule(AgentLoopModule):
    comm_mgr: CommunicationManager
    
    def __init__(self, comm_mgr: CommunicationManager):
        super().__init__()
        self.comm_mgr = comm_mgr
        
    def setup(self):
        pass

    @toolfn
    def message(self, entity: str, message: str):
        pass

    @toolfn
    def ask(self, entity: str, queryId: str, query: str, timeout: int = 30):
        pass
    
    @toolfn
    def reply(self, queryId: str, content: str):
        pass
    
    @toolfn
    def ask_structured(self, entity: str, queryId: str, query: str, schema: JsonSchema, timeout: int = 30):
        pass
    
    @toolfn
    def reply_structured(self, queryId: str, object: dict, message: Optional[str]):
        pass
    
    @toolfn
    def send_structured_object(self, entity: str, protocol: str, object: dict):
        pass

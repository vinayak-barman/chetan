from chetan._chetanbase import ChetanbaseClient

from typing import Dict, Optional

from chetan import CommunicationManager
from chetan.agent import AgentLoop
from chetan.agent import Agent
from chetan.entity import Entity
from chetan.entity.user import User
from chetan.lm import LanguageModel
from chetan.system import System

from chetan.tools.toolbox import Toolbox
from chetan.types.context.agent.iteration import AgentContext
from tqdm import tqdm

class IdDict[T](Dict[str, T]):
    def __init__(self, mgr: "SessionManager", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mgr = mgr

    def add(self, *items):
        for item in items:
            try:
                if isinstance(item, Agent):
                    if item._loop is None:
                        item._loop = self.mgr.agentloop.get("default").clone()

                    if item._lm is None:
                        item._lm = self.mgr.lm.get("default").clone()

                    item._loop.lm = item._lm
                    
                    item.context = AgentContext(_lm=item._lm)
                    
                    item.apply_system_prompt()
                    

                self[item.id] = item

            except KeyError:
                raise ValueError("The item does not have an ID")


class SessionManager:
    client: Optional[ChetanbaseClient]
    comm_mgr: CommunicationManager

    lm: Dict[str, LanguageModel] = {}
    agentloop: Dict[str, AgentLoop] = {}

    tools: Toolbox = Toolbox()
    agents: IdDict[Agent]
    users: IdDict[User]

    system: System

    def __init__(self, client: ChetanbaseClient = None):
        self.client = client

        self.agents = IdDict[Agent](self)
        self.users = IdDict[User](self)

    def setup(self):
        for mod in tqdm(
            self.agentloop["default"].modules.values(), desc="Setting up modules"
        ):
            if hasattr(mod, "setup"):
                mod.setup()

    def get_entity(self, entity_id: str) -> Entity:
        if entity_id in self.agents:
            return self.agents[entity_id]
        elif entity_id in self.users:
            return self.users[entity_id]
        else:
            raise ValueError(f"Entity with ID {entity_id} not found.")

from typing import Dict, Literal
from chetan import CommunicationManager
from chetan.entity import Connection
from chetan.entity.user import User
from chetan.orchestra import Orchestrator

from asq import query
from chetan.types.json import JsonSchema

UserResponseAcess = Literal[
    "TARGET_ONLY", # Only the target agent's response is returned
    "TARGET_TO_RELATED", # If the target agent interacts with other entities, their responses are also returned
    "ALL" # All communication items in the system are returned
]

UserResponseDetails = Literal[
    "COMMUNICATION", # Only the communication items are returned
    "CONTEXT", # The entire agent system context is returned
]

class ActiveConnection(Connection):
    comm_mgr: CommunicationManager

    def __init__(self, comm_mgr, **kwargs):
        super().__init__(**kwargs)
        self.comm_mgr = comm_mgr

    def message(self, message: str):
        pass

    def ask(self, queryId: str, query: str, timeout: int = 30):
        pass

    def ask_structured(
        self, queryId: str, query: str, schema: JsonSchema, timeout: int = 30
    ):
        pass

    def send_structured_object(self, protocol: str, object: dict):
        pass


class UserWithConnections(User):
    connections: Dict[str, Connection] = {}
    comm_mgr: CommunicationManager

    def to(self, id: str) -> ActiveConnection:
        """Create a connection to another entity."""

        target = self.connections.get(f"{self.id}-{id}")

        if target:
            return ActiveConnection(comm_mgr=self.comm_mgr, **target.__dict__)
        else:
            raise ValueError(f"Connection to entity with ID {id} not found.")


class ChatOrchestrator(Orchestrator):
    def user(self, id: str) -> UserWithConnections:
        """Get the user entity by ID."""

        user = self.mgr.get_entity(id)
        if isinstance(user, User):
            connections = dict(
                query(list(self.mgr.system.connections.items()))
                .where(lambda c: c[1].source.id == id)
                .to_list()
            )

            return UserWithConnections(
                **user.__dict__, connections=connections, comm_mgr=self.mgr.comm_mgr
            )
        else:
            raise ValueError(f"Entity with ID {id} is not a User.")

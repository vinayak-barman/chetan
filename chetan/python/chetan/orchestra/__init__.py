from chetan._mgr import SessionManager
from chetan.system.comm import CommunicationModule


class Orchestrator:
    def __init__(self, mgr: SessionManager, use_communication: bool = True):
        self.mgr = mgr

        if use_communication:
            for loop in self.mgr.agentloop.values():
                loop.use(CommunicationModule())

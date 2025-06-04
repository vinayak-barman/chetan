from chetan.agent.module import AgentLoopModule


class ToolRecommenderModule(AgentLoopModule):
    def __init__(self, embedder: str):
        super().__init__()
    
    def setup(self):
        # TODO: Setup tool recommender embedding model
        pass
    
    # TODO: Add epilogue memory snapshots

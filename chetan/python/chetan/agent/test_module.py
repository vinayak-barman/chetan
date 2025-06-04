from .module import AgentLoopModule, prologue, epilogue

def test_prologue_fn():
    @prologue
    def sample_prologue():
        return "This is a prologue function."

    assert sample_prologue() == "This is a prologue function."
    assert hasattr(sample_prologue, "__agentloop_item_type__")
    assert sample_prologue.__agentloop_item_type__ == "prologue"
    
def test_epilogue_fn():
    @epilogue
    def sample_epilogue():
        return "This is an epilogue function."

    assert sample_epilogue() == "This is an epilogue function."
    assert hasattr(sample_epilogue, "__agentloop_item_type__")
    assert sample_epilogue.__agentloop_item_type__ == "epilogue"
    
class TestAgentLoopModule(AgentLoopModule):
    @prologue
    def prologue_method(self):
        return "Prologue method executed."

    @epilogue
    def epilogue_method(self):
        return "Epilogue method executed."
    
def test_agent_loop_module():
    module = TestAgentLoopModule()
    assert "prologue_method" in module.functions["prologue"].keys()
    assert "epilogue_method" in module.functions["epilogue"].keys()

    assert module.prologue_method() == "Prologue method executed."
    assert module.epilogue_method() == "Epilogue method executed."
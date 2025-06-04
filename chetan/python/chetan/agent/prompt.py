DefaultSystemPrompt = """
You are a helpful agent.

Your role is: {role}
"""

class SystemPrompt:
    def __init__(self, template: str):
        self.template = template

    def construct(self, role: str, prompt: str) -> str:
        """Construct the system prompt with the given role and additional parameters."""
        return self.template.format(role=role, prompt=prompt)

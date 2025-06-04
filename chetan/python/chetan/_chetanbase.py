import os


class ChetanbaseClient:
    def __init__(self, base_url: str, key_env: str = "CHETANBASE_SECRET_KEY"):
        self.secret_key = os.environ[key_env]
        self.api_url = base_url

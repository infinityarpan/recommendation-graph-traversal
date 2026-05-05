import sys
import types

neo4j_stub = types.ModuleType("neo4j")
neo4j_stub.GraphDatabase = types.SimpleNamespace(driver=lambda *args, **kwargs: None)
sys.modules.setdefault("neo4j", neo4j_stub)

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)


class FakeTx:
    def __init__(self, records=None):
        self.records = records or []
        self.calls = []

    def run(self, query, **params):
        self.calls.append((query, params))
        return self.records


class FakeSession:
    def __init__(self, records=None, error=None):
        self.records = records or []
        self.error = error
        self.closed = False
        self.tx = FakeTx(records=self.records)

    def execute_read(self, callback, *args):
        if self.error:
            raise self.error
        return callback(self.tx, *args)

    def execute_write(self, callback, *args):
        if self.error:
            raise self.error
        return callback(self.tx, *args)

    def close(self):
        self.closed = True

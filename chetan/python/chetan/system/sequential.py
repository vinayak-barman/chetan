from chetan.system import Connection, System


class SequentialSystem(System):
    def create(self, *names):
        for i in range(len(names) - 1):
            source = self.mgr.find_entity(names[i])
            target = self.mgr.find_entity(names[i + 1])

            conn = Connection(source=source, target=target)
            conn.description = f"{source.id} -> {target.id}"
            self.connections[f"{conn.source.id}-{conn.target.id}"] = (conn)
            
        return self

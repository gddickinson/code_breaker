"""A small sqlite3-style wrapper over apsw (Anaconda's sqlite3 module is broken on this Mac)."""
import apsw


class Row(tuple):
    """A result row readable by position or by column name."""

    def __new__(cls, names, values):
        row = super().__new__(cls, values)
        row.names = names
        return row

    def __getitem__(self, key):
        return tuple.__getitem__(self, self.names.index(key) if isinstance(key, str) else key)

    def keys(self):
        return list(self.names)

    def as_dict(self):
        return dict(zip(self.names, self))


class Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def __iter__(self):
        return iter(self.rows)


class Connection:
    """Autocommit connection: each statement is durable, and commit() is a no-op."""

    def __init__(self, path, timeout=30):
        self.db = apsw.Connection(str(path))
        self.db.set_busy_timeout(int(timeout * 1000))

    def execute(self, sql, params=()):
        cur = self.db.cursor().execute(sql, params)
        try:
            names = [d[0] for d in cur.get_description()]
        except apsw.ExecutionCompleteError:
            return Result([])
        return Result([Row(names, r) for r in cur])

    def executescript(self, sql):
        for _ in self.db.cursor().execute(sql):
            pass

    def commit(self):
        return None

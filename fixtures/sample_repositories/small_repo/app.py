import sqlite3


def find_user(connection: sqlite3.Connection, username: str):
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return connection.execute(query).fetchone()


def load_settings(path: str) -> str:
    try:
        return open(path, encoding="utf-8").read()
    except OSError:
        pass
    return ""


def page(items: list[str], index: int) -> str:
    if index > len(items):
        raise IndexError(index)
    return items[index]

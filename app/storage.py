import json
import os
import sqlite3
from contextlib import closing
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SQLite:
    def connect(self):
        return closing(sqlite3.connect(os.getenv("SQLITE_PATH") or ROOT / "wonder.sqlite3"))

    def __init__(self):
        with self.connect() as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS documents (collection TEXT, id TEXT, body TEXT, PRIMARY KEY(collection,id))")

    def list(self, collection):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute(
                "SELECT body FROM documents WHERE collection=?", (collection,)
            )]

    def get(self, collection, key):
        with self.connect() as db:
            row = db.execute("SELECT body FROM documents WHERE collection=? AND id=?", (collection, key)).fetchone()
            return json.loads(row[0]) if row else None

    def create(self, collection, item):
        with self.connect() as db, db:
            return bool(db.execute("INSERT OR IGNORE INTO documents VALUES (?,?,?)",
                                   (collection, item["id"], json.dumps(item))).rowcount)

    def update(self, collection, item):
        with self.connect() as db, db:
            return bool(db.execute("UPDATE documents SET body=? WHERE collection=? AND id=?",
                                   (json.dumps(item), collection, item["id"])).rowcount)

    def delete(self, collection, key):
        with self.connect() as db, db:
            return bool(db.execute("DELETE FROM documents WHERE collection=? AND id=?", (collection, key)).rowcount)


class Firestore:
    def __init__(self):
        import firebase_admin
        from firebase_admin import credentials, firestore

        account = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"])
        app = firebase_admin.initialize_app(credentials.Certificate(account))
        self.db = firestore.client(app)

    def ref(self, collection, key):
        return self.db.collection(collection).document(key)

    def list(self, collection):
        return [doc.to_dict() for doc in self.db.collection(collection).stream()]

    def get(self, collection, key):
        return self.ref(collection, key).get().to_dict()

    def create(self, collection, item):
        from google.api_core.exceptions import AlreadyExists

        try:
            self.ref(collection, item["id"]).create(item)
        except AlreadyExists:
            return False
        return True

    def update(self, collection, item):
        from google.api_core.exceptions import NotFound

        try:
            self.ref(collection, item["id"]).update(item)
        except NotFound:
            return False
        return True

    def delete(self, collection, key):
        from google.api_core.exceptions import FailedPrecondition, NotFound

        ref = self.ref(collection, key)
        snapshot = ref.get()
        if not snapshot.exists:
            return False
        try:
            ref.delete(option=self.db.write_option(last_update_time=snapshot.update_time))
        except (FailedPrecondition, NotFound):
            return False
        return True


@lru_cache
def store():
    return {"sqlite": SQLite, "firestore": Firestore}[os.getenv("STORAGE", "sqlite")]()

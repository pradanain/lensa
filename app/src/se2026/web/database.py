import hashlib
import sqlite3
from contextlib import contextmanager


@contextmanager
def census_connection(settings):
    connection = sqlite3.connect(settings.census_db.as_uri() + "?mode=ro", uri=True, timeout=20)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA busy_timeout=20000")
    connection.execute("BEGIN")
    try:
        yield connection
    finally:
        connection.close()


class AppDatabase:
    def __init__(self, settings):
        self.settings = settings
        settings.app_db.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','analyst_detail','aggregate_viewer')),
                    active INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions(
                    token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),
                    csrf TEXT NOT NULL,expires_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS audit(
                    id INTEGER PRIMARY KEY,occurred_at INTEGER NOT NULL,user_id INTEGER,
                    action TEXT NOT NULL,outcome TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS session_commitments(
                    token_hash TEXT PRIMARY KEY REFERENCES sessions(token_hash) ON DELETE CASCADE,
                    version TEXT NOT NULL,accepted_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS login_attempts(
                    client_hash TEXT PRIMARY KEY,failures INTEGER NOT NULL,window_start INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS cache_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS directory_rows(
                    id INTEGER PRIMARY KEY,scope TEXT NOT NULL,source TEXT NOT NULL,
                    record_key TEXT UNIQUE NOT NULL,assignment_id TEXT NOT NULL,version TEXT,index1 TEXT,
                    title TEXT,status TEXT,status_label TEXT,kecamatan TEXT,desa TEXT,sls TEXT,subsls TEXT,
                    kecamatan_label TEXT,desa_label TEXT,kbli TEXT,kategori TEXT,kind TEXT,kbli_state TEXT);
                CREATE INDEX IF NOT EXISTS directory_scope ON directory_rows(scope,source,id);
                CREATE INDEX IF NOT EXISTS directory_geo ON directory_rows(scope,kecamatan,desa,sls);
                CREATE INDEX IF NOT EXISTS directory_kbli ON directory_rows(scope,source,kbli,kategori);
                CREATE INDEX IF NOT EXISTS directory_assignment ON directory_rows(assignment_id,scope);
                CREATE VIRTUAL TABLE IF NOT EXISTS directory_fts USING fts5(search_text,restricted_text,tokenize='unicode61');
            """)
            # Account state and disposable search-cache fields only; census stays read-only.
            con.execute("BEGIN IMMEDIATE")
            user_columns = {row[1] for row in con.execute("PRAGMA table_info(users)")}
            if "must_change_password" not in user_columns:
                con.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 1 CHECK(must_change_password IN (0,1))")
            columns = {row[1] for row in con.execute("PRAGMA table_info(directory_rows)")}
            if "subsls" not in columns:
                con.execute("ALTER TABLE directory_rows ADD COLUMN subsls TEXT")
            for column in ("status_rank", "score_admin", "score_viewer"):
                if column not in columns:
                    con.execute("ALTER TABLE directory_rows ADD COLUMN " + column + " INTEGER")
            for access in ("admin", "viewer"):
                con.execute(
                    "CREATE INDEX IF NOT EXISTS directory_order_" + access +
                    " ON directory_rows(scope,source,status_rank,score_" + access +
                    " DESC,title COLLATE NOCASE,assignment_id,version,index1,id)"
                )
            con.execute("""CREATE TRIGGER IF NOT EXISTS directory_order_changed
                AFTER UPDATE OF scope,source,record_key,assignment_id,version,index1,title,status,
                    desa,desa_label,sls,subsls,kbli,kategori ON directory_rows
                BEGIN DELETE FROM cache_meta
                    WHERE key IN ('directory_order:' || OLD.scope,'directory_order:' || NEW.scope);
                END""")
            con.execute(
                "CREATE INDEX IF NOT EXISTS directory_subsls ON directory_rows(scope,source,subsls)"
            )

    @contextmanager
    def connection(self):
        con = sqlite3.connect(self.settings.app_db, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=30000")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def audit(self, user_id, action, outcome="OK"):
        import time

        with self.connection() as con:
            con.execute(
                "INSERT INTO audit(occurred_at,user_id,action,outcome) VALUES(?,?,?,?)",
                (int(time.time()), user_id, action, outcome),
            )


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

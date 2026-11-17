import sqlite3
from contextlib import contextmanager
from codecompass.app.evidence_store import EvidenceStore

class ProductStore:
    def __init__(self,path):
        self.evidence=EvidenceStore(path)
        self.path=path
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS product_transfers(reference_id TEXT PRIMARY KEY,session_id TEXT NOT NULL,user_id TEXT NOT NULL,source_project TEXT NOT NULL,target_project TEXT NOT NULL,concept_id TEXT NOT NULL,source_evidence_ids_json TEXT NOT NULL,target_item_id TEXT NOT NULL,referenced_at TEXT NOT NULL,source_sessions_json TEXT NOT NULL,UNIQUE(session_id,concept_id));
            CREATE TABLE IF NOT EXISTS product_issue_snapshots(repo TEXT PRIMARY KEY,attempted_at TEXT NOT NULL,snapshot_json TEXT,error TEXT);
            CREATE TABLE IF NOT EXISTS product_users(user_id TEXT PRIMARY KEY,actor TEXT NOT NULL,created_at TEXT NOT NULL,preferences_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS product_sessions(session_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,task_id TEXT NOT NULL,status TEXT NOT NULL,phase TEXT NOT NULL,revision INTEGER NOT NULL,schema_version TEXT NOT NULL,content_version TEXT NOT NULL,planner_version TEXT NOT NULL,state_json TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS one_active ON product_sessions(user_id) WHERE status='active';
            CREATE TABLE IF NOT EXISTS product_actions(session_id TEXT,request_id TEXT,payload_hash TEXT,response_json TEXT,created_at TEXT,PRIMARY KEY(session_id,request_id));
            CREATE TABLE IF NOT EXISTS product_drafts(session_id TEXT,kind TEXT,content_json TEXT,revision INTEGER,updated_at TEXT,PRIMARY KEY(session_id,kind));
            CREATE TABLE IF NOT EXISTS product_answers(seq INTEGER PRIMARY KEY,session_id TEXT,item_id TEXT,value_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS product_exposures(user_id TEXT,item_id TEXT,assisted INTEGER NOT NULL DEFAULT 0,answered INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(user_id,item_id));
            CREATE TABLE IF NOT EXISTS product_messages(session_id TEXT,request_id TEXT,payload_hash TEXT,unit_id TEXT,message TEXT,response_json TEXT,status TEXT NOT NULL,created_at TEXT,PRIMARY KEY(session_id,request_id));
            CREATE TABLE IF NOT EXISTS product_submissions(submission_id TEXT PRIMARY KEY,session_id TEXT,request_id TEXT,payload_hash TEXT,status TEXT NOT NULL,result_json TEXT,created_at TEXT,UNIQUE(session_id,request_id));
            """)
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=15);db.row_factory=sqlite3.Row
        try:
            with db: yield db
        finally: db.close()

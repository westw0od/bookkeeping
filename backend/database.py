import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL.startswith("mysql+pymysql://"):
    raise RuntimeError("请在 backend/.env 中配置 DATABASE_URL=mysql+pymysql://用户名:密码@127.0.0.1:3306/bookkeeping?charset=utf8mb4")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=1800, hide_parameters=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def get_db():
    with SessionLocal() as session:
        yield session

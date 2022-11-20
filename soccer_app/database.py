from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

db_conn = os.environ['DB_CONN']
schema = os.environ.get('SCHEMA')

SQLALCHEMY_DATABASE_URL = db_conn

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

metadata_obj = MetaData(schema=schema)
Base = declarative_base(metadata=metadata_obj)

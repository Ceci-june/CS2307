from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.sql import text


class PostgresConnector:
    def __init__(self, config: dict):
        self.config = config
        self.engine = None
        self.connection_string = None
        self.dbname = None
        self.port = None
        self.host = None
        self.password = None
        self.username = None

    def start(self):
        self.username, self.password, self.host, self.port, self.dbname, statement_timeout = self.config["username_db"], \
            self.config[
                "password_db"], \
            self.config["host_db"], self.config["port_db"], self.config["database"], 100
        self.connection_string = f'postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.dbname}'
        self.engine = create_engine(self.connection_string, pool_size=5000, max_overflow=12000)

    def execute_raw_query(self, raw_query: str, **kwargs):
        try:
            query = text(raw_query)
            rr = self.engine.execute(query, **kwargs).fetchall()
            if len(rr) == 0:
                return None
            res = [tuple(i) for i in rr]
            return res
        except Exception as e:
            logger.error(f"execute_raw_query ex: {e}")
            return None

    def stop(self):
        self.engine.dispose()

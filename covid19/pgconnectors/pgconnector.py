from abc import ABC, abstractmethod
import psycopg2


class DBError(Exception):
    pass


class PostgresConnector(ABC):
    def __init__(self, host, port, database, user, password):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.first = True

    def connect(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password
        )

    def _init_db(self):
        if self.first:
            self._build_db()
            self.first = False

    @abstractmethod
    def _build_db(self):
        """Build the necessary DB elements"""

    @abstractmethod
    def _drop_db(self):
        """Remove the necessary DB elements"""

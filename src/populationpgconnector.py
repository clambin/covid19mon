import logging
import psycopg2
from src.pgconnector import PostgresConnector


class PopulationPGConnector(PostgresConnector):
    def __init__(self, host, port, database, user, password):
        super().__init__(host, port, database, user, password)
        self.first = True
        self.reported = {}

    def _build_db(self):
        conn = None
        try:
            conn = self.connect()
            curr = conn.cursor()
            curr.execute("""
                CREATE TABLE IF NOT EXISTS population (
                country_code TEXT PRIMARY KEY,
                population NUMERIC
                );
            """)
            curr.close()
            conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            logging.critical(f'Failed to create table: {error}')
        finally:
            if conn:
                conn.close()

    def _drop_db(self):
        conn = None
        try:
            conn = self.connect()
            cur = conn.cursor()
            cur.execute("""DROP TABLE IF EXISTS population""")
            conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            logging.critical(f'Could not drop tables: {error}')
        finally:
            if conn:
                conn.close()

    def add(self, records):
        self._init_db()
        conn = None
        try:
            conn = self.connect()
            curr = conn.cursor()
            curr.executemany("""
                INSERT INTO population(country_code, population)
                VALUES(%s, %s)
                ON CONFLICT (country_code)
                DO UPDATE SET population = EXCLUDED.population
                """, list(records.items()))
            curr.close()
            conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            logging.critical(f'Failed to insert data: {error}')
        finally:
            if conn:
                conn.close()

    def list(self):
        conn = None
        rows = dict()
        try:
            conn = self.connect()
            cur = conn.cursor()
            cur.execute("""
                SELECT country_code, population FROM population
            """)
            for fetched in cur.fetchall():
                rows[fetched[0]] = fetched[1]
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            logging.critical(f'Failed to get data: {error}')
        finally:
            if conn:
                conn.close()
        return rows

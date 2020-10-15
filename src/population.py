import logging
import psycopg2
from pimetrics.probe import APIProbe
from src.countries import country_codes
from src.pgconnector import PostgresConnector


class PopulationDBConnector(PostgresConnector):
    def __init__(self, host, port, database, user, password):
        super().__init__(host, port, database, user, password)
        self.first = True
        self.reported = {}

    def _init_db(self):
        if self.first:
            self._build_db()
            self.first = False

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


class PopulationProbe(APIProbe):
    def __init__(self, api_key, dbconnector=None):
        super().__init__('https://ajayakv-rest-countries-v1.p.rapidapi.com/')
        self.headers = {
            'x-rapidapi-host': "ajayakv-rest-countries-v1.p.rapidapi.com",
            'x-rapidapi-key': api_key
        }
        self.population = dict()
        self.dbconnector = dbconnector

    def report(self, output):
        self.dbconnector.add(output)

    def process(self, output):
        codes = country_codes.values()
        bad_codes = [key for key in output.keys() if key not in codes]
        if bad_codes:
            logging.warning(f'Unknown country codes: {bad_codes}. Skipping ...')
        for bad_code in bad_codes:
            del output[bad_code]
        missing = list(filter(lambda x: x not in codes, output.keys()))
        if missing:
            logging.warning(f'No population data available for {missing}')
        return output

    def measure(self):
        response = self.get('rest/v1/all', headers=self.headers)
        if response.status_code == 200:
            return {entry['alpha2Code']: entry['population'] for entry in response.json()}
        else:
            logging.warning(f'Failed to get country stats: {response.status_code} - {response.reason}')
        return dict()

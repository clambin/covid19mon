from datetime import datetime
import logging
import psycopg2
from src.pgconnector import PostgresConnector


class CovidPGConnector(PostgresConnector):
    def __init__(self, host, port, database, user, password):
        super().__init__(host, port, database, user, password)
        self.first = True
        self.reported = {}

    def _init_db(self):
        super()._init_db()
        self._record_latest()

    def _build_db(self):
        conn = None
        try:
            conn = self.connect()
            curr = conn.cursor()
            curr.execute("""
                CREATE TABLE IF NOT EXISTS covid19 (
                time TIMESTAMPTZ,
                country_code TEXT,
                country_name TEXT,
                confirmed DOUBLE PRECISION,
                death DOUBLE PRECISION,
                recovered DOUBLE PRECISION
                );
                CREATE INDEX IF NOT EXISTS idx_covid_country_name ON covid19(country_name);
                CREATE INDEX IF NOT EXISTS idx_covid_country_code ON covid19(country_code);
                CREATE INDEX IF NOT EXISTS idx_covid_time ON covid19(time);
            """)
            curr.close()
            conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            logging.critical(f'Failed to create covid19 table: {error}')
        finally:
            if conn:
                conn.close()

    def _drop_db(self):
        conn = None
        try:
            conn = self.connect()
            cur = conn.cursor()
            cur.execute("""DROP INDEX IF EXISTS idx_covid19_country""")
            cur.execute("""DROP INDEX IF EXISTS idx_covid19_time""")
            cur.execute("""DROP TABLE IF EXISTS covid19""")
            conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            logging.critical(f'Could not drop covid tables: {error}')
        finally:
            if conn:
                conn.close()

    def _record_entry(self, country, confirmed, deaths, recovered):
        self.reported[country] = {
            'confirmed': confirmed,
            'deaths': deaths,
            'recovered': recovered
        }

    def _record_latest(self):
        conn = None
        try:
            conn = self.connect()
            cur = conn.cursor()
            cur.execute("""
                SELECT country_name, confirmed, death, recovered FROM covid19 AS a
                    WHERE a.time = (SELECT MAX(time) FROM covid19 AS b WHERE a.country_name = b.country_name)
                    ORDER BY time, country_name
            """)
            for entry in cur.fetchall():
                self._record_entry(entry[0], entry[1], entry[2], entry[3])
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            logging.critical(f'Failed to get data: {error}')
        finally:
            if conn:
                conn.close()

    def _should_report(self, country, confirmed, deaths, recovered):
        return country not in self.reported or \
               confirmed != self.reported[country]['confirmed'] or \
               deaths != self.reported[country]['deaths'] or \
               recovered != self.reported[country]['recovered']

    def add(self, country_code, country_name, confirmed, deaths, recovered, recorded=None):
        self._init_db()
        if self._should_report(country_name, confirmed, deaths, recovered):
            if recorded is None:
                recorded = datetime.now()
            conn = None
            try:
                conn = self.connect()
                curr = conn.cursor()
                curr.execute("""
                    INSERT INTO covid19(time, country_code, country_name, confirmed, death, recovered)
                    VALUES(%s,%s,%s,%s,%s,%s)
                """,
                             (recorded, country_code, country_name, confirmed, deaths, recovered,))
                curr.close()
                conn.commit()
                self._record_entry(country_name, confirmed, deaths, recovered)
            except (Exception, psycopg2.DatabaseError) as error:
                logging.critical(f'Failed to insert data: {error}')
            finally:
                if conn:
                    conn.close()

    def addmany(self, records):
        self._init_db()
        now = datetime.now()
        changes = [
            [
                details['time'] if 'time' in details else now,
                details['code'],
                country,
                details['confirmed'],
                details['deaths'],
                details['recovered']
            ]
            for country, details in records.items()
            if self._should_report(country, details['confirmed'], details['deaths'], details['recovered'])
        ]
        if changes:
            conn = None
            try:
                conn = self.connect()
                curr = conn.cursor()
                curr.executemany("""
                    INSERT INTO covid19(time, country_code, country_name, confirmed, death, recovered)
                    VALUES(%s,%s,%s,%s,%s,%s)
                """, changes)
                curr.close()
                conn.commit()
                for (recorded, code, country, confirmed, deaths, recovered) in changes:
                    self._record_entry(country, confirmed, deaths, recovered)
                logging.debug(f'{len(changes)} records added')
            except (Exception, psycopg2.DatabaseError) as error:
                logging.critical(f'Failed to insert data: {error}')
            finally:
                if conn:
                    conn.close()

    def list(self, end_time=None):
        conn = rows = None
        try:
            conn = self.connect()
            cur = conn.cursor()
            if end_time:
                cur.execute("""
                SELECT time, country_code, country_name, confirmed, death, recovered FROM covid19
                    WHERE time < (%s) ORDER BY time
            """, (end_time,))
            else:
                cur.execute("""
                    SELECT time, country_code, country_name, confirmed, death, recovered FROM covid19 ORDER BY time
                """)
            rows = cur.fetchall()
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            logging.critical(f'Failed to get data: {error}')
        finally:
            if conn:
                conn.close()
        return rows

    def get_first(self, country):
        conn = entry = None
        try:
            conn = self.connect()
            cur = conn.cursor()
            cur.execute("""
                SELECT min(time) FROM covid19 WHERE country_name = %s
            """, (country,))
            entry = cur.fetchone()
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            logging.critical(f'Failed to get data: {error}')
        finally:
            if conn:
                conn.close()
        return entry[0] if entry else None

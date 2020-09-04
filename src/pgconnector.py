import psycopg2
import logging
from datetime import datetime


class DBError(Exception):
    pass


class PostgresConnector:
    def __init__(self, host, port, database, user, password):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    def connect(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password
        )


class TSDBConnector(PostgresConnector):
    def __init__(self, host, port, database, user, password):
        super().__init__(host, port, database, user, password)

    def migrate_data(self, target):
        added = 0
        collected = {}
        conn = None
        try:
            conn = self.connect()
            cur = conn.cursor()
            cur.execute("""
            SELECT time, name, value, labels FROM metrics WHERE value != 'NaN' ORDER BY time
            """)

            while True:
                rows = cur.fetchmany(1000)
                if not rows:
                    break
                for (time, metric, value, labels) in rows:
                    if labels['job'] == 'covid19':
                        code = labels['country_code']
                        name = labels['country_name']

                        if name not in collected:
                            collected[name] = {
                                'time': time,
                                'code': code
                            }
                        collected[name][metric] = value

                        if 'corona_confirmed_count' in collected[name] and \
                                'corona_death_count' in collected[name] and \
                                'corona_recovered_count' in collected[name]:
                            target.add(
                                collected[name]['code'],
                                name,
                                collected[name]['corona_confirmed_count'],
                                collected[name]['corona_death_count'],
                                collected[name]['corona_recovered_count'],
                                collected[name]['time'],
                            )
                            del collected[name]
                            added += 1
                            logging.debug(f'Records added: {added}')
        except (Exception, psycopg2.DatabaseError) as error:
            logging.critical(f'Failed to get metrics: {error}')
        finally:
            if conn:
                conn.close()


class CovidConnector(PostgresConnector):
    def __init__(self, host, port, database, user, password):
        super().__init__(host, port, database, user, password)
        self.first = True
        self.reported = {}

    def _build_covid_db(self):
        if self.first:
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
                    )
                """)
                # FIXME: 'create or replace' can fail if we're changing columns
                curr.execute("""
                    CREATE OR REPLACE VIEW delta AS
                        SELECT country_code, DATE_TRUNC('day', time) AS "day",
                        MAX(confirmed)-LAG(MAX(confirmed)) OVER (ORDER BY country_code, DATE_TRUNC('day',time))
                            AS "confirmed",
                        MAX(death)-LAG(MAX(death)) OVER (ORDER BY country_code, DATE_TRUNC('day',time)) AS "death",
                        MAX(recovered)-LAG(MAX(recovered)) OVER (ORDER BY country_code, DATE_TRUNC('day',time))
                            AS "recovered"
                        FROM covid19
                        GROUP BY 1,2
                        ORDER BY 1,2;
                """)
                curr.close()
                conn.commit()
            except (Exception, psycopg2.DatabaseError) as error:
                logging.critical(f'Failed to create covid19 table: {error}')
            finally:
                if conn:
                    conn.close()
            self.first = False

    def _drop_covid_db(self):
        conn = None
        try:
            conn = self.connect()
            cur = conn.cursor()
            try:
                cur.execute("""DROP VIEW delta""")
                conn.commit()
            except (Exception, psycopg2.DatabaseError):
                conn.rollback()
            try:
                cur.execute("""DROP TABLE covid19""")
                conn.commit()
            except (Exception, psycopg2.DatabaseError):
                conn.rollback()
        except (Exception, psycopg2.DatabaseError) as error:
            logging.critical(f'Could not drop covid tables: {error}')
        finally:
            if conn:
                conn.close()

    def _should_report(self, country, confirmed, deaths, recovered):
        return country not in self.reported or \
            confirmed != self.reported[country]['confirmed'] or \
            deaths != self.reported[country]['deaths'] or \
            recovered != self.reported[country]['recovered']

    def _record(self, country, confirmed, deaths, recovered):
        self.reported[country] = {
            'confirmed': confirmed,
            'deaths': deaths,
            'recovered': recovered
        }

    def add(self, country_code, country_name, confirmed, deaths, recovered, time=None):
        self._build_covid_db()
        if self._should_report(country_name, confirmed, deaths, recovered):
            if time is None:
                time = datetime.now()
            conn = None
            try:
                conn = self.connect()
                curr = conn.cursor()
                curr.execute("""
                INSERT INTO covid19(time, country_code, country_name, confirmed, death, recovered)
                VALUES(%s,%s,%s,%s,%s,%s)
                """,
                             (time, country_code, country_name, confirmed, deaths, recovered,))
                curr.close()
                conn.commit()
                self._record(country_name, confirmed, deaths, recovered)
            except (Exception, psycopg2.DatabaseError) as error:
                logging.critical(f'Failed to insert data: {error}')
            finally:
                if conn:
                    conn.close()

    def addmany(self, records):
        self._build_covid_db()
        time = datetime.now()
        changes = [
            [time, details['code'], country, details['confirmed'], details['deaths'], details['recovered']]
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
                for (time, code, country, confirmed, deaths, recovered) in changes:
                    self._record(country, confirmed, deaths, recovered)
            except (Exception, psycopg2.DatabaseError) as error:
                logging.critical(f'Failed to insert data: {error}')
            finally:
                if conn:
                    conn.close()

    def list(self):
        conn = rows = None
        try:
            conn = self.connect()
            cur = conn.cursor()
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

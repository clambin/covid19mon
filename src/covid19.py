import logging
import time
import requests
import psycopg2
from datetime import datetime
from prometheus_client import start_http_server, Summary, Gauge
from pimetrics.probe import APIProbe
from src.pgconnector import PostgresConnector, DBError
from src.version import version
from src.configuration import print_configuration
from src.population import PopulationProbe, PopulationConnector
from src.countries import country_codes

REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request', ['server', 'endpoint'])
GAUGES = {
    'corona_confirmed_count':
        Gauge('corona_confirmed_count', 'Number of confirmed cases', ['country_code', 'country_name']),
    'corona_death_count':
        Gauge('corona_death_count', 'Number of deaths', ['country_code', 'country_name']),
    'corona_recovered_count':
        Gauge('corona_recovered_count', 'Number of recoveries', ['country_code', 'country_name']),
}


class CovidConnector(PostgresConnector):
    def __init__(self, host, port, database, user, password):
        super().__init__(host, port, database, user, password)
        self.first = True
        self.reported = {}

    def _init_db(self):
        if self.first:
            self._build_covid_db()
            self._record_latest()
            self.first = False

    def _build_covid_db(self):
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
                CREATE INDEX IF NOT EXISTS idx_covid_country ON covid19(country_name);
                CREATE INDEX IF NOT EXISTS idx_covid_time ON covid19(time);
                CREATE OR REPLACE VIEW delta AS
                    SELECT country_code, DATE_TRUNC('day', time) AS "day",
                    MAX(confirmed)-LAG(MAX(confirmed)) OVER (ORDER BY country_code, DATE_TRUNC('day',time))
                        AS "confirmed",
                    MAX(death)-LAG(MAX(death)) OVER (ORDER BY country_code, DATE_TRUNC('day',time)) AS "death",
                    MAX(recovered)-LAG(MAX(recovered)) OVER (ORDER BY country_code, DATE_TRUNC('day',time))
                        AS "recovered"
                    FROM covid19
                    GROUP BY 1,2
                    ORDER BY 1,2
            """)
            curr.close()
            conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            logging.critical(f'Failed to create covid19 table: {error}')
        finally:
            if conn:
                conn.close()

    def _drop_covid_db(self):
        conn = None
        try:
            conn = self.connect()
            cur = conn.cursor()
            cur.execute("""DROP VIEW IF EXISTS delta""")
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
        recorded = datetime.now()
        changes = [
            [recorded, details['code'], country, details['confirmed'], details['deaths'], details['recovered']]
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


class CoronaStats(APIProbe):
    def __init__(self, api_key, dbconnector=None):
        super().__init__('https://covid-19-coronavirus-statistics.p.rapidapi.com/')
        self.api_key = api_key
        self.countries = None
        self.dbconnector = dbconnector
        self.bad_countries = []

    def call(self, endpoint, country=None):
        with REQUEST_TIME.labels(self.url, endpoint).time():
            result = None
            try:
                headers = {
                    'x-rapidapi-key': self.api_key,
                    'x-rapidapi-host': 'covid-19-coronavirus-statistics.p.rapidapi.com'
                }
                params = {'country': country} if country else None
                response = self.get(endpoint, headers, params=params)
                if response.status_code == 200:
                    result = response.json()
                else:
                    logging.error("%d - %s" % (response.status_code, response.reason))
            except requests.exceptions.RequestException as err:
                logging.warning(f'Failed to call "{self.url}": "{err}')
            return result

    def report(self, output):
        for country, details in output.items():
            code = details['code']
            confirmed = details['confirmed']
            deaths = details['deaths']
            recovered = details['recovered']
            GAUGES['corona_confirmed_count'].labels(code, country).set(confirmed)
            GAUGES['corona_death_count'].labels(code, country).set(deaths)
            GAUGES['corona_recovered_count'].labels(code, country).set(recovered)
        if output and self.dbconnector:
            try:
                self.dbconnector.addmany(output)
            except DBError as err:
                logging.error(f'Could not insert data in covid19 db: {err}')

    def measure(self):
        def nonetozero(val):
            return val if val is not None else 0
        output = {}
        stats = self.call('v1/stats')
        if stats:
            for entry in stats['data']['covid19Stats']:
                country = entry['country']
                if country not in country_codes:
                    if country not in self.bad_countries:
                        logging.warning(f'Could not find country code for "{country}". Skipping ...')
                        self.bad_countries.append(country)
                    continue
                if country not in output:
                    output[country] = {
                        # Grafana world map uses country codes ('BE') rather than names ('Belgium')
                        'code': country_codes[country],
                        'confirmed': 0,
                        'deaths': 0,
                        'recovered': 0
                    }
                output[country]['confirmed'] += nonetozero(entry['confirmed'])
                output[country]['deaths'] += nonetozero(entry['deaths'])
                output[country]['recovered'] += nonetozero(entry['recovered'])
        return output


def covid19(configuration):
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG if configuration.debug else logging.INFO)
    logging.info(f'Starting covid19mon v{version}')
    logging.info(f'Configuration: {print_configuration(configuration)}')

    start_http_server(configuration.port)

    populationconn = PopulationConnector(
        host=configuration.postgres_host,
        port=configuration.postgres_port,
        database=configuration.postgres_database,
        user=configuration.postgres_user,
        password=configuration.postgres_password
    )

    probe = PopulationProbe(configuration.apikey, populationconn)
    probe.run()

    covidconn = CovidConnector(
        host=configuration.postgres_host,
        port=configuration.postgres_port,
        database=configuration.postgres_database,
        user=configuration.postgres_user,
        password=configuration.postgres_password
    )

    probe = CoronaStats(configuration.apikey, covidconn)
    while True:
        probe.run()
        if configuration.once:
            break
        time.sleep(configuration.interval)

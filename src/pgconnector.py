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

    def _query(self, statement):
        conn = None
        try:
            conn = self.connect()
            cur = conn.cursor()
            cur.execute(statement)
            data = cur.fetchall()
            cur.close()
        except psycopg2.OperationalError as e:
            raise DBError(e)
        finally:
            if conn:
                conn.close()
        return data


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
            SELECT time, name, value, labels FROM METRICS WHERE value != 'NaN' ORDER BY TIME
            """)

            while True:
                rows = cur.fetchmany(100)
                if not rows: break
                for (time, metric, value, labels) in rows:
                    if labels['job'] != 'covid19': continue
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
                        logging.info(f'Records added: {added}')
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

    def _create_covid_table(self):
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
            curr.close()
            conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            logging.critical(f'Failed to create covid19 table: {error}')
        finally:
            if conn:
                conn.close()

    def _should_report(self, country, confirmed, death, recovered):
        return country not in self.reported or \
               confirmed != self.reported[country]['confirmed'] or \
               death != self.reported[country]['death'] or \
               recovered != self.reported[country]['recovered']

    def _record(self, country, confirmed, death, recovered):
        self.reported[country] = {
            'confirmed': confirmed,
            'death': death,
            'recovered': recovered
        }

    def add(self, country_code, country_name, confirmed, death, recovered, time=None):
        if self.first:
            self._create_covid_table()
            self.first = False
        if self._should_report(country_name, confirmed, death, recovered):
            if time is None:
                time = datetime.now()
            conn = None
            try:
                conn = self.connect()
                curr = conn.cursor()
                curr.execute('INSERT INTO covid19(time, country_code, country_name, confirmed, death, recovered) '
                             'VALUES(%s,%s,%s,%s,%s,%s)',
                             (time, country_code, country_name, confirmed, death, recovered,))
                curr.close()
                conn.commit()
                self._record(country_name, confirmed, death, recovered)
            except (Exception, psycopg2.DatabaseError) as error:
                logging.critical(f'Failed to insert data: {error}')
            finally:
                if conn:
                    conn.close()


# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO)
#    covid = CovidConnector(
#        host='192.168.0.10',
#        port='5433',
#        database='covid19',
#        user='postgres',
#        password='example'
#    )
#    tsdb = TSDBConnector(
#        host='192.168.0.10',
#        port='5432',
#        database='postgres',
#        user='postgres',
#        password='example'
#    )
#
#    tsdb.migrate_data(covid)

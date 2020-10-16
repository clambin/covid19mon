import logging
import os
import psycopg2
from src.pgconnector import PostgresConnector
from src.covid19mon import CovidConnector


class TSDBConnector(PostgresConnector):
    def __init__(self, host, port, database, user, password):
        super().__init__(host, port, database, user, password)

    def _init_db(self):
        pass

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


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    covid = CovidConnector(
        host='192.168.0.10',
        port='5433',
        database='covid19',
        user='postgres',
        password=os.getenv('COVID_PASSWORD')
    )
    tsdb = TSDBConnector(
        host='192.168.0.10',
        port='5432',
        database='postgres',
        user='postgres',
        password=os.getenv('TSDB_PASSWORD')
    )

    tsdb.migrate_data(covid)

import logging
from src.pgconnector import CovidConnector, TSDBConnector

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    covid = CovidConnector(
        host='192.168.0.10',
        port='5433',
        database='covid19',
        user='postgres',
        password='example'  # noseq
    )
    tsdb = TSDBConnector(
        host='192.168.0.10',
        port='5432',
        database='postgres',
        user='postgres',
        password='example'  # noseq
    )

    tsdb.migrate_data(covid)

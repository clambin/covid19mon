import logging
import os
from src.pgconnector import CovidConnector, TSDBConnector

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

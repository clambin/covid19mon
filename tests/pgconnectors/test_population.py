import os
import psycopg2
import psycopg2.errors
import pytest
from covid19.pgconnectors.population import PopulationPGConnector


def get_dbenv():
    return \
        os.getenv('POSTGRES_HOST'), \
        os.getenv('POSTGRES_PORT'), \
        os.getenv('POSTGRES_DB'), \
        os.getenv('POSTGRES_USER'), \
        os.getenv('POSTGRES_PASSWORD')


def get_connector():
    host, port, database, user, password = get_dbenv()
    return PopulationPGConnector(host, port, database, user, password)


def test_pgconnector():
    connector = get_connector()
    assert connector
    connector._drop_db()
    connector.addmany({
        'BE': 11248330,
        'US': 321645000,
        'CN': 1371590000
    })
    rows = connector.list()
    assert rows == {'BE': 11248330, 'CN': 1371590000, 'US': 321645000}
    connector.addmany({
        'NL': 16916000,
    })
    rows = connector.list()
    assert rows == {'BE': 11248330, 'CN': 1371590000, 'NL': 16916000, 'US': 321645000}
    connector._drop_db()
    with pytest.raises(psycopg2.errors.UndefinedTable):
        conn = connector.connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM population")
        conn.commit()

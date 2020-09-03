import os
import psycopg2
from src.pgconnector import CovidConnector


def get_dbenv_gitlab():
    return \
        os.getenv('POSTGRES_HOST'), \
        os.getenv('POSTGRES_PORT'), \
        os.getenv('POSTGRES_DB'), \
        os.getenv('POSTGRES_USER'), \
        os.getenv('POSTGRES_PASSWORD')


def get_dbenv():
    return '192.168.0.10', 5432, 'test', 'postgres', 'example'


def test_pgconnector():
    host, port, database, user, password = get_dbenv()
    connector = CovidConnector(host, port, database, user, password)
    assert connector
    conn = connector.connect()
    assert conn
    cur = conn.cursor()
    assert cur
    try:
        cur.execute("DELETE FROM covid19")
        conn.commit()
    except psycopg2.DatabaseError:
        conn.rollback()
    connector.add('BE', 'Belgium', 3, 2, 1)
    cur.execute("SELECT time, country_code, country_name, confirmed, death, recovered FROM covid19 ORDER BY time")
    rows = cur.fetchmany(1000)
    assert len(rows) == 1
    assert len(rows[0]) == 6
    assert rows[0][1] == 'BE'
    assert rows[0][2] == 'Belgium'
    assert rows[0][3] == 3
    assert rows[0][4] == 2
    assert rows[0][5] == 1
    connector.addmany({
        'Belgium': {
            'code': 'BE',
            'confirmed': 3,
            'deaths': 2,
            'recovered': 1
        }
    })
    cur.execute("SELECT time, country_code, country_name, confirmed, death, recovered FROM covid19 ORDER BY time")
    rows = cur.fetchmany(1000)
    assert len(rows) == 1
    connector.addmany({
        'Belgium': {
            'code': 'BE',
            'confirmed': 6,
            'deaths': 4,
            'recovered': 2
        }
    })
    cur.execute("SELECT time, country_code, country_name, confirmed, death, recovered FROM covid19 ORDER BY time")
    rows = cur.fetchmany(1000)
    assert len(rows) == 2
    assert rows[0][1] == rows[1][1] == 'BE'
    assert rows[0][2] == rows[1][2] == 'Belgium'
    assert rows[0][3] == 3
    assert rows[0][4] == 2
    assert rows[0][5] == 1
    assert rows[1][3] == 6
    assert rows[1][4] == 4
    assert rows[1][5] == 2

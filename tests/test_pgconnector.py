import os
import datetime
import psycopg2
from src.pgconnector import CovidConnector


def get_dbenv():
    return \
        os.getenv('POSTGRES_HOST'), \
        os.getenv('POSTGRES_PORT'), \
        os.getenv('POSTGRES_DB'), \
        os.getenv('POSTGRES_USER'), \
        os.getenv('POSTGRES_PASSWORD')


def test_pgconnector():
    host, port, database, user, password = get_dbenv()
    connector = CovidConnector(host, port, database, user, password)
    assert connector
    conn = connector.connect()
    assert conn
    cur = conn.cursor()
    assert cur
    cur.execute("DELETE FROM covid19")
    cur.close()
    conn.commit()
    conn.close()
    connector.add('BE', 'Belgium', 3, 2, 1)
    rows = connector.list()
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
    rows = connector.list()
    assert len(rows) == 1
    connector.addmany({
        'Belgium': {
            'code': 'BE',
            'confirmed': 6,
            'deaths': 4,
            'recovered': 2
        }
    })
    rows = connector.list()
    assert len(rows) == 2
    assert rows[0][1] == rows[1][1] == 'BE'
    assert rows[0][2] == rows[1][2] == 'Belgium'
    assert rows[0][3] == 3
    assert rows[0][4] == 2
    assert rows[0][5] == 1
    assert rows[1][3] == 6
    assert rows[1][4] == 4
    assert rows[1][5] == 2
    connector.add('BE', 'Belgium', 0, 0, 0, datetime.datetime(2000, 1, 1))
    entry = connector.get_first('Belgium')
    assert entry.strftime('%Y-%m-%d') == '2000-01-01'
    entry = connector.get_first('Not a country')
    assert entry is None

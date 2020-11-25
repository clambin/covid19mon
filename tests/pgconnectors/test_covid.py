import os
import datetime
import psycopg2
import psycopg2.errors
import pytest
from covid19.pgconnectors.covid import CovidPGConnector


def get_dbenv():
    return \
        os.getenv('POSTGRES_HOST'), \
        os.getenv('POSTGRES_PORT'), \
        os.getenv('POSTGRES_DB'), \
        os.getenv('POSTGRES_USER'), \
        os.getenv('POSTGRES_PASSWORD')


def get_connector():
    host, port, database, user, password = get_dbenv()
    return CovidPGConnector(host, port, database, user, password)


def test_pgconnector():
    connector = get_connector()
    assert connector
    connector._drop_db()
    with pytest.raises(psycopg2.errors.UndefinedTable):
        conn = connector.connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM covid19")
        conn.commit()
    connector.addmany({
        'Belgium': {
            'code': 'BE',
            'confirmed': 3,
            'deaths': 2,
            'recovered': 1,
            'time': datetime.datetime(2020, 11, 1)
        }
    })
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
            'confirmed': 6,
            'deaths': 4,
            'recovered': 2,
            'time': datetime.datetime(2020, 11, 2)
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
    rows = connector.list('2020-11-02')
    assert len(rows) == 1
    assert len(rows[0]) == 6
    assert rows[0][1] == 'BE'
    assert rows[0][2] == 'Belgium'
    assert rows[0][3] == 3
    assert rows[0][4] == 2
    assert rows[0][5] == 1
    entry = connector.get_first('Belgium')
    assert entry.strftime('%Y-%m-%d') == '2020-11-01'
    entry = connector.get_first('Not a country')
    assert entry is None
    connector2 = get_connector()
    connector2._init_db()
    last_updated = connector2.get_last_updated()
    assert len(last_updated.keys()) == 1
    assert 'Belgium' in last_updated
    assert last_updated['Belgium'] == datetime.datetime(2020, 11, 2)

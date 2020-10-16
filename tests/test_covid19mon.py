import os
from src.configuration import get_configuration
from src.covid19mon import covid19mon
from src.covidpgconnector import CovidPGConnector
from tests.test_pgconnector import get_dbenv


def test_main():
    host, port, database, user, password = get_dbenv()
    connector = CovidPGConnector(host, port, database, user, password)
    connector._drop_db()
    config = get_configuration(f'--once --debug '
                               f'--apikey {os.getenv("API_KEY")} '
                               f'--postgres-host {host} '
                               f'--postgres-port {port} '
                               f'--postgres-database {database} '
                               f'--postgres-user {user} '
                               f'--postgres-password {password}'.split())
    assert config
    covid19mon(config)
    rows = connector.list()
    assert rows
    assert len(rows) > 0
    for row in rows:
        assert isinstance(row, tuple)
        assert len(row) == 6

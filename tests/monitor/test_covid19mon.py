import os
from covid19.monitor.configuration import get_configuration
from covid19.monitor.monitor import main
from covid19.pgconnectors.covid import CovidPGConnector
from tests.pgconnectors.test_covid import get_dbenv


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
    main(config)
    rows = connector.list()
    assert rows
    assert len(rows) > 0
    for row in rows:
        assert isinstance(row, tuple)
        assert len(row) == 6

import os
from src.population import PopulationProbe
from src.population import PopulationDBConnector


def get_dbenv():
    return \
        os.getenv('POSTGRES_HOST'), \
        os.getenv('POSTGRES_PORT'), \
        os.getenv('POSTGRES_DB'), \
        os.getenv('POSTGRES_USER'), \
        os.getenv('POSTGRES_PASSWORD')


def get_connector():
    host, port, database, user, password = get_dbenv()
    return PopulationDBConnector(host, port, database, user, password)


def test_population():
    connector = get_connector()
    probe = PopulationProbe(os.getenv('API_KEY'), connector)
    probe.run()
    measured = probe.measured()
    assert 'BE' in measured
    assert measured['BE'] > 0
    assert measured['US'] > measured['BE'] > measured['GS']
    stored = connector.list()
    assert len(stored) == len(measured)
    for key, value in stored.items():
        assert key in measured
        assert value == measured[key]
    probe.run()
    measured2 = probe.measured()
    assert len(measured2) == len(measured)
    assert measured2 == measured
    stored = connector.list()
    assert len(stored) == len(measured)

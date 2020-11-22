from covid19.apiserver.configuration import get_configuration, print_configuration


def test_default_config():
    config = get_configuration([])
    assert config.debug is False
    assert config.port == 8080
    assert config.postgres_database == 'covid19'


def test_main_config():
    args = '--port 1234 --postgres-database=covid'.split()
    config = get_configuration(args)
    assert config.port == 1234
    assert config.debug is False
    assert config.postgres_database == "covid"


def test_print_config():
    args = '--postgres-host foobar --postgres-port 5432 --postgres-database snafu'.split()
    config = get_configuration(args)
    output = print_configuration(config)
    assert output == 'port=8080, debug=False, postgres_host=foobar, postgres_port=5432, ' \
                     'postgres_database=snafu, postgres_user=None, postgres_password=None'


def test_redacted_config():
    args = '--postgres-user foo --postgres-password bar'.split()
    config = get_configuration(args)
    output = print_configuration(config)
    assert output == 'port=8080, debug=False, postgres_host=None, postgres_port=5432, ' \
                     'postgres_database=covid19, postgres_user=foo, postgres_password=************'

import argparse
import pytest
from src.configuration import str2bool, get_configuration, print_configuration


def test_str2bool():
    assert str2bool(True) is True
    for arg in ['yes', 'true', 't', 'y', '1', 'on']:
        assert str2bool(arg) is True
    for arg in ['no', 'false', 'f', 'n', '0', 'off']:
        assert str2bool(arg) is False
    with pytest.raises(argparse.ArgumentTypeError) as e:
        assert str2bool('maybe')
    assert str(e.value) == 'Boolean value expected.'


def test_default_config():
    config = get_configuration([])
    assert config.debug is False
    assert config.interval == 1200
    assert config.port == 8080
    assert config.postgres_database == 'covid19'


def test_main_config():
    args = '--interval 25 --port 1234 --apikey 4321'.split()
    config = get_configuration(args)
    assert config.interval == 25
    assert config.port == 1234
    assert config.debug is False
    assert config.apikey == "4321"


def test_print_config():
    args = '--once --apikey 4321 --postgres-host foobar --postgres-port 5432 --postgres-database snafu'.split()
    config = get_configuration(args)
    output = print_configuration(config)
    assert output == 'interval=1200, port=8080, debug=False, once=True, apikey=****, postgres_host=foobar, ' \
                     'postgres_port=5432, postgres_database=snafu, postgres_user=None, ' \
                     'postgres_password=None'


def test_redacted_config():
    args = '--postgres-user foo --postgres-password bar'.split()
    config = get_configuration(args)
    output = print_configuration(config)
    assert output == 'interval=1200, port=8080, debug=False, once=False, apikey=None, ' \
                     'postgres_host=None, postgres_port=5432, postgres_database=covid19, postgres_user=foo, ' \
                     'postgres_password=************'
    args = '--apikey 12345678901234567890123456789012'.split()
    config = get_configuration(args)
    output = print_configuration(config)
    assert output == 'interval=1200, port=8080, debug=False, once=False, apikey=********************************, ' \
                     'postgres_host=None, postgres_port=5432, postgres_database=covid19, postgres_user=None, ' \
                     'postgres_password=None'

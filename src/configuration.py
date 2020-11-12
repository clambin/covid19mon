import argparse
import copy

from src.version import version


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1', 'on'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0', 'off'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def get_configuration(args=None):
    default_interval = 1200
    default_port = 8080
    default_pg_port = 5432
    default_pg_database = 'covid19'

    # FIXME: allow credentials to be retrieved from file rather than cmdline options
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version=f'%(prog)s {version}')
    parser.add_argument('--interval', type=int, default=default_interval,
                        help=f'Time between measurements (default: {default_interval} sec)')
    parser.add_argument('--port', type=int, default=default_port,
                        help=f'Prometheus listener port (default: {default_port})')
    parser.add_argument('--debug', action='store_true',
                        help='Set logging level to debug')
    parser.add_argument('--once', action='store_true',
                        help='Measure once and then terminate')
    parser.add_argument('--apikey',
                        help='API Key')
    parser.add_argument('--postgres-host',
                        help='Postgres DB host')
    parser.add_argument('--postgres-port', default=default_pg_port,
                        help=f'Postgres DB port (default: {default_pg_port})')
    parser.add_argument('--postgres-database', default=default_pg_database,
                        help=f'Postgres DB database name (default: {default_pg_database})')
    parser.add_argument('--postgres-user',
                        help='Postgres DB user name')
    parser.add_argument('--postgres-password',
                        help='Postgres DB password')
    parser.add_argument('--pushgateway',
                        help='URL of Prometheus pushgateway server')
    return parser.parse_args(args)


def print_configuration(config):
    redacted = copy.deepcopy(config)
    if redacted.apikey:
        redacted.apikey = '*' * len(redacted.apikey)
    if redacted.postgres_password:
        redacted.postgres_password = '*' * 12
    return ', '.join([f'{key}={val}' for key, val in vars(redacted).items()])

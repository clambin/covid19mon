import logging
from prometheus_client import start_http_server
from pimetrics.scheduler import Scheduler
from src.version import version
from src.configuration import print_configuration
from src.populationprobe import PopulationProbe
from src.populationpgconnector import PopulationPGConnector
from src.covidprobe import CovidProbe
from src.covidpgconnector import CovidPGConnector


def initialise(configuration):
    scheduler = Scheduler()

    if configuration.postgres_host:
        populationconn = PopulationPGConnector(
            host=configuration.postgres_host,
            port=configuration.postgres_port,
            database=configuration.postgres_database,
            user=configuration.postgres_user,
            password=configuration.postgres_password
        )
        scheduler.register(PopulationProbe(configuration.apikey, populationconn), 60*60*24)

        covidconn = CovidPGConnector(
            host=configuration.postgres_host,
            port=configuration.postgres_port,
            database=configuration.postgres_database,
            user=configuration.postgres_user,
            password=configuration.postgres_password
        )
    else:
        covidconn = None

    scheduler.register(CovidProbe(configuration.apikey, covidconn), configuration.interval)

    return scheduler


def covid19mon(configuration):
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG if configuration.debug else logging.INFO)
    logging.info(f'Starting covid19mon v{version}')
    logging.info(f'Configuration: {print_configuration(configuration)}')
    start_http_server(configuration.port)

    scheduler = initialise(configuration)
    if configuration.once:
        scheduler.run(once=True)
    else:
        while True:
            scheduler.run(duration=configuration.interval)
    return 0

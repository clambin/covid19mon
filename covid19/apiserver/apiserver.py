import os
import cProfile
import json
import logging
import waitress
from prometheus_flask_exporter import PrometheusMetrics

from covid19.apiserver.covid19api import Covid19API
from covid19.version import version
from covid19.apiserver.configuration import print_configuration
from covid19.pgconnectors.covid import CovidPGConnector

from flask import Flask, request


app = Flask("test")
flask_metrics = PrometheusMetrics(app)
flask_metrics.info('covid19api', 'Grafana API server for covid19mon data', version=version)
g_covid19api = Covid19API()


@app.route("/")
@flask_metrics.do_not_track()
def index():
    return "OK"


@app.route("/search", methods=["POST"])
def grafana_search():
    global g_covid19api
    targets = g_covid19api.targets
    logging.debug(f'/search: {json.dumps(targets, indent=4, sort_keys=True)}')
    return json.dumps(targets)


@app.route("/query", methods=["POST"])
def grafana_query():
    global g_covid19api
    req = request.get_json(force=True)
    # max_data_points = req['maxDataPoints']
    # interval = req['interval']
    start_time = req['range']['from']
    end_time = req['range']['to']
    targets = [(entry['target'], entry['type']) for entry in req['targets']]
    logging.info(f'/query - {targets} ({start_time}/{end_time}')
    metrics = g_covid19api.get_data(targets, start_time, end_time)
    logging.debug(f'/query: {json.dumps(metrics, indent=4, sort_keys=True)}')
    logging.info('/query done')
    return json.dumps(metrics)


def main(configuration):
    global g_covid19api, app
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG if configuration.debug else logging.INFO)
    logging.info(f'Starting covid19api v{version}')
    logging.info(f'Configuration: {print_configuration(configuration)}')
    g_covid19api.set_covidpg(CovidPGConnector(
        configuration.postgres_host, configuration.postgres_port,
        configuration.postgres_database,
        configuration.postgres_user, configuration.postgres_password))
    waitress.serve(app, host='0.0.0.0', port=configuration.port)  # nosec


if __name__ == '__main__':
    g_covid19api.set_covidpg(CovidPGConnector(
        os.getenv('POSTGRES_HOST'),
        os.getenv('POSTGRES_PORT'),
        os.getenv('POSTGRES_DATABASE'),
        os.getenv('POSTGRES_USER'),
        os.getenv('POSTGRES_PASSWORD')))
    cProfile.run('g_covid19api.get_data([("confirmed","timeseries")])')

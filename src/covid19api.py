import json
import logging
from datetime import datetime
from src.covidpgconnector import CovidPGConnector
from src.version import version
from src.configuration import print_configuration

from flask import Flask, request


app = Flask("test")
g_covid19api = None


class Covid19API:
    def __init__(self, covid19pg):
        self._targets = ['confirmed', 'death', 'recovered']
        self.covid19pg = covid19pg

    @property
    def targets(self):
        return self._targets

    def get_data(self, targets):
        def datetime_to_epoch(ts):
            return int((datetime(ts.year, ts.month, ts.day) - datetime(1970, 1, 1)).total_seconds() * 1000)

        def is_target(target, target_names):
            for t in target_names:
                if t[0] == target:
                    return True
            return False

        countries = set()
        values = dict()
        for entry in self.covid19pg.list():
            time = datetime_to_epoch(entry[0])
            code = entry[1]
            confirmed = entry[3]
            death = entry[4]
            recovered = entry[5]
            if time not in values:
                values[time] = dict()
            if code not in values[time]:
                values[time][code] = {}
            values[time][code] = {'confirmed': confirmed, 'death': death, 'recovered': recovered}
            countries.add(code)
        confirmed = {'target': 'confirmed', 'datapoints': []}
        death = {'target': 'death', 'datapoints': []}
        recovered = {'target': 'recovered', 'datapoints': []}
        last = {
            'confirmed': {country: 0 for country in countries},
            'death': {country: 0 for country in countries},
            'recovered': {country: 0 for country in countries}
        }
        for time, metrics in values.items():
            for country, data in metrics.items():
                last['confirmed'][country] = data['confirmed']
                last['death'][country] = data['death']
                last['recovered'][country] = data['recovered']
            confirmed['datapoints'].append([sum(last['confirmed'].values()), time])
            death['datapoints'].append([sum(last['death'].values()), time])
            recovered['datapoints'].append([sum(last['recovered'].values()), time])
        # TODO: support table output: https://grafana.com/grafana/plugins/simpod-json-datasource#query
        output = []
        if is_target('confirmed', targets):
            output.append(confirmed)
        if is_target('death', targets):
            output.append(death)
        if is_target('recovered', targets):
            output.append(recovered)
        return output


@app.route("/")
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
    # TODO: optimize by only calculating/returning for start_time/end_time
    # start_time = req['range']['from']
    # end_time = req['range']['to']
    targets = [(entry['target'], entry['type']) for entry in req['targets']]
    logging.debug(f'Got request for {targets}')
    metrics = g_covid19api.get_data(targets)
    logging.debug(f'/query: {json.dumps(metrics, indent=4, sort_keys=True)}')
    return json.dumps(metrics)


def covid19api(configuration):
    global g_covid19api
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG if configuration.debug else logging.INFO)
    logging.info(f'Starting covid19api v{version}')
    logging.info(f'Configuration: {print_configuration(configuration)}')
    covid19pg = CovidPGConnector(
        configuration.postgres_host, configuration.postgres_port,
        configuration.postgres_database,
        configuration.postgres_user, configuration.postgres_password)
    g_covid19api = Covid19API(covid19pg)
    app.run(debug=False, host='0.0.0.0')  # nosec

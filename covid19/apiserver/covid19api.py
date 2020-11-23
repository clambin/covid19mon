import logging
import re
from datetime import datetime, date


class DataCache:
    def __init__(self):
        self._cache = dict()

    def add(self, key, data):
        self._cache[key] = data

    def get(self, key):
        if self.has(key):
            return self._cache[key]
        return None

    def has(self, key):
        return key in self._cache


    def len(self):
        return len(self._cache)

    def clear(self, key=None):
        if key:
            del self._cache[key]
        else:
            self._cache = dict()


class Covid19API:
    def __init__(self):
        self._targets = [
            'confirmed', 'confirmed-delta',
            'death', 'death-delta',
            'recovered', 'recovered-delta',
            'active', 'active-delta'
        ]
        self.covid19pg = None
        self._epoch_cache = dict()
        self._cache = DataCache()

    @property
    def targets(self):
        return self._targets

    def set_covidpg(self, covidpg):
        self.covid19pg = covidpg

    def datetime_to_epoch(self, ts):
        if ts not in self._epoch_cache:
            self._epoch_cache[ts] = int(
                (datetime(ts.year, ts.month, ts.day) - datetime(1970, 1, 1)).total_seconds() * 1000
            )
        return self._epoch_cache[ts]

    def grafana_date_to_epoch(self, ts):
        if ts:
            m = re.match(r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.(\d{3})Z', ts)
            if m:
                return self.datetime_to_epoch(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        return 0

    @staticmethod
    def is_target(my_target, target_names):
        for t in target_names:
            if t[0] == my_target:
                return True
        return False

    def get_data_by_time_country(self, end_time=None):
        countries = set()
        values = dict()
        all_data = self._cache.get(end_time)
        if all_data is None:
            self._cache.clear()
            all_data = self.covid19pg.list(end_time=end_time)
            self._cache.add(end_time, all_data)
        for entry in all_data:
            time = self.datetime_to_epoch(entry[0])
            code = entry[1]
            confirmed = entry[3]
            death = entry[4]
            recovered = entry[5]
            if time not in values:
                values[time] = dict()
            if code not in values[time]:
                values[time][code] = dict()
            values[time][code] = {'confirmed': confirmed, 'death': death, 'recovered': recovered}
            countries.add(code)
        return values, countries

    def get_data_by_time(self, values, countries, start_time):
        metrics = dict()
        current = dict()
        for t in self.targets:
            metrics[t] = {'target': t, 'datapoints': []}
            current[t] = 0
        last = {
            'confirmed': {country: 0 for country in countries},
            'death': {country: 0 for country in countries},
            'recovered': {country: 0 for country in countries}
        }
        skip_time = self.grafana_date_to_epoch(start_time)
        for time, time_data in values.items():
            for country, data in time_data.items():
                last['confirmed'][country] = data['confirmed']
                last['death'][country] = data['death']
                last['recovered'][country] = data['recovered']
            previous = current
            current = dict()
            current['confirmed'] = sum(last['confirmed'].values())
            current['death'] = sum(last['death'].values())
            current['recovered'] = sum(last['recovered'].values())
            current['active'] = current['confirmed'] - current['death'] - current['recovered']
            if time < skip_time:
                continue
            for t in self.targets:
                if t.endswith('-delta'):
                    pass
                else:
                    metrics[t]['datapoints'].append([current[t], time])
                    metrics[f'{t}-delta']['datapoints'].append([current[t] - previous[t], time])
        return metrics

    def get_data(self, targets, start_time=None, end_time=None):
        # TODO: support table output: https://grafana.com/grafana/plugins/simpod-json-datasource#query
        logging.debug(f'{start_time} {end_time}')
        values, countries = self.get_data_by_time_country(end_time)
        metrics = self.get_data_by_time(values, countries, start_time)
        output = []
        for target in self.targets:
            if Covid19API.is_target(target, targets):
                output.append(metrics[target])
        return output

    def clear_cache(self):
        self._cache.clear()

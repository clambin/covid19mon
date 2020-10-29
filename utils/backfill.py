import os
import time
import datetime
import requests
import logging
import pytz
from src.countries import country_codes
from src.covidpgconnector import CovidPGConnector

# You'd expect country names & codes would be an easy standard but noooooo ...
country_mapping = {
    'Wallis and Futuna Islands': 'Wallis and Futuna',
    'Republic of Kosovo': 'Kosovo',
    'United States of America': 'US',
    'Holy See (Vatican City State)': 'Holy See',
    'Korea (South)': 'Korea, South',
    'Saint-Martin (French part)': 'Saint Martin',
    'Cocos (Keeling) Islands': 'Cocos [Keeling] Islands',
    'Côte d\'Ivoire': 'Cote d\'Ivoire',
    'Micronesia, Federated States of': 'Micronesia',
    'Palestinian Territory': 'West Bank and Gaza',
    'Russian Federation': 'Russia',
    'Macao, SAR China': 'Macau',
    'ALA Aland Islands': 'Åland',
    'Pitcairn': 'Pitcairn Islands',
    'Brunei Darussalam': 'Brunei',
    'Hong Kong, SAR China': 'Hong Kong',
    'Macedonia, Republic of': 'North Macedonia',
    'Virgin Islands, US': 'U.S. Virgin Islands',
    'Myanmar': 'Burma',
    'Korea (North)': 'North Korea',
    'Saint Vincent and Grenadines': 'Saint Vincent and the Grenadines',
    'Heard and Mcdonald Islands': 'Heard Island and McDonald Islands',
    'Svalbard and Jan Mayen Islands': 'Svalbard and Jan Mayen',
    'Taiwan, Republic of China': 'Taiwan*',
    'Tanzania, United Republic of': 'Tanzania',
    'Syrian Arab Republic (Syria)': 'Syria',
    'Iran, Islamic Republic of': 'Iran',
    'Venezuela (Bolivarian Republic)': 'Venezuela',
    'Viet Nam': 'Vietnam',
    'Falkland Islands (Malvinas)': 'Falkland Islands [Islas Malvinas]',
    'US Minor Outlying Islands': 'U.S. Minor Outlying Islands',
    'Lao PDR': 'Laos',
    'Czech Republic': 'Czechia',
    'Cape Verde': 'Cabo Verde',
    'Swaziland': 'Eswatini',
}


class HistoricalData:
    def __init__(self, pgconnector):
        self.url = 'https://api.covid19api.com'
        self.countries = self._get_countries()
        self.slowdown = 5
        self.pgconnector = pgconnector

    @staticmethod
    def map_country(name):
        mapped = country_mapping[name] if name in country_mapping else name
        if mapped in country_codes.keys():
            return mapped, country_codes[mapped]
        else:
            return None, None

    def _call(self, endpoint):
        url = f'{self.url}/{endpoint}'
        while True:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    logging.debug(response.content)
                    return response.json()
                elif response.status_code == 429:
                    logging.debug(f'{response.reason}. Sleeping for {self.slowdown} second(s)')
                    time.sleep(self.slowdown)
                else:
                    logging.error(f'Failed to get data: {response.status_code} - {response.reason}')
                    break
            except requests.exceptions.ConnectionError as e:
                logging.warning(f'Failed to connect to {url}: {e}')
                break
        return None

    def _get_countries(self):
        countries = dict()
        for country in self._call('countries'):
            countries[country['Slug']] = {
                'code': country['ISO2'],
                'country': country['Country'],
            }
        return countries

    def get_country(self, slug):
        return self.countries[slug]['country'] if slug in self.countries else None

    def get_historical_data(self, countries=None):
        if countries is None:
            countries = self.countries.keys()
        output = dict()
        for slug in countries:
            country = self.get_country(slug)
            country, code = self.map_country(country)
            last_date = self.pgconnector.get_first(country)
            logging.info(f'Processing {country}')
            for entry in self._call(f'total/country/{slug}'):
                timestamp = pytz.UTC.localize(datetime.datetime.strptime(entry['Date'], '%Y-%m-%dT%H:%M:%SZ'))
                if last_date is not None and timestamp >= last_date:
                    continue
                if timestamp not in output:
                    output[timestamp] = dict()
                output[timestamp][country] = {
                    'time': timestamp,
                    'code': code,
                    'confirmed': entry['Confirmed'],
                    'deaths': entry['Deaths'],
                    'recovered': entry['Recovered'],
                }
        return output

    def backfill(self, countries=None):
        data = self.get_historical_data(countries)
        for timestamp, values in data.items():
            logging.info(f'Processing {timestamp}')
            self.pgconnector.addmany(values)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    covid = CovidPGConnector(
        host='192.168.0.11',
        port='31000',
        database='cicd',
        user='cicd',
        password=os.getenv('COVID_PASSWORD')
    )
    server = HistoricalData(covid)
    server.backfill()

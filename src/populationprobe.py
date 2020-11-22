import logging
from pimetrics.probe import APIProbe
from src.countries import country_codes


class PopulationProbe(APIProbe):
    def __init__(self, api_key, dbconnector=None):
        super().__init__('https://ajayakv-rest-countries-v1.p.rapidapi.com')
        self.headers = {
            'x-rapidapi-host': "ajayakv-rest-countries-v1.p.rapidapi.com",
            'x-rapidapi-key': api_key
        }
        self.population = dict()
        self.dbconnector = dbconnector

    def report(self, output):
        self.dbconnector.add(output)

    def process(self, output):
        codes = country_codes.values()
        bad_codes = [key for key in output.keys() if key not in codes]
        if bad_codes:
            logging.warning(f'Unknown country codes: {bad_codes}. Skipping ...')
        for bad_code in bad_codes:
            del output[bad_code]
        missing = list(filter(lambda x: x not in codes, output.keys()))
        if missing:
            logging.warning(f'No population data available for {missing}')
        return output

    def measure(self):
        response = self.call('/rest/v1/all', headers=self.headers)
        return {entry['alpha2Code']: entry['population'] for entry in response}

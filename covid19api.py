from src.covid19api import covid19api
from src.configuration import get_configuration

if __name__ == '__main__':
    print('hello')
    covid19api(get_configuration())

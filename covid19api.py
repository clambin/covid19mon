from covid19.apiserver.apiserver import main
from covid19.apiserver.configuration import get_configuration

if __name__ == '__main__':
    main(get_configuration())

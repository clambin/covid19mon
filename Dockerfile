FROM python:3.8-slim
MAINTAINER Christophe Lambin <christophe.lambin@gmail.com>

WORKDIR /app

EXPOSE 8080
RUN groupadd -g 1000 abc && \
    useradd -u 1000 -g abc abc && \
    pip install --upgrade pip && \
    pip install pipenv
RUN if [ "$(uname -m)" = "armv7l" ]; then \
        echo "[global]" > /etc/pip.conf && \
        echo "extra-index-url=https://www.piwheels.org/simple" >> /etc/pip.conf && \
        apt-get update && \
        apt-get install -y libpq5 libunistring2 libcom-err2 && \
        pip install psycopg2-binary; \
    fi
COPY Pip* ./
RUN pipenv install --system --deploy --ignore-pipfile
COPY *.py ./
COPY src/*.py ./src/

USER abc
ENTRYPOINT ["/usr/local/bin/python3", "covid19.py"]
CMD []

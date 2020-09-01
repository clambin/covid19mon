FROM python:3.7-slim
MAINTAINER Christophe Lambin <christophe.lambin@gmail.com>

WORKDIR /app

EXPOSE 8080
RUN groupadd -g 1000 abc && \
    useradd -u 1000 -g abc abc
RUN pip install --upgrade pip && \
    pip install pipenv
COPY Pip* ./
RUN pipenv install --system --deploy --ignore-pipfile
COPY *.py ./
COPY src/*.py ./src

USER abc
ENTRYPOINT ["/usr/local/bin/python3", "covid19.py"]
CMD []

FROM python:3.7-alpine

WORKDIR /app

EXPOSE 8080
RUN addgroup -S -g 1000 abc && \
    adduser -S --uid 1000 --ingroup abc abc
RUN pip install --upgrade pip && \
    pip install pipenv
COPY Pip* ./
RUN pipenv install --system --deploy --ignore-pipfile
COPY *.py ./

USER abc
ENTRYPOINT ["/usr/local/bin/python3", "covid19mon.py"]
CMD []

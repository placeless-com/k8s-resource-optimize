FROM python:3.9-slim

COPY placeless-controller/src src
COPY ../placeless-db-client/ placeless-db-client/
COPY placeless-controller/requirements.txt requirements.txt
RUN pip install placeless-db-client/
RUN pip install -r requirements.txt

WORKDIR src
CMD kopf run handlers.py --verbose

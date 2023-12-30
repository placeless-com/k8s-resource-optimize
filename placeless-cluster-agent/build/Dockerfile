FROM python:3.9-slim

COPY placeless-cluster-agent/app/ app/
COPY ../../placeless-db-client/ placeless-db-client/
COPY placeless-cluster-agent/build/requirements.txt requirements.txt
RUN pip install placeless-db-client/
RUN pip install -r requirements.txt

WORKDIR app
CMD ["python3","main.py"]

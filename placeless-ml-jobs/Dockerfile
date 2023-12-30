FROM python:3.9-slim
COPY placeless-ml-jobs/app/ /app

COPY ../placeless-db-client/ placeless-db-client/
COPY placeless-ml-jobs/requirements.txt requirements.txt
RUN pip install placeless-db-client/
RUN pip install -r requirements.txt

WORKDIR /app
ENTRYPOINT ["invoke"]

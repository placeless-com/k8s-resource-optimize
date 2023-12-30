# Use an official Python runtime as a parent image
FROM python:3.9-slim

ENV PLACELESS_MYSQL_HOSTNAME url
ENV PLACELESS_MYSQL_PASSWORD password
ENV PLACELESS_MYSQL_USERNAME user
ENV PLACELESS_MYSQL_DB placeless

COPY placeless-view /app
COPY placeless-db-client/ placeless-db-client/

RUN pip install placeless-db-client/

COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
WORKDIR /app

EXPOSE 8080
CMD ["streamlit", "run", "dashboard.py"]

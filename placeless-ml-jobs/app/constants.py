import os

BUCKET_NAME = os.getenv('PLACELESS_S3_BUCKET', "")
REGION = os.getenv('PLACELESS_S3_BUCKET_REGION', "us-east-1")
MYSQL_HOST = os.environ.get("PLACELESS_MYSQL_HOSTNAME", "127.0.0.1")
MYSQL_USER = os.environ.get("PLACELESS_MYSQL_USERNAME", "placeless")
MYSQL_PASSWORD = os.environ.get("PLACELESS_MYSQL_PASSWORD", "placeless")
MYSQL_DB = os.environ.get("PLACELESS_MYSQL_DB", "placeless")
PDB_ARGS = MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

import boto3
import pickle
from constants import BUCKET_NAME


def get_workloads_from_S3(workloads_id):
    session = connect_to_bucket()
    s3 = session.resource('s3')
    my_pickle = pickle.loads(s3.Bucket(BUCKET_NAME).Object(f"placeless/{workloads_id}.pickle").get()['Body'].read())
    return my_pickle


def send_to_s3(obj):
    print('connecting...')
    session = connect_to_bucket()
    s3 = session.resource('s3')
    file_name = obj.get_id()
    print('dumping...')
    binary_file = pickle.dumps(obj)
    print('putting the obj....')
    s3.Bucket(BUCKET_NAME).put_object(Key=f'placeless/{file_name}.pickle', Body=binary_file)


def connect_to_bucket():
    return boto3.Session()

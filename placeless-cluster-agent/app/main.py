from datetime import datetime
import os
import threading
import logging
import json

from kubernetes.config import load_kube_config, load_incluster_config, config_exception
from kubernetes.client import CustomObjectsApi
from lib import MetricDataCollector, MetricsProcessor



TIME_INTERVAL = 60
CLUSTER_NAME = os.getenv("PLACELESS_CLS_NAME", "cluster-test")

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
logging.info(f"logging level set to {logging.root.level}")


def get_workloads_name_from_query_line(data):
    return [workload_name[4] for workload_name in data]

def set_kubernetes_config_option():
    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d %H:%M:%S")
    threading.Timer(TIME_INTERVAL, set_kubernetes_config_option).start()
    pods_usage = cust.list_cluster_custom_object('metrics.k8s.io', 'v1beta1', 'pods')
    deployment_metadata = cust.list_cluster_custom_object('apps', 'v1', 'deployments')
    data_metric = MetricDataCollector(pods_usage, deployment_metadata)
    logging.info(f"metrics collected successfully")
    metric_processor = MetricsProcessor(CLUSTER_NAME)
    parsed_data = metric_processor.parse_raw_data(json.dumps(data_metric.__dict__, indent=4), date_time)
    logging.info("Successfully processed metrics")
    metric_processor.upload_to_mysql(parsed_data)
    logging.info(f"Ingested <NUMBER_OF_METRICS> metrics from cluster {CLUSTER_NAME}")

    logging.info("update workload ")
    workloads_name = get_workloads_name_from_query_line(parsed_data)



try:
    load_incluster_config()
    logging.info("use kubernetes in-cluster service account")
except config_exception.ConfigException:
    load_kube_config()
    logging.info("use kubernetes local config file")


if __name__ == "__main__":
    cust = CustomObjectsApi()
    set_kubernetes_config_option()
import os
import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
logging.info(f"logging level set to {logging.root.level}")


class ExportMetricDataField:
    def __init__(self, obj_metrics_v1beta1 ):
        self.timestamp = obj_metrics_v1beta1['timestamp']
        self.namespace = obj_metrics_v1beta1['metadata']['namespace']
        self.name = obj_metrics_v1beta1['metadata']['name']
        self.memory_usage = obj_metrics_v1beta1['containers'][0]['usage']['memory']
        self.cpu_usage = obj_metrics_v1beta1['containers'][0]['usage']['cpu']


class ExportMetaDataField:
    def __init__(self, obj_deployment_v1):
        self.limits = self.__return_resources_dict(obj_deployment_v1).get("limits", {})
        self.requests = self.__return_resources_dict(obj_deployment_v1).get('requests', {})
        self.deployment_name = obj_deployment_v1['metadata']['name']

    @staticmethod
    def __return_resources_dict(dict):
        return dict['spec']['template']['spec']['containers'][0]['resources']


class MetricDataCollector:
    def __init__(self, obj_metrics_v1beta1, obj_deployment_v1):
        self.data_metric = self.__get_data_metric_list(obj_metrics_v1beta1['items'])
        self.metadata = self.__get_metadata_list(obj_deployment_v1['items'])

    @staticmethod
    def __get_data_metric_list(obj_deployment_v1):
        return {obj['metadata']['name']: ExportMetricDataField(obj).__dict__ for obj in obj_deployment_v1}

    @staticmethod
    def __get_metadata_list(obj_metrics_v1beta1):
        return {obj['metadata']['name']: ExportMetaDataField(obj).__dict__ for obj in obj_metrics_v1beta1}

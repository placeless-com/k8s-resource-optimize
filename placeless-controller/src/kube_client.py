import kubernetes as kube
import logging


class KubeClient:
    def __init__(self):
        try:
            kube.config.load_incluster_config()
            logging.info("use kubernetes in-cluster service account")
        except kube.config.config_exception.ConfigException:
            kube.config.load_config()
            logging.info("use kubernetes local config file")
        self.__kube_client = kube

    @property
    def kube_client(self):
        return self.__kube_client

import threading
import time
from helpers import update_workload_monitored_by_placeless


class ScheduleResourcesUpdateByPlaceless(threading.Thread):
    TIME_SLEEP = 60

    def __init__(self, kube):
        super(ScheduleResourcesUpdateByPlaceless, self).__init__()
        self.kube = kube

    def run(self):
        while True:
            update_workload_monitored_by_placeless(self.kube.client)
            time.sleep(self.TIME_SLEEP)


from api import ResourcesAction
import kopf
import logging
from helpers import is_workload_exist_in_placeless, get_container_name, create_new_workload
from kube_client import KubeClient
from schedule_resources_update_by_placeless import ScheduleResourcesUpdateByPlaceless

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
logging.info(f"logging level set to {logging.root.level}")
kube_client = KubeClient().kube_client


@kopf.on.startup()
def config(settings: kopf.OperatorSettings, **_):
    settings.admission.managed = 'auto.kopf.dev'
    settings.admission.server = kopf.WebhookServer(cafile='client-cert.pem')
    schedule_update_resources = ScheduleResourcesUpdateByPlaceless(kube_client)
    schedule_update_resources.daemon = True
    schedule_update_resources.start()
    schedule_update_resources.join()

'''
kopf decorator @timer use Async function on each deployment collected by the filter
'''


@kopf.timer('deployment', idle=10, interval=60)
def sync_deployment_monitored_by_placeless(spec, body, **kwargs):
    try:
        is_workload_exist_in_placeless(body)
        logging.info(f"deployment {body['metadata']['name']} exist.")
    except AssertionError:
        logging.warning(f"deployment {body['metadata']['name']} does not exist!")
        create_new_workload(body, spec)


@kopf.on.update('deployment', labels={'placeless/enabled': 'true',
                                      'placeless/container_name': kopf.PRESENT}, retries=2)
def set_resources_deployment(body, spec, patch, check_required=True, **kwargs):
    container_name, container_index = get_container_name(body)
    placeless_resources_adjustment = ResourcesAction().get_workload_resources(body['metadata']['name'],
                                                                              body['metadata']['namespace'])
    deployment_current_resources = spec['template']['spec']['containers'][container_index]
    for resource_spec in placeless_resources_adjustment:
        for resource_type, value in placeless_resources_adjustment[resource_spec].items():
            if value == 0:
                continue
            try:
                deployment_current_resources['resources'][resource_spec]
            except KeyError:
                deployment_current_resources['resources'][resource_spec] = {}
            deployment_current_resources['resources'][resource_spec][resource_type] = value

    try:
        v1 = kube_client.client.AppsV1Api()
        v1.patch_namespaced_deployment(
            name=body['metadata']['name'],
            namespace=body['metadata']['namespace'],
            body={'spec': {'template': {'spec': {'containers': [deployment_current_resources]}}}}
        )
        logging.info(f"Successfully set {container_name} from placeless workload table, {deployment_current_resources}")
    except Exception as err:
        logging.error(f"Error while set resources for {body['metadata']['name']} - {err}")




from math import floor
from typing import Union

from kubernetes import client
from kubernetes.client import ApiException
from pydantic import BaseModel, root_validator
from pylon.core.tools import log

from tools import session_project
from ..utils import get_cluster_capacity, get_core_api
from ...integrations.models.pd.integration import SecretField


class IntegrationModel(BaseModel):
    k8s_token: Union[SecretField, str]
    hostname: str
    namespace: str = "default"
    secure_connection: bool = False

    def _prepare_configuration(self) -> client.CoreV1Api:
        core_api = get_core_api(
            self.k8s_token.unsecret(session_project.get()),
            self.hostname,
            self.secure_connection
        )
        return core_api

    def check_connection(self) -> bool:
        core_api = self._prepare_configuration()
        try:
            core_api.read_namespace_status(self.namespace)
        except ApiException as e:
            log.info("Exception when calling CoreV1Api->read_namespace_status: %s\n" % e)
            return False
        return True

    def get_namespaces(self):
        core_api = self._prepare_configuration()
        namespaces = core_api.list_namespace()
        return [item.metadata.name for item in namespaces.items]


class PerformanceBackendTestModel(IntegrationModel):
    id: int
    cpu_cores_limit: int
    memory_limit: int
    concurrency: int

    @root_validator
    def check_capacity(cls, values):
        token = SecretField.parse_obj(values["k8s_token"])
        core_api = get_core_api(
            token.unsecret(session_project.get()),
            values["hostname"],
            values["secure_connection"]
        )
        capacity = get_cluster_capacity(core_api, values["namespace"])
        required_cpu = values["cpu_cores_limit"] * values["concurrency"]
        required_memory = values["memory_limit"] * values["concurrency"]
        available_cpu_cores = floor(capacity["cpu"] / 1000)
        available_memory = floor(capacity["memory"] / 1024)
        assert values["concurrency"] <= capacity["pods"], "Not enough runners"
        msg = f"Not enough capacity. " \
              f"Test requires {required_cpu} cores and {required_memory}Gb memory"
        assert (
                required_cpu <= available_cpu_cores and required_memory <= available_memory), msg

        return values


class PerformanceUiTestModel(PerformanceBackendTestModel):
    ...

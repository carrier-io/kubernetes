from enum import Enum
from typing import Union, Optional

from kubernetes import client
from kubernetes.client import ApiClient, ApiException
from pydantic import BaseModel

from tools import session_project
from ...integrations.models.pd.integration import SecretField
from pylon.core.tools import log


class IntegrationModel(BaseModel):
    k8s_token: Union[SecretField, str]
    hostname: str
    namespace: str = "default"
    secure_connection: bool = False

    def _prepare_configuration(self) -> client.CoreV1Api:
        configuration = client.Configuration()

        configuration.api_key_prefix['authorization'] = 'Bearer'
        configuration.api_key['authorization'] = self.k8s_token.unsecret(session_project.get())
        configuration.host = self.hostname
        configuration.verify_ssl = self.secure_connection

        core_api = client.CoreV1Api(ApiClient(configuration))
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


class PerformanceUiTestModel(PerformanceBackendTestModel):
    ...

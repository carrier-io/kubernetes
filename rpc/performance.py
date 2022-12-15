from typing import Optional

from pydantic import ValidationError
from pylon.core.tools import web, log

from tools import rpc_tools
from ..models.integration_pd import PerformanceBackendTestModel, PerformanceUiTestModel


class RPC:
    integration_name = 'kubernetes'

    @web.rpc(f'backend_performance_test_create_integration_validate_{integration_name}')
    @rpc_tools.wrap_exceptions(ValidationError)
    def backend_performance_test_create_integration_validate(self, data: dict,
            pd_kwargs: Optional[dict] = None, **kwargs
    ) -> dict:
        if not pd_kwargs:
            pd_kwargs = {}
        log.info(f"before validation {data=}")
        integration = self.context.rpc_manager.call.integrations_get_by_id(data["id"])
        pd_object = PerformanceBackendTestModel(**{**integration.settings, **data})
        pd_object.k8s_token = pd_object.k8s_token.value
        return pd_object.dict(**pd_kwargs)

    @web.rpc(f'backend_performance_execution_json_config_{integration_name}')
    @rpc_tools.wrap_exceptions(RuntimeError)
    def backend_make_execution_json_config(self, integration_data: dict) -> dict:
        """ Prepare execution_json for this integration """
        return integration_data

    @web.rpc(f'ui_performance_test_create_integration_validate_{integration_name}')
    @rpc_tools.wrap_exceptions(ValidationError)
    def ui_performance_test_create_integration_validate(self, data: dict,
            pd_kwargs: Optional[dict] = None,
            **kwargs
    ) -> dict:
        if not pd_kwargs:
            pd_kwargs = {}
        integration = self.context.rpc_manager.call.integrations_get_by_id(data["id"])
        pd_object = PerformanceUiTestModel(**{**integration.settings, **data})
        pd_object.k8s_token = pd_object.k8s_token.value
        return pd_object.dict(**pd_kwargs)

    @web.rpc(f'ui_performance_execution_json_config_{integration_name}')
    @rpc_tools.wrap_exceptions(RuntimeError)
    def ui_make_execution_json_config(self, integration_data: dict) -> dict:
        """ Prepare execution_json for this integration """
        return integration_data

from typing import Optional

from pydantic import ValidationError
from pylon.core.tools import web

from tools import rpc_tools, secrets_tools
from ..models.integration_pd import SecretField


class RPC:
    integration_name = 'kubernetes'

    @web.rpc(f'{integration_name}_process_secrets')
    @rpc_tools.wrap_exceptions(RuntimeError)
    def process_secrets(self, integration_data: dict) -> dict:
        project_id = integration_data["project_id"]
        secrets = secrets_tools.get_project_hidden_secrets(project_id)
        settings: dict = integration_data["settings"]

        for field, value in settings.items():
            try:
                secret_field = SecretField.parse_obj(value)
            except ValidationError:
                continue
            if secret_field.from_secrets:
                continue
            secret_path = f"{field}_{integration_data['id']}"
            secrets[secret_path] = secret_field.value
            settings[field] = "{{" + f"secret.{secret_path}" + "}}"

        secrets_tools.set_project_hidden_secrets(integration_data["project_id"], secrets)

        return settings

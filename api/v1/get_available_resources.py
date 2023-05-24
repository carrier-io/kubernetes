from math import floor

from flask import request
from flask_restful import Resource
from pydantic import ValidationError

from tools import session_project, api_tools
from ...models.integration_pd import IntegrationModel
from ...utils import get_core_api, get_cluster_capacity


class ProjectAPI(api_tools.APIModeHandler):
    ...


class AdminAPI(api_tools.APIModeHandler):
    ...


class API(api_tools.APIBase):
    url_params = [
        '<string:mode>',
        ''
    ]

    mode_handlers = {
        'default': ProjectAPI,
        'administration': AdminAPI,
    }

    def post(self, mode):
        try:
            settings: IntegrationModel = IntegrationModel.parse_obj(request.json)
        except ValidationError as e:
            return e.errors(), 400

        core_api = get_core_api(
            settings.k8s_token.unsecret(session_project.get()),
            settings.hostname,
            settings.secure_connection
        )
        try:
            capacity = get_cluster_capacity(core_api, settings.namespace)
        except Exception as e:
            return str(e), 400
        capacity["cpu"] = floor(capacity["cpu"] / 1000)
        capacity["memory"] = floor(capacity["memory"] / 1024)
        return capacity, 200

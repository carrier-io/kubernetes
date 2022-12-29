from math import floor

from flask import request
from flask_restful import Resource
from pydantic import ValidationError

from tools import session_project
from ...models.integration_pd import IntegrationModel
from ...utils import get_core_api, get_cluster_capacity


class API(Resource):

    def __init__(self, module):
        self.module = module

    def post(self):
        try:
            settings: IntegrationModel = IntegrationModel.parse_obj(request.json)
        except ValidationError as e:
            return e.errors(), 400

        core_api = get_core_api(
            settings.k8s_token.unsecret(session_project.get()),
            settings.hostname,
            settings.secure_connection
        )
        capacity = get_cluster_capacity(core_api, settings.namespace)
        capacity["cpu"] = floor(capacity["cpu"] / 1000)
        capacity["memory"] = floor(capacity["memory"] / 1024)
        return capacity, 200

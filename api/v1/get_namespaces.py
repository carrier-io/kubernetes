from flask import request
from flask_restful import Resource
from pydantic import ValidationError
from tools import api_tools

from ...models.integration_pd import IntegrationModel


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
            settings = IntegrationModel.parse_obj(request.json)
        except ValidationError as e:
            return e.errors(), 400

        namespaces: list = settings.get_namespaces()
        return namespaces, 200

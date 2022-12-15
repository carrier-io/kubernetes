from pylon.core.tools import log, web


class Slot:
    integration_name = 'kubernetes'
    section_name = 'clouds'

    @web.slot(f'integrations_{section_name}_content')
    def integration_create_modal_content(self, context, slot, payload):
        with context.app.app_context():
            return self.descriptor.render_template(
                'integration/content.html'
            )

    @web.slot(f'integrations_{section_name}_scripts')
    def integration_create_modal_scripts(self, context, slot, payload):
        with context.app.app_context():
            return self.descriptor.render_template(
                'integration/scripts.html',
            )

    @web.slot(f'integration_card_{integration_name}')
    def integration_card(self, context, slot, payload):
        """
        :param payload: Holds pydantic model of the integration
        """
        with context.app.app_context():
            return self.descriptor.render_template(
                'integration/card.html',
                integration_data=payload
            )

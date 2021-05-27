from oscar.apps.order import processing
from oscar.apps.communication.models import CommunicationEventType
from oscar.apps.order.utils import OrderDispatcher

import logging

logger = logging.getLogger(__name__)

class EventHandler(processing.EventHandler):

    def handle_shipping_event(self, order, event_type, lines,
                              line_quantities, **kwargs):
        self.validate_shipping_event(
            order, event_type, lines, line_quantities, **kwargs
        )

        if event_type.name == 'shipped':
            # Already taken payment in checkout so not need handle payment here
            self.consume_stock_allocations(
                order, lines, line_quantities
            )

        shipping_event = self.create_shipping_event(
            order, event_type, lines, line_quantities,
            reference=kwargs.get('reference', None)
        )

        self.send_user_message(order, lines, 'SHIPPING_PLACED')

    def send_user_message(self, order, lines, code, **kwargs):

        ctx = {'user': order.email,
               'order': order,
               'lines': lines}


        event_type = CommunicationEventType.objects.get(code=code)

        # Commented out as not sure what 'CommunicationEvent' is
        # CommunicationEvent._default_manager.create(
        #     order=order, event_type=event_type)

        messages = event_type.get_messages(ctx)

        if messages and messages['body']:
            logger.info("Order #%s - sending %s messages", order.number, code)
            dispatcher = OrderDispatcher(logger)
            dispatcher.dispatch_order_messages(order, messages,
                                               event_type, **kwargs)

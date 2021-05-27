from django.conf import settings
from django.db import transaction
from django.core.mail import send_mail
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.utils.translation import gettext_lazy as _

from oscar.apps.order.utils import OrderCreator as CoreOrderCreator
from oscar.apps.order.utils import OrderNumberGenerator
from oscar.apps.order.utils import OrderDispatcher as CoreOrderDispatcher
from oscar.apps.communication.models import CommunicationEventType

from oscar.core.loading import get_class, get_model
from oscar.apps.order.signals import order_placed

from decimal import Decimal as D

import logging

logger = logging.getLogger(__name__)


Order = get_model('order', 'Order')

class OrderCreator(CoreOrderCreator):

    def place_order(self, basket, total,  # noqa (too complex (12))
                    shipping_method, shipping_charge, user=None,
                    shipping_address=None, billing_address=None,
                    order_number=None, status=None, request=None, surcharges=None, **kwargs):
        """
        Placing an order involves creating all the relevant models based on the
        basket and session data.
        """
        if basket.is_empty:
            raise ValueError(_("Empty baskets cannot be submitted"))
        if not order_number:
            generator = OrderNumberGenerator()
            order_number = generator.order_number(basket)
        if not status and hasattr(settings, 'OSCAR_INITIAL_ORDER_STATUS'):
            status = getattr(settings, 'OSCAR_INITIAL_ORDER_STATUS')

        if Order._default_manager.filter(number=order_number).exists():
            raise ValueError(_("There is already an order with number %s")
                             % order_number)

        with transaction.atomic():

            kwargs['surcharges'] = surcharges
            # Ok - everything seems to be in order, let's place the order
            order = self.create_order_model(
                user, basket, shipping_address, shipping_method, shipping_charge,
                billing_address, total, order_number, status, request, **kwargs)
            for line in basket.all_lines():
                self.create_line_models(order, line)
                self.update_stock_records(line)

            for voucher in basket.vouchers.select_for_update():
                if not voucher.is_active():  # basket ignores inactive vouchers
                    basket.vouchers.remove(voucher)
                else:
                    available_to_user, msg = voucher.is_available_to_user(user=user)
                    if not available_to_user:
                        raise ValueError(msg)

            # Record any discounts associated with this order
            for application in basket.offer_applications:
                # Trigger any deferred benefits from offers and capture the
                # resulting message
                application['message'] \
                    = application['offer'].apply_deferred_benefit(basket, order,
                                                                  application)
                # Record offer application results
                if application['result'].affects_shipping:
                    # Skip zero shipping discounts
                    shipping_discount = shipping_method.discount(basket)
                    if shipping_discount <= D('0.00'):
                        continue
                    # If a shipping offer, we need to grab the actual discount off
                    # the shipping method instance, which should be wrapped in an
                    # OfferDiscount instance.
                    application['discount'] = shipping_discount
                self.create_discount_model(order, application)
                self.record_discount(application)

            for voucher in basket.vouchers.all():
                self.record_voucher_usage(order, voucher, user)

        # Send signal for analytics to pick up
        order_placed.send(sender=self, order=order, user=user)

        # Send admins order confirmation through dispatcher
        for admin in settings.ADMIN_EMAIL_ADDRESS:
            ctx = {'user': admin,
                   'order': order}

            commtype_code = "ADMIN_ORDER_MAIL"

            event_type = CommunicationEventType.objects.get(code=commtype_code)

            messages = event_type.get_messages(ctx)

            if messages and messages['body']:
                logger.info("Order #%s - sending %s messages", order.number, commtype_code)
                dispatcher = OrderDispatcher(logger)
                dispatcher.dispatch_admin_messages(order, messages,
                                                   event_type, **kwargs)

        return order


class OrderDispatcher(CoreOrderDispatcher):

    def dispatch_admin_messages(self, order, messages, event_code, attachments=None, **kwargs):
        """
        Dispatch order-related messages to the admin.
        """
        self.dispatcher.logger.info("Order #%s - sending %s messages", order.number, event_code)

        for admin in settings.ADMIN_EMAIL_ADDRESS:
            dispatched_messages = self.dispatcher.dispatch_admin_messages(admin, messages, attachments)
            try:
                event_type = CommunicationEventType.objects.get(code=event_code)
            except CommunicationEventType.DoesNotExist:
                event_type = None

        self.create_communication_event(order, event_type, dispatched_messages)

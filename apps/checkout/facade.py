from django.utils import timezone
import stripe
from django.apps import apps
import logging
import os

logger = logging.getLogger(__name__)
Source = apps.get_model('payment', 'Source')
Order = apps.get_model('order', 'Order')

# import stripe keys
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', None)
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', None)
STRIPE_CURRENCY = os.environ.get('STRIPE_CURRENCY', None)


class Facade(object):

    def __init__(self):
        stripe.api_key = STRIPE_SECRET_KEY

    @staticmethod
    def get_friendly_decline_message(error):
        return 'The transaction was declined by your bank - please check your bankcard details and try again'

    @staticmethod
    def get_friendly_error_message(error):
        return 'An error occurred when communicating with the payment gateway.'

    def create_checkout_session(self, basket, total):
        line_items_summary = ", ".join(["{0}x{1}".format(l.quantity, l.product.title) for l in basket.lines.all()])
        line_items = [{
            "name": line_items_summary,
            "amount": int(100 * total.incl_tax),
            "currency": "gbp",
            "quantity": 1,
        }]

        basket.freeze()

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url="http://http://127.0.0.1:8000/checkout/preview/" + str(basket.id),
            cancel_url="http://http://127.0.0.1:8000/checkout/payment-cancel/" + str(basket.id),
            payment_intent_data={
                'capture_method': 'manual',
            },
        )
        return session

    def retrieve_payment_intent(self, pi):
        return stripe.PaymentIntent.retrieve(pi)

    def capture(self, order_number, **kwargs):
        """
        if capture is set to false in charge, the charge will only be pre-authorized
        one need to use capture to actually charge the customer
        """
        logger.info("Initiating payment capture for order '%s' via stripe" % (order_number))
        try:
            order = Order.objects.get(number=order_number)
            payment_source = Source.objects.get(order=order)
            # get charge_id from source
            charge_id = payment_source.reference

            stripe.PaymentIntent.modify(
                charge_id,
                receipt_email=order.user.email
            )

            stripe.PaymentIntent.capture(charge_id)
            # set captured timestamp
            payment_source.date_captured = timezone.now()
            payment_source.save()
            logger.info("payment for order '%s' (id:%s) was captured via stripe (stripe_ref:%s)" % (order.number, order.id, charge_id))
        except Source.DoesNotExist as e:
            logger.exception('Source Error for order: \'{}\''.format(order_number) )
            raise Exception("Capture Failure could not find payment source for Order %s" % order_number)
        except Order.DoesNotExist as e:
            logger.exception('Order Error for order: \'{}\''.format(order_number) )
            raise Exception("Capture Failure Order %s does not exist" % order_number)

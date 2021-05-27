from oscar.apps.shipping import methods
from oscar.core import prices
from decimal import Decimal as D

class Standard(methods.FixedPrice):
    code = 'standard'
    name = 'Standard shipping'
    charge_excl_tax = D('1.99')

    def calculate(self, basket):
        return prices.Price(
            currency=basket.currency,
            excl_tax=D('1.99'), incl_tax=D('1.99'))

class Express(methods.FixedPrice):
    code = 'express'
    name = 'Express shipping'
    charge_excl_tax = D('10.00')

    def calculate(self, basket):
        return prices.Price(
            currency=basket.currency,
            excl_tax=D('10.00'), incl_tax=D('10.00'))
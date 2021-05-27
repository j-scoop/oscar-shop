from django.apps import apps
from django.urls import include, path
from django.contrib import admin
from django.conf import settings
from django.conf.urls import url


from shop import views
from apps.checkout.views import StripeSCASuccessResponseView as stripe_success_view
from apps.checkout.views import StripeSCACancelResponseView as stripe_cancel_view


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),

    path('admin/', admin.site.urls),

    url(r'^$', views.home, name='home'),
    url(r'^about/$', views.about, name='about'),
    url(r'^contact/$', views.contact, name='contact'),

    # Oscar urls
    path('', include(apps.get_app_config('oscar').urls[0])),

    # PayPal Express integration...
    path('checkout/paypal/', include('paypal.express.urls')),
    # Dashboard views for Express
    path('dashboard/paypal/express/', apps.get_app_config("express_dashboard").urls),
    # Dashboard views for Express Checkout
    # path('dashboard/paypal/express-checkout/', apps.get_app_config('express_checkout_dashboard').urls),
    path('', include(apps.get_app_config('oscar').urls[0])),

    # stripe redirect views
    url(r'preview/(?P<basket_id>\d+)/$',
        stripe_success_view.as_view(preview=True), name='stripe-preview'),
    url(r'payment-cancel/(?P<basket_id>\d+)/$',
        stripe_cancel_view.as_view(), name='stripe-cancel'),
        # stripe_cancel_view.as_view(), name='stripe-cancel'),

]

if settings.DEBUG:  # To be removed & amended when pushed to production & not serving images locally
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

from oscar.apps.catalogue.views import ProductDetailView as CoreProductDetailView


class ProductDetailView(CoreProductDetailView):

    def get_template_names(self):
        """
        Return a list of possible templates.

        If an overriding class sets a template name, we use that. Otherwise,
        we try 2 options before defaulting to :file:`catalogue/detail.html`:

            1. :file:`detail-for-upc-{upc}.html`
            2. :file:`detail-for-class-{classname}.html`

        This allows alternative templates to be provided for a per-product
        and a per-item-class basis.
        """
        if self.template_name:
            return [self.template_name]

        return [
            'oscar/%s/detail-for-upc-%s.html' % (
                self.template_folder, self.object.upc),
            'oscar/%s/detail-for-class-%s.html' % (
                self.template_folder, self.object.get_product_class().slug),
            'oscar/%s/detail.html' % self.template_folder]

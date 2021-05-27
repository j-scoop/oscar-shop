from oscar.apps.communication.utils import Dispatcher as CoreDispatcher

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.contrib.auth.models import User


class Dispatcher(CoreDispatcher):
    def send_admin_email_messages(self, recipient_email, messages, from_email=None, attachments=None):
        """
        Send email to recipient, HTML attachment optional. Overriding so admin emails are saved to db.
        """
        from_email = from_email or settings.OSCAR_FROM_EMAIL

        content_attachments, file_attachments = self.prepare_attachments(attachments)

        # Determine whether we are sending a HTML version too
        if messages['html']:
            email = EmailMultiAlternatives(
                messages['subject'],
                messages['body'],
                from_email=from_email,
                to=[recipient_email],
                attachments=content_attachments,
            )
            email.attach_alternative(messages['html'], "text/html")
        else:
            email = EmailMessage(
                messages['subject'],
                messages['body'],
                from_email=from_email,
                to=[recipient_email],
                attachments=content_attachments,
            )
        for attachment in file_attachments:
            email.attach_file(attachment)

        self.logger.info("Sending email to %s" % recipient_email)

        if self.mail_connection:
            self.mail_connection.send_messages([email])
        else:
            email.send()

        # Save admin emails to db

        admin = User.objects.get(email=settings.ADMIN_EMAIL_ADDRESS[0])

        if settings.OSCAR_SAVE_SENT_EMAILS_TO_DB:
            self.create_email(admin, messages, email)

        return email

    def dispatch_admin_messages(self, recipient_email, messages, attachments=None):
        """
        Dispatch one-off messages to explicitly specified recipient email.
        """
        if messages['subject'] and (messages['body'] or messages['html']):
            return self.send_admin_email_messages(recipient_email, messages, attachments=attachments)

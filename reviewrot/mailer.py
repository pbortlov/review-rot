"""
This script is used to send emails
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class Mailer:
    """ A mailer component used to send emails
    """

    DEFAULT_FROM = "do-not-reply@redhat.com"
    DEFAULT_SERVER = "smtp.corp.redhat.com"

    def __init__(self):
        """Returns mailer object
        """
        self._cfg = {}
        self._cfg.setdefault("server", self.DEFAULT_SERVER)
        self._cfg.setdefault("from", self.DEFAULT_FROM)

    def send(self, recipients, subject, text):
        """ Sends email to recipients
        :param list recipiencts : recipients of email
        :param string subject : subject of the email
        :pram string text: text of the email
        """
        sender = self._cfg["from"]
        msg = MIMEMultipart('alternative')
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        server = smtplib.SMTP(self._cfg["server"])
        part = MIMEText(text, 'html', 'utf-8')
        msg.attach(part)

        server.sendmail(sender, recipients, msg.as_string())
        server.quit()

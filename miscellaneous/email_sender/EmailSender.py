"""
Este script permite el envío de correos electrónicos a través del servidor SMTP de Gmail,
incluyendo la posibilidad de agregar destinatarios en copia oculta (BCC) y adjuntar archivos.
Las credenciales y configuraciones se cargan desde un archivo .env para mayor seguridad.
"""

import logging
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from dotenv import load_dotenv

# Cargar variables de entorno desde un archivo .env
load_dotenv()

SMTP_GMAIL__USER: str = os.getenv("SMTP_GMAIL__USER")
SMTP_GMAIL__APP_PASSWORD: str = os.getenv("SMTP_GMAIL__APP_PASSWORD")
SMTP_GMAIL__FILES: str = os.getenv("SMTP_GMAIL__FILES")
SMTP_GMAIL__LOG_FILE: str = os.getenv("SMTP_GMAIL__LOG_FILE")

# Configuración del log
logging.basicConfig(
    filename=SMTP_GMAIL__LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)


class EmailSender:
    """
    Clase para enviar correos electrónicos utilizando el servidor SMTP de Gmail.

    :param user_gmail: Dirección de correo de Gmail.
    :param app_password: Contraseña de la aplicación generada en Gmail.
    """

    def __init__(self, user_gmail: str, app_password: str) -> None:
        self.user_gmail = user_gmail
        self.app_password = app_password
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def send_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        attachments: Optional[str] = None,
        bcc_addresses: Optional[str] = None,
    ):
        """
        Envía un correo electrónico con los detalles especificados.

        :param to_address: Dirección de correo del destinatario.
        :param subject: Asunto del correo.
        :param body: Cuerpo del correo.
        :param attachments: Archivos adjuntos separados por comas (opcional).
        :param bcc_addresses: Direcciones de correo en copia oculta separadas por comas (opcional).
        :return: None
        """
        logging.debug(
            f'Preparando el envío de correo a {to_address} con asunto "{subject}".'
        )

        try:
            # Crear el mensaje
            msg = MIMEMultipart()
            # Agregar ususario que envia el correo
            msg["From"] = self.user_gmail
            # Agregar destinatarios
            msg["To"] = ", ".join([to_address.replace(" ", "")])
            # Agregar destinatarios en copia oculta
            if bcc_addresses:
                msg["Bcc"] = ", ".join([bcc_addresses.replace(" ", "")])
            # Agregar asunto
            msg["Subject"] = subject

            # Agregar el cuerpo del mensaje
            msg.attach(MIMEText(body, "plain"))

            # Crear lista de adjuntos en el caso de que no sea nulo
            if attachments:
                attachments = attachments.replace(" ", "").split(",")

                # Adjuntar archivos
                for file in attachments:
                    logging.debug(f"Adjuntando archivo: {file}")
                    attachment = MIMEBase("application", "octet-stream")
                    with open(file, "rb") as attachment_file:
                        attachment.set_payload(attachment_file.read())
                    encoders.encode_base64(attachment)
                    attachment.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(file)}",
                    )
                    msg.attach(attachment)

            # Enviar el mensaje
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                logging.debug("Conectando al servidor SMTP...")
                server.starttls()
                server.login(self.user_gmail, self.app_password)
                server.send_message(msg)
                logging.info(f"Correo enviado exitosamente a {to_address}.")
        except Exception as e:
            logging.error(f"Error al enviar el correo: {str(e)}")


if __name__ == "__main__":
    email_sender = EmailSender(SMTP_GMAIL__USER, SMTP_GMAIL__APP_PASSWORD)
    to_address = "ctacoronte@itccanarias.org"
    bcc_addresses = "itc.eerr.info@gmail.com"
    subject = "Prueba de envío de correo"
    body = "Este es el cuerpo del correo. Adjunto un archivo docx. Aquí hay correos en CCO."
    attachments = SMTP_GMAIL__FILES

    email_sender.send_email(to_address, subject, body, attachments, bcc_addresses)

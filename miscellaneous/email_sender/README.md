# Email Sender

Este proyecto permite el envío de correos electrónicos a través del servidor SMTP de Gmail, incluyendo la posibilidad de agregar destinatarios en copia oculta (BCC) y adjuntar archivos. Las credenciales y configuraciones se cargan desde un archivo `.env` para mayor seguridad.

## Variables esperadas en el archivo .env

El archivo `.env` debe contener las siguientes variables:

- `SMTP_GMAIL__USER`: Dirección de correo de Gmail.
- `SMTP_GMAIL__APP_PASSWORD`: Contraseña de la aplicación generada en Gmail.
- `SMTP_GMAIL__FILES`: Archivos adjuntos separados por comas.
- `SMTP_GMAIL__LOG_FILE`: Ruta del archivo de log.

Ejemplo de archivo `.env`:
```env
SMTP_GMAIL__USER=my-user@gmail.com
SMTP_GMAIL__APP_PASSWORD=myapppassword
SMTP_GMAIL__FILES=/path_file1,/path_file2
SMTP_GMAIL__LOG_FILE=/var/log/log_email_sender.log
```

---
Para obtener la contraseña de aplicación, se debe de ir a los ajustes de la cuenta gmail la cual se quiere emplear como servidor SMTP y activar la doble verificación. Una vez se haya completado ese paso, ya es posible generar contraseñas de aplicaciones.

Para más información de cómo obtener la contraseña de aplicación en España, visite el siguiente link: https://support.google.com/accounts/answer/185833?sjid=466537387126917489-EU
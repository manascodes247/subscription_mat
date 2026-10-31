"""Small SMTP adapter used for transactional email."""

import os
import smtplib
from email.message import EmailMessage


def send_password_reset_email(recipient: str, token: str) -> None:
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM")
    if not host or not sender:
        raise RuntimeError("SMTP_HOST and SMTP_FROM must be configured before password reset email can be sent")
    port = int(os.getenv("SMTP_PORT", "587"))
    reset_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173').rstrip('/')}/reset-password?token={token}"
    message = EmailMessage()
    message["Subject"] = "Reset your Brightloop password"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(f"Use this link to reset your Brightloop password. It expires in 30 minutes:\n\n{reset_url}")
    with smtplib.SMTP(host, port, timeout=15) as client:
        if os.getenv("SMTP_STARTTLS", "true").lower() == "true":
            client.starttls()
        username = os.getenv("SMTP_USERNAME")
        password = os.getenv("SMTP_PASSWORD")
        if username and password:
            client.login(username, password)
        client.send_message(message)


def send_invoice_email(recipient: str, invoice_number: str, pdf_bytes: bytes) -> None:
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM")
    if not host or not sender:
        raise RuntimeError("SMTP_HOST and SMTP_FROM must be configured before invoices can be emailed")
    message = EmailMessage()
    message["Subject"] = f"Your Brightloop invoice {invoice_number}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content("Your invoice is attached. Please contact support if you have any questions.")
    message.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=f"{invoice_number}.pdf")
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as client:
        if os.getenv("SMTP_STARTTLS", "true").lower() == "true":
            client.starttls()
        username = os.getenv("SMTP_USERNAME")
        password = os.getenv("SMTP_PASSWORD")
        if username and password:
            client.login(username, password)
        client.send_message(message)

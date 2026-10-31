"""Printable invoice rendering for the Brightloop API."""

from io import BytesIO
import os
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import Invoice


def money(value: Decimal | int | float) -> str:
    currency = os.getenv("BRIGHTLOOP_CURRENCY", "INR")
    return f"{currency} {Decimal(value):,.2f}"


def invoice_number(invoice: Invoice) -> str:
    return f"INV-{invoice.id:06d}"


def render_invoice_pdf(invoice: Invoice) -> bytes:
    """Return a completed, static A4 PDF for a persisted invoice."""
    stream = BytesIO()
    document = SimpleDocTemplate(stream, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("InvoiceTitle", parent=styles["Title"], fontSize=24, textColor=colors.HexColor("#3B2E5A"), alignment=TA_RIGHT)
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=9, leading=12)
    story = []
    company = os.getenv("BRIGHTLOOP_COMPANY_NAME", "Brightloop Software")
    company_address = os.getenv("BRIGHTLOOP_COMPANY_ADDRESS", "Subscription management platform").replace("\n", "<br/>")
    header = Table([[Paragraph(f"<b>{company}</b><br/>{company_address}", styles["BodyText"]), Paragraph("INVOICE", title)]], colWidths=[105 * mm, 70 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.extend([header, Spacer(1, 8 * mm)])
    customer = invoice.customer_name_snapshot or invoice.subscription.customer.full_name
    email = invoice.customer_email_snapshot or invoice.subscription.customer.email
    details = Table([
        [Paragraph(f"<b>Bill to</b><br/>{customer}<br/>{email}", styles["BodyText"]), Paragraph(f"<b>Invoice</b> {invoice_number(invoice)}<br/><b>Issued</b> {invoice.created_at.date().isoformat() if invoice.created_at else ''}<br/><b>Due</b> {invoice.due_on.isoformat()}", small)],
    ], colWidths=[105 * mm, 70 * mm])
    details.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F5FA")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDD7E8")), ("PADDING", (0, 0), (-1, -1), 8)]))
    story.extend([details, Spacer(1, 8 * mm)])
    rows = [["Description", "Qty", "Unit price", "Discount", "Amount"]]
    for line in invoice.lines:
        description = line.product_name + (f" - {line.variant_name}" if line.variant_name else "")
        rows.append([description, str(line.quantity), money(line.unit_price), f"- {money(line.discount_amount)}", money(line.line_total)])
    table = Table(rows, colWidths=[64 * mm, 15 * mm, 30 * mm, 30 * mm, 35 * mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3B2E5A")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDD7E8")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("PADDING", (0, 0), (-1, -1), 7)]))
    story.extend([table, Spacer(1, 6 * mm)])
    totals = Table([["Subtotal", money(invoice.subtotal)], ["Discount", f"- {money(invoice.discount_amount)}"], ["Tax", money(invoice.tax_amount)], ["Total", money(invoice.amount)], ["Outstanding", money(invoice.outstanding_balance)]], colWidths=[45 * mm, 35 * mm], hAlign="RIGHT")
    totals.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("FONTNAME", (0, -2), (-1, -1), "Helvetica-Bold"), ("LINEABOVE", (0, -2), (-1, -2), 0.75, colors.HexColor("#3B2E5A")), ("PADDING", (0, 0), (-1, -1), 5)]))
    story.extend([totals, Spacer(1, 10 * mm), Paragraph(f"<b>Payment instructions</b><br/>{os.getenv('BRIGHTLOOP_PAYMENT_INSTRUCTIONS', 'Payment is due by the due date shown above.')}", small), Spacer(1, 5 * mm), Paragraph(f"Questions? Contact {os.getenv('BRIGHTLOOP_SUPPORT_EMAIL', 'support@brightloop.example')}", small)])
    document.build(story)
    return stream.getvalue()

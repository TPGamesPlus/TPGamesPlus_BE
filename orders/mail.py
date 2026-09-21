import base64
import logging
import threading

from django.conf import settings
from django.template.loader import render_to_string
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Attachment, Disposition, Mail

from orders.item_images import ITEM_CID, LOGO_CID, LOGO_PATH, item_image_path
from orders.models import Order

logger = logging.getLogger(__name__)


def should_send_receipt_email(user):
    if not (getattr(user, "email", "") or "").strip():
        logger.warning("Skipping receipt email for user %s: no email on file", getattr(user, "pk", user))
        return False
    if not settings.SENDGRID_API_KEY:
        logger.warning("Skipping receipt email: SENDGRID_API_KEY is unset")
        return False
    if not settings.SENDGRID_FROM_EMAIL:
        logger.warning("Skipping receipt email: SENDGRID_FROM_EMAIL is unset")
        return False
    return True


def attach_receipt_email_on_close(response, order_id):
    """Start the SendGrid job only after the WSGI server has sent the response body."""
    original_close = response.close
    scheduled = False

    def close(*args, **kwargs):
        nonlocal scheduled
        try:
            return original_close(*args, **kwargs)
        finally:
            if not scheduled:
                scheduled = True
                schedule_receipt_email(order_id)

    response.close = close
    return response


def schedule_receipt_email(order_id):
    thread = threading.Thread(
        target=send_order_receipt_email,
        args=(order_id,),
        name=f"order-receipt-email-{order_id}",
        daemon=True,
    )
    thread.start()


def send_order_receipt_email(order_id):
    try:
        _send_order_receipt_email(order_id)
    except Exception:
        logger.exception("Failed to send receipt email for order %s", order_id)


def _send_order_receipt_email(order_id):
    try:
        order = Order.objects.select_related("user").get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("Skipping receipt email: order %s no longer exists", order_id)
        return

    if not should_send_receipt_email(order.user):
        return

    item_path = item_image_path(order.product_title)
    has_logo = LOGO_PATH.is_file()
    context = {
        "order": order,
        "location_label": order.get_location_display(),
        "formatted_price": f"${order.unit_price:.2f}",
        "formatted_date": order.created_at.strftime("%Y-%m-%d %H:%M UTC"),
        "has_logo": has_logo,
        "has_item_image": item_path is not None,
        "logo_cid": LOGO_CID,
        "item_cid": ITEM_CID,
    }
    html = render_to_string("orders/emails/receipt.html", context)
    plain = render_to_string("orders/emails/receipt.txt", context)

    message = Mail(
        from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
        to_emails=order.user.email.strip(),
        subject=f"Your Tamatem Plus receipt — Order #{order.pk}",
        plain_text_content=plain,
        html_content=html,
    )
    if has_logo:
        message.add_attachment(_inline_attachment(LOGO_PATH, LOGO_CID, "image/png"))
    if item_path is not None:
        message.add_attachment(_inline_attachment(item_path, ITEM_CID, "image/jpeg"))

    SendGridAPIClient(settings.SENDGRID_API_KEY).send(message)
    logger.info("Sent receipt email for order %s to %s", order.pk, order.user.email)


def _inline_attachment(path, content_id, mime_type):
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return Attachment(
        file_content=encoded,
        file_name=path.name,
        file_type=mime_type,
        disposition=Disposition("inline"),
        content_id=content_id,
    )

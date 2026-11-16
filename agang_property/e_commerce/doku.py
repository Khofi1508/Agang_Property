"""DOKU Checkout Sandbox helpers."""

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings


DOKU_CHECKOUT_PATH = '/checkout/v1/payment'
DOKU_NOTIFICATION_PATH = '/payments/doku/notification/'
DOKU_SANDBOX_ENDPOINT = f'https://api-sandbox.doku.com{DOKU_CHECKOUT_PATH}'


class DokuError(Exception):
    """An expected DOKU request or configuration error."""


def _is_https_url(value):
    parsed = urlparse(value or '')
    return parsed.scheme == 'https' and bool(parsed.netloc)


def _is_supported_notification_url(value):
    parsed = urlparse(value or '')
    host = (parsed.hostname or '').lower()
    return (
        parsed.scheme == 'https'
        and bool(host)
        and 'ngrok' not in host
        and parsed.path.rstrip('/') == DOKU_NOTIFICATION_PATH.rstrip('/')
        and not parsed.query
        and not parsed.fragment
    )


def doku_checkout_is_configured():
    """Require credentials and public HTTPS callback/notification endpoints."""
    return bool(
        getattr(settings, 'DOKU_CLIENT_ID', '')
        and getattr(settings, 'DOKU_SHARED_KEY', '')
        and _is_https_url(getattr(settings, 'SITE_BASE_URL', ''))
        and _is_supported_notification_url(getattr(settings, 'DOKU_NOTIFICATION_URL', ''))
    )


def _digest(raw_body):
    return base64.b64encode(hashlib.sha256(raw_body).digest()).decode('ascii')


def _signature(client_id, request_id, timestamp, target, digest, shared_key):
    components = '\n'.join((
        f'Client-Id:{client_id}',
        f'Request-Id:{request_id}',
        f'Request-Timestamp:{timestamp}',
        f'Request-Target:{target}',
        f'Digest:{digest}',
    ))
    mac = hmac.new(shared_key.encode('utf-8'), components.encode('utf-8'), hashlib.sha256).digest()
    return 'HMACSHA256=' + base64.b64encode(mac).decode('ascii')


def create_checkout_payment(payment_order, finish_url):
    if not doku_checkout_is_configured():
        raise DokuError(
            'Konfigurasi DOKU Sandbox belum lengkap. Isi DOKU_CLIENT_ID, DOKU_SHARED_KEY, '
            'SITE_BASE_URL HTTPS, dan DOKU_NOTIFICATION_URL HTTPS non-ngrok di .env.'
        )

    client_id = settings.DOKU_CLIENT_ID
    shared_key = settings.DOKU_SHARED_KEY
    request_id = hashlib.sha256(
        f'{payment_order.invoice_number}:{payment_order.reference}'.encode('utf-8')
    ).hexdigest()
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    amount = int(payment_order.jumlah_dp)
    profile = getattr(payment_order.user, 'profile', None)
    customer_name = (
        payment_order.user.get_full_name().strip()
        or payment_order.user.username
    )[:255]
    phone = ''.join(ch for ch in (getattr(profile, 'no_telepon', '') or '') if ch.isdigit())
    if phone.startswith('0'):
        phone = '62' + phone[1:]
    elif phone and not phone.startswith('62'):
        phone = '62' + phone

    payload = {
        'order': {
            'amount': amount,
            'invoice_number': payment_order.invoice_number,
            'currency': 'IDR',
            'callback_url': finish_url,
            'callback_url_result': finish_url,
            'language': 'ID',
            'auto_redirect': True,
            'line_items': [{
                'id': str(payment_order.properti.kode_properti or payment_order.properti_id)[:64],
                'name': f'Down Payment - {payment_order.properti.nama_properti}'[:255],
                'quantity': 1,
                'price': amount,
            }],
        },
        'payment': {'payment_due_date': 1440},
        'customer': {
            'id': str(payment_order.user_id),
            'name': customer_name,
            'email': (payment_order.user.email or '')[:128],
        },
        'additional_info': {
            'override_notification_url': settings.DOKU_NOTIFICATION_URL,
            'doku_wallet_notify_url': settings.DOKU_NOTIFICATION_URL,
        },
    }
    if phone:
        payload['customer']['phone'] = phone[:16]

    raw_body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    body_digest = _digest(raw_body)
    signature = _signature(
        client_id,
        request_id,
        timestamp,
        DOKU_CHECKOUT_PATH,
        body_digest,
        shared_key,
    )
    req = Request(
        DOKU_SANDBOX_ENDPOINT,
        data=raw_body,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Client-Id': client_id,
            'Request-Id': request_id,
            'Request-Timestamp': timestamp,
            'Signature': signature,
        },
        method='POST',
    )
    try:
        with urlopen(req, timeout=25) as response:
            response_body = response.read()
    except HTTPError as exc:
        try:
            error_data = json.loads(exc.read().decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            error_data = {}
        error_object = error_data.get('error') if isinstance(error_data, dict) else None
        messages = error_object.get('message') if isinstance(error_object, dict) else None
        if not messages and isinstance(error_data, dict):
            messages = error_data.get('message') or error_data.get('error_messages')
        detail = '; '.join(map(str, messages)) if isinstance(messages, list) else str(messages or '')
        raise DokuError(
            f'DOKU Sandbox menolak permintaan (HTTP {exc.code})'
            f'{": " + detail if detail else ". Periksa Client ID, Shared Key, dan format data."}'
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise DokuError('Website tidak dapat menghubungi DOKU Sandbox. Periksa koneksi server.') from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DokuError('Respons DOKU Sandbox tidak dapat dibaca sebagai JSON.') from exc

    try:
        data = json.loads(response_body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DokuError('Respons DOKU Sandbox tidak valid.') from exc

    payment = (data.get('response') or {}).get('payment') if isinstance(data, dict) else None
    order_response = (data.get('response') or {}).get('order') if isinstance(data, dict) else None
    payment_url = payment.get('url', '') if isinstance(payment, dict) else ''
    token = payment.get('token_id', '') if isinstance(payment, dict) else ''
    parsed_url = urlparse(payment_url)
    payment_host = (parsed_url.hostname or '').lower()
    is_doku_host = payment_host == 'doku.com' or payment_host.endswith('.doku.com')
    if not token or parsed_url.scheme != 'https' or not is_doku_host:
        detail = data.get('message') if isinstance(data, dict) else None
        if isinstance(detail, list):
            detail = '; '.join(map(str, detail))
        raise DokuError(f'DOKU tidak mengembalikan tautan checkout yang valid{": " + str(detail) if detail else "."}')

    session_id = (order_response or {}).get('session_id', '') if isinstance(order_response, dict) else ''
    return token, payment_url, str(session_id)


def verify_notification(raw_body, headers, request_target):
    client_id = headers.get('Client-Id', '')
    request_id = headers.get('Request-Id', '')
    timestamp = headers.get('Request-Timestamp', '')
    received_signature = headers.get('Signature', '')
    shared_key = getattr(settings, 'DOKU_SHARED_KEY', '')

    if (
        not shared_key
        or client_id != getattr(settings, 'DOKU_CLIENT_ID', '')
        or not request_id
        or not timestamp
        or not received_signature.startswith('HMACSHA256=')
    ):
        return False

    expected = _signature(client_id, request_id, timestamp, request_target, _digest(raw_body), shared_key)
    return hmac.compare_digest(expected, received_signature)

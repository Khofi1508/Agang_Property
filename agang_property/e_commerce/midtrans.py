"""Midtrans Snap Sandbox API helpers."""

import base64
import hashlib
import hmac
import json
import re
from datetime import datetime
from urllib.parse import quote, urlparse
from zoneinfo import ZoneInfo
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class MidtransError(Exception):
    pass


def midtrans_is_configured():
    notification_url = urlparse(getattr(settings, 'MIDTRANS_NOTIFICATION_URL', ''))
    return bool(
        getattr(settings, 'MIDTRANS_SERVER_KEY', '')
        and getattr(settings, 'SITE_BASE_URL', '').startswith('https://')
        and notification_url.scheme == 'https'
        and notification_url.netloc
        and notification_url.path.rstrip('/') == '/payments/midtrans/notification'
    )


def _international_phone(phone):
    digits = re.sub(r'\D', '', phone or '')
    if digits.startswith('0'):
        return f'62{digits[1:]}'
    if digits and not digits.startswith('62'):
        return f'62{digits}'
    return digits


def create_snap_transaction(payment_order, finish_url):
    server_key = getattr(settings, 'MIDTRANS_SERVER_KEY', '')
    site_base_url = getattr(settings, 'SITE_BASE_URL', '')
    if not server_key:
        raise MidtransError('Server Key Midtrans belum diatur. Isi MIDTRANS_SERVER_KEY pada file .env.')
    if not site_base_url.startswith('https://'):
        raise MidtransError('SITE_BASE_URL harus memakai domain HTTPS publik agar notifikasi Midtrans dapat mencapai website.')

    profile = getattr(payment_order.user, 'profile', None)
    customer_details = {
        'first_name': (payment_order.user.first_name or payment_order.user.username)[:50],
    }
    email = (payment_order.user.email or '').strip()
    phone = _international_phone(getattr(profile, 'no_telepon', ''))
    if email:
        customer_details['email'] = email
    if phone:
        customer_details['phone'] = phone

    payload = {
        'transaction_details': {
            'order_id': payment_order.invoice_number,
            'gross_amount': int(payment_order.jumlah_dp),
        },
        'item_details': [{
            'id': (payment_order.properti.kode_properti or str(payment_order.properti_id))[:50],
            'price': int(payment_order.jumlah_dp),
            'quantity': 1,
            'name': f'Down Payment - {payment_order.properti.nama_properti}'[:50],
        }],
        'customer_details': customer_details,
        'callbacks': {'finish': finish_url},
        'page_expiry': {'duration': 24, 'unit': 'hours'},
        'expiry': {
            'start_time': datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%Y-%m-%d %H:%M:%S %z'),
            'duration': 24,
            'unit': 'hours',
        },
    }
    body = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    authorization = base64.b64encode(f'{server_key}:'.encode('utf-8')).decode('ascii')
    endpoint = 'https://app.sandbox.midtrans.com/snap/v1/transactions'
    req = Request(
        endpoint,
        data=body,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {authorization}',
        },
        method='POST',
    )
    try:
        with urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        try:
            response_text = exc.read().decode('utf-8', errors='replace')
            error_data = json.loads(response_text)
        except (UnicodeDecodeError, json.JSONDecodeError):
            response_text = ''
            error_data = {}
        detail = ''
        if isinstance(error_data, dict):
            error_messages = error_data.get('error_messages')
            if isinstance(error_messages, list):
                detail = '; '.join(str(message) for message in error_messages)
            elif error_messages:
                detail = str(error_messages)
            else:
                detail = str(error_data.get('message') or error_data.get('status_message') or '')
        if not detail and response_text:
            detail = ' '.join(response_text.split())[:300]
        if not detail and exc.code in (401, 403):
            detail = 'Autentikasi ditolak. Pastikan yang dipakai adalah Server Key dari akun Sandbox Midtrans yang sama.'
        if not detail:
            detail = f'HTTP {exc.code}; periksa Server Key Sandbox, nominal, dan kanal pembayaran yang aktif.'
        raise MidtransError(f'Midtrans menolak transaksi: {detail}') from exc
    except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MidtransError('Tidak dapat menghubungi Midtrans Sandbox. Coba lagi beberapa saat atau periksa koneksi server.') from exc

    if not isinstance(data, dict):
        raise MidtransError('Respons Midtrans tidak valid.')
    redirect_url = data.get('redirect_url', '')
    token = data.get('token', '')
    if not token or not redirect_url.startswith('https://'):
        raise MidtransError('Midtrans tidak mengembalikan token atau tautan pembayaran yang valid.')
    return token, redirect_url


def verify_notification(payload):
    server_key = getattr(settings, 'MIDTRANS_SERVER_KEY', '')
    if not server_key or not isinstance(payload, dict):
        return False
    order_id = str(payload.get('order_id', ''))
    status_code = str(payload.get('status_code', ''))
    gross_amount = str(payload.get('gross_amount', ''))
    signature = str(payload.get('signature_key', ''))
    if not order_id or not status_code or not gross_amount or not signature:
        return False
    expected = hashlib.sha512(f'{order_id}{status_code}{gross_amount}{server_key}'.encode('utf-8')).hexdigest()
    return hmac.compare_digest(expected.lower(), signature.lower())


def fetch_snap_transaction_status(identifier):
    """Fetch an authoritative transaction status from the Midtrans Sandbox API."""
    server_key = getattr(settings, 'MIDTRANS_SERVER_KEY', '')
    if not server_key:
        raise MidtransError('Server Key Midtrans belum diatur.')

    authorization = base64.b64encode(f'{server_key}:'.encode('utf-8')).decode('ascii')
    endpoint = f'https://api.sandbox.midtrans.com/v2/{quote(str(identifier), safe="")}/status'
    req = Request(
        endpoint,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Basic {authorization}',
            'transaction-source': 'SNAP_API',
        },
        method='GET',
    )
    try:
        with urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        raise MidtransError(f'Midtrans Status API mengembalikan HTTP {exc.code}.') from exc
    except (URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MidtransError('Tidak dapat memverifikasi status transaksi melalui Midtrans Sandbox.') from exc

    if not isinstance(data, dict):
        raise MidtransError('Midtrans Status API tidak mengembalikan objek JSON transaksi.')
    response_order_id = str(data.get('order_id', ''))
    response_transaction_id = str(data.get('transaction_id', ''))
    if str(identifier) not in {response_order_id, response_transaction_id}:
        response_code = str(data.get('status_code', ''))
        response_message = str(data.get('status_message') or data.get('error') or '')[:160]
        raise MidtransError(
            'Respons Status API tidak cocok dengan invoice '
            f'(code={response_code or "-"}, order_id={response_order_id or "-"}, '
            f'transaction_id={response_transaction_id or "-"}, '
            f'message={response_message or "-"}).'
        )
    return data

import json
import uuid
import hashlib
import logging
import xml.etree.ElementTree as ElementTree
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.forms import inlineformset_factory
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import (
    AdminUserForm,
    ArticleCategoryForm,
    ArticleForm,
    HeroSlideForm,
    PropertyCategoryForm,
    PropertyForm,
    SurveyBookingForm,
    WebSettingForm,
    WebsitePageForm,
)
from .models import (
    Article,
    ArticleCategory,
    CustomerProfile,
    Category,
    HeroSlide,
    PaymentOrder,
    Property,
    PropertyGalleryImage,
    PaymentNotificationEvent,
    Testimonial,
    UpcomingProject,
    SurveyBooking,
    WebSetting,
    WebsitePage,
)
from django.core.paginator import Paginator
from .doku import (
    verify_notification as verify_doku_notification,
)
from .midtrans import (
    MidtransError,
    create_snap_transaction,
    fetch_snap_transaction_status,
    midtrans_is_configured,
    verify_notification as verify_midtrans_notification,
)

logger = logging.getLogger(__name__)


def _fetch_midtrans_status_for_order(payment_order, identifiers):
    """Try known Midtrans identifiers and accept only a response for this invoice."""
    tried = set()
    last_error = None
    for identifier in identifiers:
        identifier = str(identifier or '').strip()
        if not identifier or identifier in tried:
            continue
        tried.add(identifier)
        try:
            payload = fetch_snap_transaction_status(identifier)
        except MidtransError as exc:
            last_error = exc
            continue
        if str(payload.get('order_id', '')) == payment_order.invoice_number:
            return payload
        last_error = MidtransError(
            'Respons Status API Midtrans tidak cocok dengan invoice '
            f'{payment_order.invoice_number} (order_id={payload.get("order_id", "-")}).'
        )
    if last_error:
        raise last_error
    raise MidtransError('Tidak ada ID transaksi Midtrans yang dapat diverifikasi.')

# Fungsi pengecekan apakah user adalah Admin (Superuser)
def is_admin(user):
    return user.is_authenticated and user.is_superuser


# ==========================================
# 1. HALAMAN PUBLIK (HOME)
# ==========================================
def home_view(request):
    categories = Category.objects.all()
    properties = Property.objects.filter(tampil_di_home=True)
    testimonials = Testimonial.objects.filter(tampil_di_home=True)
    upcoming_projects = UpcomingProject.objects.all()
    hero_slides = list(HeroSlide.objects.filter(aktif=True))

    kota_query = request.GET.get('kota')
    kategori_slug = request.GET.get('kategori')
    harga_max = request.GET.get('harga_max')

    if kota_query:
        properties = properties.filter(kota__icontains=kota_query)
    if kategori_slug:
        properties = properties.filter(kategori__slug=kategori_slug)
    if harga_max:
        properties = properties.filter(harga__lte=harga_max)

    context = {
        'categories': categories,
        'properties': properties,
        'testimonials': testimonials,
        'upcoming_projects': upcoming_projects,
        'hero_slides': hero_slides,
    }
    return render(request, 'home.html', context)


def gallery_view(request):
    """Public editorial gallery. Captions let admins classify additional photos."""
    properties = Property.objects.prefetch_related('foto_galeri').order_by('-tanggal_dibuat')
    category_labels = {
        'exterior': 'Exterior Views',
        'interior': 'Interior Spaces',
        'neighborhood': 'The Neighborhood',
        'architecture': 'Architectural Details',
    }
    entries_by_category = {key: [] for key in category_labels}
    unclassified_entries = []
    total_photos = 0

    def classify_gallery_photo(caption, is_cover=False):
        if is_cover:
            return 'exterior'
        text = (caption or '').casefold()
        if any(word in text for word in ('interior', 'ruang', 'kamar', 'dapur', 'kitchen', 'living')):
            return 'interior'
        if any(word in text for word in ('kawasan', 'lingkungan', 'neighbourhood', 'neighborhood', 'taman', 'cluster')):
            return 'neighborhood'
        if any(word in text for word in ('arsitektur', 'material', 'detail', 'architecture', 'texture', 'fasad', 'exterior', 'eksterior')):
            return 'architecture' if any(word in text for word in ('arsitektur', 'material', 'detail', 'architecture', 'texture')) else 'exterior'
        # Keep photos without a descriptive caption in the general collection.
        return ''

    for properti in properties:
        if properti.gambar_utama:
            category = classify_gallery_photo(properti.nama_properti, is_cover=True)
            entry = {
                'property': properti,
                'image_url': properti.gambar_utama.url,
                'caption': properti.nama_properti,
                'alt': f'Foto utama {properti.nama_properti}',
                'category': category,
                'is_cover': True,
            }
            entries_by_category[category].append(entry)
            total_photos += 1
        for photo in properti.foto_galeri.all():
            category = classify_gallery_photo(photo.keterangan)
            entry = {
                'property': properti,
                'image_url': photo.gambar.url,
                'caption': photo.keterangan or properti.nama_properti,
                'alt': photo.keterangan or f'Galeri {properti.nama_properti}',
                'category': category,
                'is_cover': False,
            }
            if category:
                entries_by_category[category].append(entry)
            else:
                unclassified_entries.append(entry)
            total_photos += 1

    property_list = list(properties)
    if not entries_by_category['neighborhood']:
        for properti in property_list[:4]:
            if not properti.gambar_utama:
                continue
            entries_by_category['neighborhood'].append({
                'property': properti,
                'image_url': properti.gambar_utama.url,
                'caption': properti.fasilitas_lingkungan,
                'alt': f'Properti dan fasilitas kawasan {properti.nama_properti}',
                'category': 'neighborhood',
                'is_cover': True,
                'property_summary': True,
            })

    gallery_groups = [
        {
            'key': key,
            'label': category_labels[key],
            'entries': entries,
            'count': len(entries),
        }
        for key, entries in entries_by_category.items() if entries or key == 'interior'
    ]
    if unclassified_entries:
        gallery_groups.append({
            'key': 'collection',
            'label': 'Property Albums',
            'entries': unclassified_entries,
            'count': len(unclassified_entries),
        })
    featured_property = property_list[0] if property_list else None
    return render(request, 'gallery.html', {
        'gallery_groups': gallery_groups,
        'gallery_categories': [
            {'key': key, 'label': label, 'count': len(entries_by_category[key])}
            for key, label in category_labels.items()
        ],
        'total_photos': total_photos,
        'property_count': len(property_list),
        'available_property_count': sum(
            property.status_penjualan == Property.StatusPenjualan.AVAILABLE
            for property in property_list
        ),
        'properties': property_list,
        'featured_property': featured_property,
        'canonical_url': request.build_absolute_uri(reverse('gallery')),
    })


def about_us_view(request):
    """Brand story and service principles for Agang Property."""
    featured_property = Property.objects.order_by('-tanggal_dibuat').first()
    return render(request, 'about_us.html', {
        'featured_property': featured_property,
        'leadership_team': [
            {
                'name': 'Ahmad Fadzel Idrus',
                'role': 'CEO',
                'photo': 'e_commerce/images/team/ahmad-fadzel-idrus.jpg',
            },
            {
                'name': 'Kholid Firdaus',
                'role': 'Operation',
                'photo': 'e_commerce/images/team/kholid-firdaus.jpg',
            },
            {
                'name': 'Muh. Rifky Putra Handoko',
                'role': 'Marketing',
                'photo': 'e_commerce/images/team/muh-rifky-putra-handoko.jpg',
            },
            {
                'name': 'Nur Alim',
                'role': 'Product / Platform',
                'photo': 'e_commerce/images/team/nur-alim.jpg',
            },
        ],
        'canonical_url': request.build_absolute_uri(reverse('about_us')),
    })


# ==========================================
# 2. AUTENTIKASI (LOGIN SATU PINTU & REGISTRASI PENGGUNA)
# ==========================================
def login_view(request):
    # Jika sudah login, langsung arahkan sesuai role
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        return redirect('user_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            # Cek apakah yang login adalah Admin (Superuser) atau Pengguna biasa
            if user.is_superuser:
                messages.success(request, f'Selamat datang kembali, Admin {user.username}!')
                return redirect('admin_dashboard')
            else:
                messages.success(request, f'Selamat datang, {user.first_name or user.username}!')
                return redirect('user_dashboard')
        else:
            messages.error(request, 'Username atau password salah!')

    return render(request, 'login.html', {'next': request.GET.get('next', '')})


def register_view(request):
    # Registrasi khusus untuk pengguna (Customer), bukan Admin
    if request.user.is_authenticated:
        return redirect('user_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        nama_lengkap = request.POST.get('nama_lengkap')
        no_telepon = request.POST.get('no_telepon')
        alamat = request.POST.get('alamat')
        password = request.POST.get('password')
        konfirmasi_password = request.POST.get('konfirmasi_password')

        if password != konfirmasi_password:
            messages.error(request, 'Password dan konfirmasi password tidak cocok!')
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username sudah terdaftar, silakan gunakan yang lain!')
            return redirect('register')

        # Membuat akun customer biasa (is_superuser=False)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=nama_lengkap
        )
        CustomerProfile.objects.create(
            user=user,
            no_telepon=no_telepon,
            alamat=alamat
        )

        messages.success(request, 'Registrasi berhasil! Silakan login menggunakan akun Anda.')
        return redirect('login')

    return render(request, 'register.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'Anda telah keluar dari sistem.')
    return redirect('login')


# ==========================================
# 3. AREA KHUSUS ADMIN (SUPERUSER)
# ==========================================
@user_passes_test(is_admin, login_url='login')
def admin_dashboard_view(request):
    context = {
        'total_properti': Property.objects.count(),
        'total_customer': User.objects.filter(is_superuser=False).count(),
        'total_testimoni': Testimonial.objects.count(),
        'total_upcoming': UpcomingProject.objects.count(),
        'total_artikel': Article.objects.count(),
        'total_artikel_terbit': Article.objects.filter(status=Article.Status.PUBLISHED).count(),
        'properties': Property.objects.all().order_by('-tanggal_dibuat')[:5],
        'articles': Article.objects.select_related('kategori').order_by('-diperbarui')[:5],
        'customers': CustomerProfile.objects.select_related('user').filter(user__is_superuser=False)[:8],
        'admin_profile': CustomerProfile.objects.filter(user=request.user).first(),
        'page_title': 'Dashboard Administrator',
        'active_nav': 'dashboard',
    }
    return render(request, 'admin_dashboard.html', context)


@user_passes_test(is_admin, login_url='login')
def admin_users_view(request):
    users = User.objects.filter(is_superuser=False).select_related('profile').order_by('-date_joined')
    query = request.GET.get('q', '').strip()
    account_status = request.GET.get('status', 'all')
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(profile__no_telepon__icontains=query)
            | Q(profile__alamat__icontains=query)
        )
    if account_status == 'active':
        users = users.filter(is_active=True)
    elif account_status == 'inactive':
        users = users.filter(is_active=False)
    else:
        account_status = 'all'

    page_obj = Paginator(users, 20).get_page(request.GET.get('page'))
    all_customers = User.objects.filter(is_superuser=False)
    return render(request, 'admin_users.html', {
        'page_title': 'Kelola User',
        'active_nav': 'users',
        'page_obj': page_obj,
        'query': query,
        'account_status': account_status,
        'total_users': all_customers.count(),
        'active_users': all_customers.filter(is_active=True).count(),
        'inactive_users': all_customers.filter(is_active=False).count(),
    })


@user_passes_test(is_admin, login_url='login')
def admin_user_create_view(request):
    form = AdminUserForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        account = form.save()
        messages.success(request, f'Akun @{account.username} berhasil dibuat.')
        return redirect('admin_users')
    return render(request, 'admin_user_form.html', {
        'page_title': 'Tambah User',
        'active_nav': 'users',
        'form': form,
        'is_create': True,
    })


@user_passes_test(is_admin, login_url='login')
def admin_user_edit_view(request, pk):
    account = get_object_or_404(User, pk=pk, is_superuser=False)
    form = AdminUserForm(request.POST or None, request.FILES or None, instance=account)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Akun @{account.username} berhasil diperbarui.')
        return redirect('admin_users')
    return render(request, 'admin_user_form.html', {
        'page_title': f'Edit User · {account.username}',
        'active_nav': 'users',
        'form': form,
        'account': account,
        'is_create': False,
    })


@user_passes_test(is_admin, login_url='login')
@require_POST
def admin_user_delete_view(request, pk):
    account = get_object_or_404(User, pk=pk, is_superuser=False)
    username = account.username
    try:
        account.delete()
    except ProtectedError:
        messages.error(request, f'Akun @{username} memiliki riwayat transaksi. Nonaktifkan akun agar riwayat tetap tersimpan.')
    else:
        messages.success(request, f'Akun @{username} berhasil dihapus.')
    return redirect('admin_users')


@user_passes_test(is_admin, login_url='login')
def admin_orders_view(request):
    PaymentOrder.objects.filter(
        status=PaymentOrder.Status.PENDING,
        jatuh_tempo__lte=timezone.now(),
    ).update(status=PaymentOrder.Status.EXPIRED, diperbarui=timezone.now())

    orders = PaymentOrder.objects.select_related('user', 'properti').order_by('-dibuat')
    query = request.GET.get('q', '').strip()
    order_status = request.GET.get('status', 'all')
    if query:
        orders = orders.filter(
            Q(invoice_number__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__email__icontains=query)
            | Q(properti__nama_properti__icontains=query)
            | Q(properti__kode_properti__icontains=query)
        )
    if order_status in {PaymentOrder.Status.PENDING, PaymentOrder.Status.PAID, PaymentOrder.Status.EXPIRED, PaymentOrder.Status.FAILED}:
        orders = orders.filter(status=order_status)
    else:
        order_status = 'all'

    all_orders = PaymentOrder.objects.all()
    page_obj = Paginator(orders, 20).get_page(request.GET.get('page'))
    return render(request, 'admin_orders.html', {
        'page_title': 'Kelola Pesanan',
        'active_nav': 'orders',
        'page_obj': page_obj,
        'query': query,
        'order_status': order_status,
        'total_orders': all_orders.count(),
        'pending_orders': all_orders.filter(status=PaymentOrder.Status.PENDING).count(),
        'paid_orders': all_orders.filter(status=PaymentOrder.Status.PAID).count(),
    })


@user_passes_test(is_admin, login_url='login')
def admin_order_detail_view(request, pk):
    order = get_object_or_404(
        PaymentOrder.objects.select_related('user', 'properti').prefetch_related('notifications'),
        pk=pk,
    )
    if order.status == PaymentOrder.Status.PENDING and order.jatuh_tempo <= timezone.now():
        order.status = PaymentOrder.Status.EXPIRED
        order.save(update_fields=['status', 'diperbarui'])
    return render(request, 'admin_order_detail.html', {
        'page_title': f'Detail Pesanan · {order.invoice_number}',
        'active_nav': 'orders',
        'order': order,
        'notification_events': order.notifications.all(),
        'payment_payload_json': json.dumps(order.payment_payload or {}, indent=2, ensure_ascii=False),
    })


@user_passes_test(is_admin, login_url='login')
def admin_properties_view(request):
    if request.method == 'POST' and 'update_listing' in request.POST:
        properti = get_object_or_404(Property, pk=request.POST.get('property_id'))
        status = request.POST.get('status_penjualan', '')
        badge = request.POST.get('badge_status', '').strip()
        badge_kedua = request.POST.get('badge_kedua', '').strip()
        badge_ketiga = request.POST.get('badge_ketiga', '').strip()
        tampil_di_home = bool(request.POST.get('tampil_di_home'))
        valid_statuses = {value for value, _label in Property.StatusPenjualan.choices}
        if status not in valid_statuses or not badge or any(len(value) > 50 for value in (badge, badge_kedua, badge_ketiga)):
            messages.error(request, 'Status penjualan atau badge tidak valid. Badge utama wajib diisi dan setiap badge maksimal 50 karakter.')
        else:
            properti.status_penjualan = status
            properti.badge_status = badge
            properti.badge_kedua = badge_kedua or None
            properti.badge_ketiga = badge_ketiga or None
            properti.tampil_di_home = tampil_di_home
            properti.save(update_fields=['status_penjualan', 'badge_status', 'badge_kedua', 'badge_ketiga', 'tampil_di_home'])
            messages.success(request, f'Status, badge, dan tampilan beranda {properti.nama_properti} berhasil diperbarui.')
        return redirect('admin_properties')

    properties = Property.objects.select_related('kategori').order_by('-tanggal_dibuat')
    query = request.GET.get('q', '').strip()
    property_status = request.GET.get('status', 'all')
    category_id = request.GET.get('category', 'all')
    city = request.GET.get('city', 'all')
    home_visibility = request.GET.get('home', 'all')
    if query:
        properties = properties.filter(
            Q(nama_properti__icontains=query)
            | Q(kode_properti__icontains=query)
            | Q(nama_cluster__icontains=query)
            | Q(kota__icontains=query)
            | Q(lokasi_detail__icontains=query)
        )
    if property_status in {Property.StatusPenjualan.AVAILABLE, Property.StatusPenjualan.SOLD}:
        properties = properties.filter(status_penjualan=property_status)
    else:
        property_status = 'all'
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        category_id = 'all'
    if category_id != 'all' and Category.objects.filter(pk=category_id).exists():
        properties = properties.filter(kategori_id=category_id)
    else:
        category_id = 'all'
    valid_cities = set(Property.objects.order_by().values_list('kota', flat=True).distinct())
    if city in valid_cities:
        properties = properties.filter(kota=city)
    else:
        city = 'all'
    if home_visibility == 'yes':
        properties = properties.filter(tampil_di_home=True)
    elif home_visibility == 'no':
        properties = properties.filter(tampil_di_home=False)
    else:
        home_visibility = 'all'
    page_obj = Paginator(properties, 20).get_page(request.GET.get('page'))
    all_properties = Property.objects.all()
    context = {
        'page_title': 'Kelola Properti',
        'active_nav': 'properties',
        'page_obj': page_obj,
        'query': query,
        'property_status': property_status,
        'category_id': category_id,
        'city': city,
        'home_visibility': home_visibility,
        'property_categories': Category.objects.order_by('nama_kategori'),
        'property_cities': sorted(valid_cities),
        'total_properti': all_properties.count(),
        'available_properties': all_properties.filter(status_penjualan=Property.StatusPenjualan.AVAILABLE).count(),
        'sold_properties': all_properties.filter(status_penjualan=Property.StatusPenjualan.SOLD).count(),
    }
    return render(request, 'admin_properties.html', context)


PROPERTY_FIELDSETS = (
    ('Identitas dan lokasi', ('kategori', 'nama_cluster', 'nama_properti', 'kode_properti', 'kota', 'lokasi_detail')),
    ('Harga, badge, dan status', ('harga', 'harga_coret', 'estimasi_cicilan', 'badge_status', 'badge_kedua', 'badge_ketiga', 'status_legalitas', 'status_penjualan', 'tampil_di_home')),
    ('Foto dan deskripsi', ('gambar_utama', 'deskripsi_singkat', 'deskripsi_panjang', 'youtube_video_url')),
    ('Spesifikasi unit', ('jumlah_lantai', 'kamar_tidur', 'kamar_mandi', 'luas_bangunan', 'luas_tanah', 'arah_hadap', 'daftar_furnitur', 'fasilitas_lingkungan')),
    ('Legalitas dan konstruksi', ('status_kepemilikan', 'daya_listrik', 'sumber_air', 'pondasi', 'struktur_dinding', 'kusen_jendela', 'lantai_utama', 'sanitari_km', 'rangka_atap', 'lebar_jalan_row')),
    ('Informasi investasi', ('ulasan_investasi',)),
)


def _property_form_sections(form):
    return [(title, [form[name] for name in field_names]) for title, field_names in PROPERTY_FIELDSETS]


def _property_gallery_formset():
    return inlineformset_factory(
        Property,
        PropertyGalleryImage,
        fields=('gambar', 'keterangan', 'urutan'),
        extra=2,
        can_delete=True,
    )


@user_passes_test(is_admin, login_url='login')
def admin_property_create_view(request):
    form = PropertyForm(request.POST or None, request.FILES or None)
    gallery_formset_class = _property_gallery_formset()
    formset = gallery_formset_class(
        request.POST or None,
        request.FILES or None,
        instance=form.instance,
        prefix='foto_galeri',
    )
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            properti = form.save()
            formset.instance = properti
            formset.save()
        messages.success(request, 'Properti baru berhasil ditambahkan.')
        return redirect('admin_properties')
    return render(request, 'admin_property_form.html', {
        'page_title': 'Tambah Properti',
        'active_nav': 'properties',
        'form': form,
        'formset': formset,
        'fieldsets': _property_form_sections(form),
        'is_create': True,
    })


@user_passes_test(is_admin, login_url='login')
def admin_property_edit_view(request, pk):
    properti = get_object_or_404(Property, pk=pk)
    form = PropertyForm(request.POST or None, request.FILES or None, instance=properti)
    gallery_formset_class = _property_gallery_formset()
    formset = gallery_formset_class(
        request.POST or None,
        request.FILES or None,
        instance=properti,
        prefix='foto_galeri',
    )
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            form.save()
            formset.save()
        messages.success(request, f'Data {properti.nama_properti} berhasil diperbarui.')
        return redirect('admin_properties')
    return render(request, 'admin_property_form.html', {
        'page_title': f'Edit Properti · {properti.nama_properti}',
        'active_nav': 'properties',
        'form': form,
        'formset': formset,
        'fieldsets': _property_form_sections(form),
        'properti': properti,
        'is_create': False,
    })


@user_passes_test(is_admin, login_url='login')
@require_POST
def admin_property_delete_view(request, pk):
    properti = get_object_or_404(Property, pk=pk)
    nama_properti = properti.nama_properti
    try:
        properti.delete()
    except ProtectedError:
        messages.error(request, f'{nama_properti} memiliki riwayat pesanan dan tidak dapat dihapus. Ubah statusnya menjadi SOLD bila sudah terjual.')
    else:
        messages.success(request, f'{nama_properti} berhasil dihapus.')
    return redirect('admin_properties')


@user_passes_test(is_admin, login_url='login')
def admin_property_categories_view(request):
    form = PropertyCategoryForm()
    if request.method == 'POST' and 'save_category' in request.POST:
        category = get_object_or_404(Category, pk=request.POST.get('category_id'))
        form = PropertyCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kategori properti berhasil diperbarui.')
            return redirect('admin_property_categories')
    elif request.method == 'POST' and 'add_category' in request.POST:
        form = PropertyCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kategori properti berhasil ditambahkan.')
            return redirect('admin_property_categories')
    elif request.method == 'POST' and 'delete_category' in request.POST:
        category = get_object_or_404(Category, pk=request.POST.get('category_id'))
        if category.properties.exists():
            messages.error(request, 'Kategori ini masih digunakan properti. Pindahkan propertinya sebelum menghapus kategori.')
        else:
            category.delete()
            messages.success(request, 'Kategori properti berhasil dihapus.')
        return redirect('admin_property_categories')
    return render(request, 'admin_property_categories.html', {
        'page_title': 'Kategori Properti',
        'active_nav': 'property_categories',
        'form': form,
        'categories': Category.objects.all().order_by('nama_kategori'),
    })


@user_passes_test(is_admin, login_url='login')
def admin_surveys_view(request):
    if request.method == 'POST' and 'update_survey_status' in request.POST:
        survey = get_object_or_404(SurveyBooking, pk=request.POST.get('survey_id'))
        status = request.POST.get('status', '')
        valid_statuses = {value for value, _label in SurveyBooking.STATUS_SURVEI}
        if status in valid_statuses:
            survey.status = status
            survey.save(update_fields=['status'])
            messages.success(request, 'Status jadwal survei berhasil diperbarui.')
        else:
            messages.error(request, 'Status jadwal survei tidak valid.')
        return redirect('admin_surveys')

    surveys = SurveyBooking.objects.select_related('properti', 'user').order_by('-tanggal_survei', '-tanggal_dibuat')
    query = request.GET.get('q', '').strip()
    survey_status = request.GET.get('status', 'all')
    if query:
        surveys = surveys.filter(
            Q(nama_pemohon__icontains=query)
            | Q(no_whatsapp__icontains=query)
            | Q(properti__nama_properti__icontains=query)
            | Q(properti__kode_properti__icontains=query)
            | Q(user__username__icontains=query)
        )
    valid_statuses = {value for value, _label in SurveyBooking.STATUS_SURVEI}
    if survey_status in valid_statuses:
        surveys = surveys.filter(status=survey_status)
    else:
        survey_status = 'all'
    page_obj = Paginator(surveys, 20).get_page(request.GET.get('page'))
    all_surveys = SurveyBooking.objects.all()
    return render(request, 'admin_surveys.html', {
        'page_title': 'Jadwal Survei',
        'active_nav': 'surveys',
        'page_obj': page_obj,
        'query': query,
        'survey_status': survey_status,
        'survey_statuses': SurveyBooking.STATUS_SURVEI,
        'total_surveys': all_surveys.count(),
        'waiting_surveys': all_surveys.filter(status='Menunggu Konfirmasi').count(),
        'scheduled_surveys': all_surveys.filter(status='Terjadwal').count(),
        'completed_surveys': all_surveys.filter(status='Selesai').count(),
    })


@user_passes_test(is_admin, login_url='login')
def admin_survey_create_view(request):
    form = SurveyBookingForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Jadwal survei berhasil ditambahkan.')
        return redirect('admin_surveys')
    return render(request, 'admin_survey_form.html', {
        'page_title': 'Tambah Jadwal Survei',
        'active_nav': 'surveys',
        'form': form,
        'is_create': True,
    })


@user_passes_test(is_admin, login_url='login')
def admin_survey_edit_view(request, pk):
    survey = get_object_or_404(SurveyBooking, pk=pk)
    form = SurveyBookingForm(request.POST or None, instance=survey)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Jadwal survei berhasil diperbarui.')
        return redirect('admin_surveys')
    return render(request, 'admin_survey_form.html', {
        'page_title': 'Edit Jadwal Survei',
        'active_nav': 'surveys',
        'form': form,
        'survey': survey,
        'is_create': False,
    })


@user_passes_test(is_admin, login_url='login')
@require_POST
def admin_survey_delete_view(request, pk):
    survey = get_object_or_404(SurveyBooking, pk=pk)
    survey.delete()
    messages.success(request, 'Jadwal survei berhasil dihapus.')
    return redirect('admin_surveys')


@user_passes_test(is_admin, login_url='login')
def admin_articles_view(request):
    article_form = ArticleForm()
    article_category_form = ArticleCategoryForm()

    if request.method == 'POST' and 'tambah_artikel' in request.POST:
        article_form = ArticleForm(request.POST, request.FILES)
        if article_form.is_valid():
            article = article_form.save(commit=False)
            article.penulis = request.user
            article.save()
            messages.success(request, 'Artikel berhasil disimpan.')
            return redirect('admin_articles')

    if request.method == 'POST' and 'tambah_kategori_artikel' in request.POST:
        article_category_form = ArticleCategoryForm(request.POST)
        if article_category_form.is_valid():
            article_category_form.save()
            messages.success(request, 'Kategori artikel berhasil ditambahkan.')
            return redirect('/dashboard/admin/articles/?section=categories#article-categories')

    section = request.GET.get('section') or (
        'categories' if request.method == 'POST' and 'tambah_kategori_artikel' in request.POST else 'articles'
    )
    context = {
        'page_title': 'Kelola Artikel',
        'active_nav': 'article_categories' if section == 'categories' else 'articles',
        'articles': Article.objects.select_related('kategori', 'penulis').order_by('-diperbarui'),
        'article_categories': ArticleCategory.objects.all(),
        'article_form': article_form,
        'article_category_form': article_category_form,
        'total_artikel': Article.objects.count(),
        'total_artikel_terbit': Article.objects.filter(status=Article.Status.PUBLISHED).count(),
    }
    return render(request, 'admin_articles.html', context)


@user_passes_test(is_admin, login_url='login')
def admin_article_category_edit_view(request, pk):
    category = get_object_or_404(ArticleCategory, pk=pk)
    form = ArticleCategoryForm(request.POST or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Kategori artikel berhasil diperbarui.')
        return redirect('/dashboard/admin/articles/?section=categories#article-categories')
    return render(request, 'admin_article_category_form.html', {
        'page_title': 'Edit Kategori Artikel',
        'active_nav': 'article_categories',
        'form': form,
        'category': category,
    })


@user_passes_test(is_admin, login_url='login')
@require_POST
def admin_article_category_delete_view(request, pk):
    category = get_object_or_404(ArticleCategory, pk=pk)
    category.delete()
    messages.success(request, 'Kategori artikel berhasil dihapus. Artikel terkait tetap tersimpan tanpa kategori.')
    return redirect('/dashboard/admin/articles/?section=categories#article-categories')


@user_passes_test(is_admin, login_url='login')
def admin_hero_slides_view(request):
    form = HeroSlideForm()
    if request.method == 'POST' and 'tambah_hero_slide' in request.POST:
        form = HeroSlideForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hero slide berhasil ditambahkan.')
            return redirect('admin_hero_slides')

    context = {
        'page_title': 'Hero Slide Beranda',
        'active_nav': 'hero_slides',
        'form': form,
        'slides': HeroSlide.objects.all(),
        'slide_count': HeroSlide.objects.count(),
        'active_slide_count': HeroSlide.objects.filter(aktif=True).count(),
    }
    return render(request, 'admin_hero_slides.html', context)


@user_passes_test(is_admin, login_url='login')
def admin_hero_slide_edit_view(request, pk):
    slide = get_object_or_404(HeroSlide, pk=pk)
    form = HeroSlideForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None,
        instance=slide,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Hero slide berhasil diperbarui.')
        return redirect('admin_hero_slides')
    return render(request, 'admin_hero_slide_form.html', {
        'page_title': 'Edit Hero Slide',
        'active_nav': 'hero_slides',
        'slide': slide,
        'form': form,
    })


@user_passes_test(is_admin, login_url='login')
@require_POST
def admin_hero_slide_toggle_view(request, pk):
    slide = get_object_or_404(HeroSlide, pk=pk)
    slide.aktif = not slide.aktif
    slide.save(update_fields=['aktif', 'diperbarui'])
    messages.success(request, 'Status hero slide berhasil diperbarui.')
    return redirect('admin_hero_slides')


@user_passes_test(is_admin, login_url='login')
@require_POST
def admin_hero_slide_delete_view(request, pk):
    slide = get_object_or_404(HeroSlide, pk=pk)
    slide.delete()
    messages.success(request, 'Hero slide berhasil dihapus.')
    return redirect('admin_hero_slides')


@user_passes_test(is_admin, login_url='login')
def admin_web_settings_view(request):
    settings, _ = WebSetting.objects.get_or_create(pk=1)
    form = WebSettingForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None,
        instance=settings,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Pengaturan website berhasil diperbarui.')
        return redirect('admin_web_settings')

    return render(request, 'admin_web_settings.html', {
        'page_title': 'Pengaturan Website',
        'active_nav': 'web_settings',
        'form': form,
        'web_settings': settings,
    })


@user_passes_test(is_admin, login_url='login')
def admin_edit_profile_view(request):
    # Menggunakan CustomerProfile untuk menyimpan foto & no telepon admin juga
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        admin_user = request.user
        admin_user.username = request.POST.get('username', admin_user.username)
        admin_user.first_name = request.POST.get('nama_lengkap', admin_user.first_name)
        admin_user.email = request.POST.get('email', admin_user.email)

        password_baru = request.POST.get('password_baru')
        if password_baru:
            admin_user.set_password(password_baru)

        admin_user.save()

        profile.no_telepon = request.POST.get('no_telepon', profile.no_telepon)
        profile.alamat = request.POST.get('alamat', profile.alamat)
        if 'foto_profil' in request.FILES:
            profile.foto_profil = request.FILES['foto_profil']
        profile.save()

        messages.success(request, 'Profil Admin berhasil diperbarui! (Jika mengganti password, silakan login ulang).')
        return redirect('admin_dashboard')

    return render(request, 'admin_edit_profile.html', {
        'profile': profile,
        'admin_profile': profile,
        'page_title': 'Profil Admin',
        'active_nav': 'profile',
    })


# ==========================================
# 4. AREA KHUSUS PENGGUNA (CUSTOMER)
# ==========================================
@login_required(login_url='login')
def user_dashboard_view(request):
    # Jika admin tidak sengaja membuka URL user, arahkan ke dashboard admin
    if request.user.is_superuser:
        return redirect('admin_dashboard')

    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    PaymentOrder.objects.filter(
        user=request.user,
        status=PaymentOrder.Status.PENDING,
        jatuh_tempo__lte=timezone.now(),
    ).update(status=PaymentOrder.Status.EXPIRED, diperbarui=timezone.now())

    section = request.GET.get('section', 'overview')
    allowed_sections = {'overview', 'profile', 'password', 'privacy', 'dp', 'order_status', 'site_info'}
    if section not in allowed_sections:
        section = 'overview'

    password_form = PasswordChangeForm(user=request.user)
    if request.method == 'POST' and request.POST.get('action') == 'change_password':
        section = 'password'
        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password berhasil diubah.')
            return redirect(f'{reverse("user_dashboard")}?section=password')
    # Pengguna bisa mengirim review/testimoni dari dashboard mereka
    elif request.method == 'POST' and 'kirim_ulasan' in request.POST:
        Testimonial.objects.create(
            user=request.user,
            nama_pengulas=request.user.first_name or request.user.username,
            ulasan=request.POST.get('ulasan'),
            rating_bintang=request.POST.get('rating_bintang', 5)
        )
        messages.success(request, 'Terima kasih! Ulasan Anda berhasil dikirim.')
        return redirect('user_dashboard')

    orders = PaymentOrder.objects.filter(user=request.user).select_related('properti').order_by('-dibuat')
    status_filter = request.GET.get('status', 'all')
    if status_filter not in {'all', 'pending', 'paid', 'expired', 'failed'}:
        status_filter = 'all'
    visible_orders = orders if status_filter == 'all' else orders.filter(status=status_filter)
    order_counts = {
        'all': orders.count(),
        'pending': orders.filter(status=PaymentOrder.Status.PENDING).count(),
        'paid': orders.filter(status=PaymentOrder.Status.PAID).count(),
        'expired': orders.filter(status=PaymentOrder.Status.EXPIRED).count(),
        'failed': orders.filter(status=PaymentOrder.Status.FAILED).count(),
    }
    context = {
        'profile': profile,
        'section': section,
        'status_filter': status_filter,
        'password_form': password_form,
        'payment_orders': orders,
        'visible_orders': visible_orders,
        'order_counts': order_counts,
        'site_settings': WebSetting.objects.first(),
        'properties': Property.objects.filter(tampil_di_home=True)[:6],
        'ulasan_saya': Testimonial.objects.filter(user=request.user),
    }
    return render(request, 'user_dashboard.html', context)


@login_required(login_url='login')
def user_edit_profile_view(request):
    if request.user.is_superuser:
        return redirect('admin_edit_profile')

    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('nama_lengkap', user.first_name)
        user.email = request.POST.get('email', user.email)
        user.save()

        profile.no_telepon = request.POST.get('no_telepon', profile.no_telepon)
        profile.alamat = request.POST.get('alamat', profile.alamat)
        if 'foto_profil' in request.FILES:
            profile.foto_profil = request.FILES['foto_profil']
        profile.save()

        messages.success(request, 'Profil Anda berhasil diperbarui!')
        return redirect(f'{reverse("user_dashboard")}?section=profile')

    return redirect(f'{reverse("user_dashboard")}?section=profile')

# ==========================================
# 4. Katalog (Publik) 
# ==========================================

def catalog_view(request):
    categories = Category.objects.all()
    properties_list = Property.objects.all().order_by('-tanggal_dibuat')
    total_terdaftar = properties_list.count()

    # 1. Pencarian Kata Kunci (Nama properti, nama cluster, lokasi, atau kota)
    q = request.GET.get('q', '').strip()
    if q:
        properties_list = properties_list.filter(
            Q(nama_properti__icontains=q) |
            Q(nama_cluster__icontains=q) |
            Q(lokasi_detail__icontains=q) |
            Q(kota__icontains=q)
        )

    # 2. Filter 4 Dropdown & Tombol Pintas (Quick Pills)
    kategori_slug = request.GET.get('kategori', '').strip()
    wilayah = request.GET.get('wilayah', '').strip()
    anggaran = request.GET.get('anggaran', '').strip()
    legalitas = request.GET.get('legalitas', '').strip()
    urutkan = request.GET.get('urutkan', 'rekomendasi').strip()

    if kategori_slug:
        properties_list = properties_list.filter(kategori__slug=kategori_slug)
    if wilayah:
        properties_list = properties_list.filter(
            Q(kota__icontains=wilayah) | Q(lokasi_detail__icontains=wilayah)
        )
    if anggaran:
        if anggaran == 'under_600':
            properties_list = properties_list.filter(harga__lte=600000000)
        elif anggaran == '600_1000':
            properties_list = properties_list.filter(harga__gte=600000000, harga__lte=1000000000)
        elif anggaran == 'above_1000':
            properties_list = properties_list.filter(harga__gt=1000000000)
    if legalitas:
        properties_list = properties_list.filter(
            Q(status_legalitas__icontains=legalitas) |
            Q(badge_status__icontains=legalitas) |
            Q(badge_kedua__icontains=legalitas)
        )

    # 3. Pengurutan (Sorting)
    if urutkan == 'termurah':
        properties_list = properties_list.order_by('harga')
    elif urutkan == 'termahal':
        properties_list = properties_list.order_by('-harga')
    elif urutkan == 'terbaru':
        properties_list = properties_list.order_by('-tanggal_dibuat')

    # 4. Paginasi (Menampilkan 9 unit per halaman sesuai prototipe)
    paginator = Paginator(properties_list, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'categories': categories,
        'properties': page_obj,
        'total_terdaftar': total_terdaftar,
        'total_tampil': properties_list.count(),
    }
    return render(request, 'katalog.html', context)

# ==========================================
# 4. Detail Unit Properti (Publik) 
# ==========================================

def _property_is_sold(properti):
    return properti.status_penjualan == Property.StatusPenjualan.SOLD


def _mark_property_sold(properti_id):
    Property.objects.filter(pk=properti_id).update(
        status_penjualan=Property.StatusPenjualan.SOLD,
    )

def property_detail_view(request, pk):
    # Mengambil data properti berdasarkan pk
    properti = get_object_or_404(Property, pk=pk)

    list_furnitur = [item.strip() for item in properti.daftar_furnitur.split(',') if item.strip()]
    list_fasilitas = [item.strip() for item in properti.fasilitas_lingkungan.split(',') if item.strip()]

    if request.method == 'POST' and 'ajukan_survei' in request.POST:
        SurveyBooking.objects.create(
            properti=properti,
            user=request.user if request.user.is_authenticated else None,
            nama_pemohon=request.POST.get('nama_pemohon'),
            no_whatsapp=request.POST.get('no_whatsapp'),
            tanggal_survei=request.POST.get('tanggal_survei'),
            sesi_waktu=request.POST.get('sesi_waktu'),
            catatan=request.POST.get('catatan'),
        )
        messages.success(request, f'Jadwal survei untuk {properti.nama_properti} berhasil diajukan!')
        return redirect('property_detail', pk=properti.pk)

    properti_serupa = Property.objects.filter(kategori=properti.kategori).exclude(pk=properti.pk)[:3]
    if not properti_serupa:
        properti_serupa = Property.objects.exclude(pk=properti.pk)[:3]

    context = {
        'prop': properti,
        'is_sold': _property_is_sold(properti),
        'list_furnitur': list_furnitur,
        'list_fasilitas': list_fasilitas,
        'properti_serupa': properti_serupa,
        'gallery_images': properti.foto_galeri.all()[:4],
    }
    return render(request, 'detail_unit.html', context)


def property_gallery_view(request, pk):
    properti = get_object_or_404(Property.objects.prefetch_related('foto_galeri'), pk=pk)
    youtube_id = _youtube_video_id(properti.youtube_video_url)
    return render(request, 'property_gallery.html', {
        'prop': properti,
        'is_sold': _property_is_sold(properti),
        'gallery_images': properti.foto_galeri.all(),
        'youtube_embed_url': f'https://www.youtube-nocookie.com/embed/{youtube_id}' if youtube_id else '',
    })


def _youtube_video_id(url):
    if not url:
        return ''
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().split(':')[0]
    if host in {'youtu.be', 'www.youtu.be'}:
        video_id = parsed.path.strip('/').split('/')[0]
    elif host in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtube-nocookie.com', 'www.youtube-nocookie.com'}:
        if parsed.path == '/watch':
            video_id = parse_qs(parsed.query).get('v', [''])[0]
        elif parsed.path.startswith(('/embed/', '/shorts/')):
            video_id = parsed.path.split('/')[2] if len(parsed.path.split('/')) > 2 else ''
        else:
            video_id = ''
    else:
        return ''
    return video_id if video_id and all(ch.isalnum() or ch in '_-' for ch in video_id) else ''


@login_required(login_url='login')
def payment_create_view(request, pk):
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    properti = get_object_or_404(Property, pk=pk)
    if _property_is_sold(properti):
        messages.error(request, 'Unit ini sudah terjual dan tidak dapat menerima pembayaran DP baru.')
        return redirect('property_detail', pk=properti.pk)
    if request.method == 'POST':
        if not midtrans_is_configured():
            messages.error(
                request,
                'Midtrans Sandbox belum siap. Isi MIDTRANS_SERVER_KEY, SITE_BASE_URL HTTPS, '
                'dan MIDTRANS_NOTIFICATION_URL HTTPS pada .env.'
            )
            return redirect('payment_create', pk=properti.pk)
        try:
            dp_percent = Decimal(request.POST.get('dp_percent', '10'))
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, 'Nilai persentase DP tidak valid. Silakan periksa kembali.')
            return redirect('payment_create', pk=properti.pk)

        if not (Decimal('1') <= dp_percent <= Decimal('50')):
            messages.error(request, 'DP harus berada di antara 1% sampai 50%.')
            return redirect('payment_create', pk=properti.pk)
        now = timezone.now()
        invoice = f"AGDP{now:%y%m%d%H%M%S}{uuid.uuid4().hex[:6].upper()}"
        with transaction.atomic():
            properti = Property.objects.select_for_update().get(pk=properti.pk)
            if _property_is_sold(properti):
                messages.error(request, 'Unit ini baru saja terjual dan tidak dapat menerima pembayaran DP baru.')
                return redirect('property_detail', pk=properti.pk)
            amount = (properti.harga * dp_percent / Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            if amount < 1 or amount > Decimal('999999999999'):
                messages.error(request, 'Jumlah DP tidak dapat diproses Midtrans. Periksa harga properti dan persentase DP.')
                return redirect('payment_create', pk=properti.pk)
            payment_order = PaymentOrder.objects.create(
                invoice_number=invoice,
                user=request.user,
                properti=properti,
                jumlah_dp=amount,
                persentase_dp=dp_percent,
                bunga_tetap=Decimal('4.50'),
                masa_bunga_tetap=1,
                tenor_tahun=15,
                metode_pembayaran='Midtrans Snap',
                payment_gateway='midtrans',
                jatuh_tempo=now + timedelta(hours=24),
            )
        base_url = getattr(settings, 'SITE_BASE_URL', '').rstrip('/')
        callback_url = f'{base_url}{reverse("payment_status", kwargs={"reference": payment_order.reference})}'
        try:
            payment_order.payment_token, payment_order.payment_url = create_snap_transaction(
                payment_order,
                callback_url,
            )
            payment_order.save(update_fields=['payment_token', 'payment_url', 'diperbarui'])
        except MidtransError as exc:
            payment_order.status = PaymentOrder.Status.FAILED
            payment_order.save(update_fields=['status', 'diperbarui'])
            messages.error(request, str(exc))
            return redirect('payment_create', pk=properti.pk)
        return redirect(payment_order.payment_url)

    return render(request, 'payment_create.html', {
        'prop': properti,
        'payment_configured': midtrans_is_configured(),
        'midtrans_notification_url': settings.MIDTRANS_NOTIFICATION_URL,
    })


def payment_status_view(request, reference):
    order = get_object_or_404(PaymentOrder.objects.select_related('properti'), reference=reference)
    if order.status == PaymentOrder.Status.PENDING and order.payment_gateway == 'midtrans':
        # The return page is also a safe recovery path if Midtrans' webhook
        # could not be verified or delivered. Trust only the authenticated
        # Sandbox Status API response after matching invoice and amount.
        try:
            status_payload = _fetch_midtrans_status_for_order(order, (
                order.invoice_number,
                request.GET.get('transaction_id'),
                order.payment_transaction_id,
            ))
            status_amount = Decimal(str(status_payload.get('gross_amount', '')))
        except (MidtransError, InvalidOperation, TypeError, ValueError) as exc:
            logger.warning('Midtrans status check failed for invoice %s: %s', order.invoice_number, exc)
            status_payload = None
            status_amount = None
        if (
            status_payload
            and str(status_payload.get('order_id', '')) == order.invoice_number
            and status_amount == order.jumlah_dp
            and str(status_payload.get('status_code', '')) == '200'
        ):
            transaction_status = str(status_payload.get('transaction_status', '')).lower()
            fraud_status = str(status_payload.get('fraud_status', '')).lower()
            if (
                transaction_status in {'settlement', 'capture'}
                and (not fraud_status or fraud_status == 'accept')
            ):
                with transaction.atomic():
                    order = PaymentOrder.objects.select_for_update().select_related('properti').get(pk=order.pk)
                    if order.status == PaymentOrder.Status.PENDING:
                        order.status = PaymentOrder.Status.PAID
                        order.dibayar_pada = timezone.now()
                        order.payment_transaction_id = str(status_payload.get('transaction_id') or '')
                        order.payment_type = str(status_payload.get('payment_type') or '')
                        order.payment_channel = order.payment_type
                        order.payment_payload = status_payload
                        order.save(update_fields=(
                            'status', 'dibayar_pada', 'payment_transaction_id',
                            'payment_type', 'payment_channel', 'payment_payload', 'diperbarui',
                        ))
                        _mark_property_sold(order.properti_id)
    if order.status == PaymentOrder.Status.PENDING and order.jatuh_tempo <= timezone.now():
        order.status = PaymentOrder.Status.EXPIRED
        order.save(update_fields=['status', 'diperbarui'])
    return render(request, 'payment_status.html', {'order': order})


@csrf_exempt
@require_POST
def doku_notification_view(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HttpResponseBadRequest('Invalid JSON')

    if not isinstance(payload, dict) or not verify_doku_notification(
        request.body,
        request.headers,
        request.path,
    ):
        return HttpResponseForbidden('Signature not valid')

    order_data = payload.get('order') or {}
    transaction_data = payload.get('transaction') or {}
    channel_data = payload.get('channel') or {}
    acquirer_data = payload.get('acquirer') or {}
    invoice = order_data.get('invoice_number')
    if not invoice:
        return HttpResponseBadRequest('Missing order id')
    try:
        amount = Decimal(str(order_data.get('amount')))
    except (InvalidOperation, TypeError, ValueError):
        return HttpResponseBadRequest('Invalid amount')

    with transaction.atomic():
        payment_order = PaymentOrder.objects.select_for_update().filter(invoice_number=invoice).first()
        if payment_order is None:
            return HttpResponse('Unknown invoice', status=404)
        if amount != payment_order.jumlah_dp:
            return HttpResponseBadRequest('Amount mismatch')
        request_id = request.headers.get('Request-Id', '')
        event_key = hashlib.sha256(
            f'{request.headers.get("Client-Id", "")}:{request_id}'.encode('utf-8')
        ).hexdigest()
        _, created = PaymentNotificationEvent.objects.get_or_create(
            event_key=event_key,
            defaults={'payment': payment_order},
        )
        if not created:
            return HttpResponse('OK')

        transaction_status = str(transaction_data.get('status', '')).upper()
        if transaction_status == 'SUCCESS':
            payment_order.status = PaymentOrder.Status.PAID
            payment_order.dibayar_pada = timezone.now()
        elif transaction_status == 'FAILED' and payment_order.status != PaymentOrder.Status.PAID:
            payment_order.status = PaymentOrder.Status.FAILED
        elif transaction_status == 'EXPIRED' and payment_order.status != PaymentOrder.Status.PAID:
            payment_order.status = PaymentOrder.Status.EXPIRED
        elif transaction_status == 'PENDING' and payment_order.status not in (PaymentOrder.Status.PAID, PaymentOrder.Status.EXPIRED, PaymentOrder.Status.FAILED):
            payment_order.status = PaymentOrder.Status.PENDING

        va_data = payload.get('virtual_account_info') or {}
        payment_order.payment_transaction_id = str(
            transaction_data.get('original_request_id') or payment_order.payment_transaction_id
        )
        payment_order.payment_type = str(channel_data.get('id') or payment_order.payment_type)
        payment_order.nomor_virtual_account = str(
            va_data.get('virtual_account_number') or payment_order.nomor_virtual_account
        )
        payment_order.nama_bank = str(acquirer_data.get('id') or payment_order.nama_bank)
        payment_order.payment_channel = str(channel_data.get('id') or payment_order.payment_channel)
        payment_order.payment_payload = payload
        payment_order.save(update_fields=(
            'status', 'dibayar_pada', 'payment_transaction_id', 'payment_type',
            'nomor_virtual_account', 'nama_bank', 'payment_channel',
            'payment_payload', 'diperbarui',
        ))
        if payment_order.status == PaymentOrder.Status.PAID:
            _mark_property_sold(payment_order.properti_id)
    return HttpResponse('OK')


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def midtrans_notification_view(request):
    # Allow a simple browser reachability check. It never changes payment state.
    if request.method == 'GET':
        return HttpResponse('OK')

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        # Dashboard URL checks may send an empty or non-transaction probe.
        return HttpResponse('OK')

    if not isinstance(payload, dict) or not verify_midtrans_notification(payload):
        # Dashboard probes may be unsigned. For a real local invoice, query
        # Midtrans over authenticated HTTPS instead of trusting an invalid
        # notification or leaving a paid order pending after a key rotation.
        test_invoice = str(payload.get('order_id', '')) if isinstance(payload, dict) else ''
        payment_order = PaymentOrder.objects.filter(
            invoice_number=test_invoice,
            payment_gateway='midtrans',
        ).first() if test_invoice else None
        if payment_order is None:
            return HttpResponse('OK')
        try:
            authoritative_payload = _fetch_midtrans_status_for_order(payment_order, (
                test_invoice,
                payload.get('transaction_id'),
                payment_order.payment_transaction_id,
            ))
        except MidtransError as exc:
            logger.warning('Midtrans notification fallback failed for invoice %s: %s', test_invoice, exc)
            return HttpResponse('Unable to verify transaction with Midtrans', status=503)
        try:
            authoritative_amount = Decimal(str(authoritative_payload.get('gross_amount', '')))
        except (InvalidOperation, TypeError, ValueError):
            return HttpResponse('Invalid Midtrans status amount', status=502)
        if (
            str(authoritative_payload.get('order_id', '')) != test_invoice
            or authoritative_amount != payment_order.jumlah_dp
            or not authoritative_payload.get('transaction_status')
        ):
            return HttpResponse('Midtrans status does not match local order', status=502)
        payload = authoritative_payload

    invoice = str(payload.get('order_id', ''))
    try:
        amount = Decimal(str(payload.get('gross_amount', '')))
    except (InvalidOperation, TypeError, ValueError):
        return HttpResponseBadRequest('Invalid amount')
    if not invoice:
        return HttpResponseBadRequest('Missing order id')

    with transaction.atomic():
        payment_order = PaymentOrder.objects.select_for_update().filter(
            invoice_number=invoice,
            payment_gateway='midtrans',
        ).first()
        if payment_order is None:
            return HttpResponse('Unknown invoice', status=404)
        if amount != payment_order.jumlah_dp:
            return HttpResponseBadRequest('Amount mismatch')

        event_key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()
        PaymentNotificationEvent.objects.get_or_create(
            event_key=event_key,
            defaults={'payment': payment_order},
        )

        transaction_status = str(payload.get('transaction_status', '')).lower()
        fraud_status = str(payload.get('fraud_status', '')).lower()
        status_code = str(payload.get('status_code', ''))
        success = (
            status_code == '200'
            and (transaction_status == 'settlement' or transaction_status == 'capture')
            and (not fraud_status or fraud_status == 'accept')
        )
        if success:
            payment_order.status = PaymentOrder.Status.PAID
            payment_order.dibayar_pada = timezone.now()
        elif transaction_status == 'pending' and payment_order.status not in (
            PaymentOrder.Status.PAID, PaymentOrder.Status.EXPIRED, PaymentOrder.Status.FAILED,
        ):
            payment_order.status = PaymentOrder.Status.PENDING
        elif transaction_status == 'expire' and payment_order.status != PaymentOrder.Status.PAID:
            payment_order.status = PaymentOrder.Status.EXPIRED
        elif transaction_status in {'deny', 'cancel'} and payment_order.status != PaymentOrder.Status.PAID:
            payment_order.status = PaymentOrder.Status.FAILED

        va_numbers = payload.get('va_numbers') or []
        va_info = va_numbers[0] if isinstance(va_numbers, list) and va_numbers and isinstance(va_numbers[0], dict) else {}
        payment_order.payment_transaction_id = str(payload.get('transaction_id') or payment_order.payment_transaction_id)
        payment_order.payment_type = str(payload.get('payment_type') or payment_order.payment_type)
        payment_order.payment_channel = payment_order.payment_type
        payment_order.nomor_virtual_account = str(
            va_info.get('va_number')
            or payload.get('permata_va_number')
            or payment_order.nomor_virtual_account
        )
        payment_order.nama_bank = str(va_info.get('bank') or payload.get('bank') or payment_order.nama_bank)
        payment_order.payment_payload = payload
        payment_order.save(update_fields=(
            'status', 'dibayar_pada', 'payment_transaction_id', 'payment_type',
            'payment_channel', 'nomor_virtual_account', 'nama_bank',
            'payment_payload', 'diperbarui',
        ))
        if payment_order.status == PaymentOrder.Status.PAID:
            _mark_property_sold(payment_order.properti_id)
    return HttpResponse('OK')


@user_passes_test(is_admin, login_url='login')
def admin_article_edit_view(request, pk):
    article = get_object_or_404(Article, pk=pk)
    form = ArticleForm(request.POST or None, request.FILES or None, instance=article)
    if request.method == 'POST' and form.is_valid():
        updated_article = form.save(commit=False)
        if not updated_article.penulis_id:
            updated_article.penulis = request.user
        updated_article.save()
        messages.success(request, 'Artikel berhasil diperbarui.')
        return redirect('admin_articles')
    return render(request, 'admin_article_form.html', {
        'form': form,
        'article': article,
        'page_title': 'Edit Artikel',
        'active_nav': 'articles',
    })


@user_passes_test(is_admin, login_url='login')
@require_POST
def admin_article_delete_view(request, pk):
    article = get_object_or_404(Article, pk=pk)
    article.delete()
    messages.success(request, 'Artikel berhasil dihapus.')
    return redirect('admin_articles')


@user_passes_test(is_admin, login_url='login')
def admin_pages_view(request):
    form = WebsitePageForm()
    if request.method == 'POST' and 'tambah_halaman' in request.POST:
        form = WebsitePageForm(request.POST)
        if form.is_valid():
            page = form.save(commit=False)
            page.penulis = request.user
            page.save()
            messages.success(request, 'Halaman berhasil dibuat.')
            return redirect('admin_pages')

    return render(request, 'admin_pages.html', {
        'page_title': 'Kelola Halaman',
        'active_nav': 'pages',
        'form': form,
        'pages': WebsitePage.objects.select_related('penulis').all(),
        'total_halaman': WebsitePage.objects.count(),
        'halaman_terbit': WebsitePage.objects.filter(status=WebsitePage.Status.PUBLISHED).count(),
    })


@user_passes_test(is_admin, login_url='login')
def admin_page_edit_view(request, pk):
    page = get_object_or_404(WebsitePage, pk=pk)
    form = WebsitePageForm(request.POST or None, instance=page)
    if request.method == 'POST' and form.is_valid():
        saved_page = form.save(commit=False)
        if not saved_page.penulis_id:
            saved_page.penulis = request.user
        saved_page.save()
        messages.success(request, 'Halaman berhasil diperbarui.')
        return redirect('admin_pages')
    return render(request, 'admin_page_form.html', {
        'page_title': 'Edit Halaman',
        'active_nav': 'pages',
        'page': page,
        'form': form,
    })


@user_passes_test(is_admin, login_url='login')
@require_POST
def admin_page_toggle_view(request, pk):
    page = get_object_or_404(WebsitePage, pk=pk)
    page.status = WebsitePage.Status.DRAFT if page.status == WebsitePage.Status.PUBLISHED else WebsitePage.Status.PUBLISHED
    page.save(update_fields=['status', 'diperbarui'])
    messages.success(request, 'Status halaman berhasil diperbarui.')
    return redirect('admin_pages')


@user_passes_test(is_admin, login_url='login')
@require_POST
def admin_page_delete_view(request, pk):
    page = get_object_or_404(WebsitePage, pk=pk)
    page.delete()
    messages.success(request, 'Halaman berhasil dihapus.')
    return redirect('admin_pages')


def article_list_view(request):
    articles = Article.objects.filter(status=Article.Status.PUBLISHED).select_related('kategori', 'penulis')
    category_slug = request.GET.get('kategori')
    search_query = request.GET.get('q', '').strip()
    if category_slug:
        articles = articles.filter(kategori__slug=category_slug)
    if search_query:
        articles = articles.filter(
            Q(judul__icontains=search_query) | Q(ringkasan__icontains=search_query)
        )
    page_obj = Paginator(articles.distinct(), 9).get_page(request.GET.get('page'))
    context = {
        'page_obj': page_obj,
        'categories': ArticleCategory.objects.all(),
        'active_category': category_slug,
        'search_query': search_query,
        'canonical_url': request.build_absolute_uri(reverse('article_list')),
    }
    return render(request, 'articles.html', context)


def article_detail_view(request, slug):
    article = get_object_or_404(
        Article.objects.select_related('kategori', 'penulis'),
        slug=slug,
        status=Article.Status.PUBLISHED,
    )
    related_articles = Article.objects.filter(status=Article.Status.PUBLISHED).exclude(pk=article.pk).select_related('kategori', 'penulis')[:3]
    if article.kategori_id:
        category_articles = Article.objects.filter(
            kategori=article.kategori,
            status=Article.Status.PUBLISHED,
        ).exclude(pk=article.pk).select_related('kategori', 'penulis')[:3]
        if category_articles:
            related_articles = category_articles

    description = article.ringkasan
    canonical_url = request.build_absolute_uri(article.get_absolute_url())
    image_url = request.build_absolute_uri(article.gambar_utama.url) if article.gambar_utama else None
    author_name = 'Tim Agang Property'
    if article.penulis:
        author_name = article.penulis.get_full_name().strip() or article.penulis.username

    structured_data = {
        '@context': 'https://schema.org',
        '@type': 'BlogPosting',
        'mainEntityOfPage': {'@type': 'WebPage', '@id': canonical_url},
        'headline': article.judul,
        'description': description,
        'datePublished': article.dibuat.isoformat(),
        'dateModified': article.diperbarui.isoformat(),
        'author': {'@type': 'Person' if article.penulis else 'Organization', 'name': author_name},
        'publisher': {'@type': 'Organization', 'name': 'Agang Property'},
    }
    if image_url:
        structured_data['image'] = [image_url]
    if article.kategori:
        structured_data['articleSection'] = article.kategori.nama_kategori
    json_ld = json.dumps(structured_data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')

    context = {
        'article': article,
        'related_articles': related_articles,
        'canonical_url': canonical_url,
        'meta_description': description,
        'article_author': author_name,
        'json_ld': mark_safe(json_ld),
    }
    return render(request, 'article_detail.html', context)


def website_page_detail_view(request, slug):
    page = get_object_or_404(WebsitePage, slug=slug, status=WebsitePage.Status.PUBLISHED)
    return render(request, 'website_page.html', {
        'page': page,
        'canonical_url': request.build_absolute_uri(page.get_absolute_url()),
    })


def sitemap_view(request):
    namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    urlset = ElementTree.Element('urlset', {'xmlns': namespace})
    for route_name in ('home', 'catalog', 'gallery', 'about_us', 'article_list'):
        item = ElementTree.SubElement(urlset, 'url')
        ElementTree.SubElement(item, 'loc').text = request.build_absolute_uri(reverse(route_name))
    articles = Article.objects.filter(status=Article.Status.PUBLISHED)
    for article in articles:
        item = ElementTree.SubElement(urlset, 'url')
        ElementTree.SubElement(item, 'loc').text = request.build_absolute_uri(article.get_absolute_url())
        ElementTree.SubElement(item, 'lastmod').text = article.diperbarui.date().isoformat()
    for page in WebsitePage.objects.filter(status=WebsitePage.Status.PUBLISHED):
        item = ElementTree.SubElement(urlset, 'url')
        ElementTree.SubElement(item, 'loc').text = request.build_absolute_uri(page.get_absolute_url())
        ElementTree.SubElement(item, 'lastmod').text = page.diperbarui.date().isoformat()
    xml = ElementTree.tostring(urlset, encoding='utf-8', xml_declaration=True)
    return HttpResponse(xml, content_type='application/xml; charset=utf-8')


def robots_txt_view(request):
    sitemap_url = request.build_absolute_uri(reverse('sitemap'))
    content = '\n'.join((
        'User-agent: *',
        'Allow: /',
        'Disallow: /dashboard/',
        'Disallow: /admin/',
        'Disallow: /login/',
        'Disallow: /register/',
        f'Sitemap: {sitemap_url}',
        '',
    ))
    return HttpResponse(content, content_type='text/plain; charset=utf-8')

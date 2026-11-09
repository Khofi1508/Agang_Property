import json
import xml.etree.ElementTree as ElementTree

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.utils.safestring import mark_safe
from .forms import ArticleCategoryForm, ArticleForm, HeroSlideForm
from .models import (
    Article,
    ArticleCategory,
    CustomerProfile,
    Category,
    HeroSlide,
    Property,
    Testimonial,
    UpcomingProject,
    SurveyBooking,
)
from django.db.models import Q
from django.core.paginator import Paginator

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
            # Cek apakah yang login adalah Admin (Superuser) atau Pengguna biasa
            if user.is_superuser:
                messages.success(request, f'Selamat datang kembali, Admin {user.username}!')
                return redirect('admin_dashboard')
            else:
                messages.success(request, f'Selamat datang, {user.first_name or user.username}!')
                return redirect('user_dashboard')
        else:
            messages.error(request, 'Username atau password salah!')

    return render(request, 'login.html')


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
def admin_properties_view(request):
    if request.method == 'POST' and 'tambah_properti' in request.POST:
        kategori_obj = get_object_or_404(Category, id=request.POST.get('kategori'))
        Property.objects.create(
            kategori=kategori_obj,
            nama_properti=request.POST.get('nama_properti'),
            kota=request.POST.get('kota'),
            lokasi_detail=request.POST.get('lokasi_detail'),
            harga=request.POST.get('harga'),
            badge_status=request.POST.get('badge_status') or 'SIAP HUNI',
            kamar_tidur=request.POST.get('kamar_tidur'),
            kamar_mandi=request.POST.get('kamar_mandi'),
            luas_bangunan=request.POST.get('luas_bangunan'),
            status_kepemilikan=request.POST.get(
                'status_kepemilikan', 'SHM (Hak Milik) + IMB / PBG'
            ),
            deskripsi_singkat=request.POST.get('deskripsi_singkat'),
            gambar_utama=request.FILES.get('gambar_utama'),
        )
        messages.success(request, 'Data properti baru berhasil ditambahkan.')
        return redirect('admin_properties')

    context = {
        'page_title': 'Kelola Properti',
        'active_nav': 'properties',
        'categories': Category.objects.all(),
        'properties': Property.objects.select_related('kategori').order_by('-tanggal_dibuat'),
        'total_properti': Property.objects.count(),
    }
    return render(request, 'admin_properties.html', context)


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
            return redirect('admin_articles')

    context = {
        'page_title': 'Kelola Artikel',
        'active_nav': 'articles',
        'articles': Article.objects.select_related('kategori', 'penulis').order_by('-diperbarui'),
        'article_categories': ArticleCategory.objects.all(),
        'article_form': article_form,
        'article_category_form': article_category_form,
        'total_artikel': Article.objects.count(),
        'total_artikel_terbit': Article.objects.filter(status=Article.Status.PUBLISHED).count(),
    }
    return render(request, 'admin_articles.html', context)


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

    # Pengguna bisa mengirim review/testimoni dari dashboard mereka
    if request.method == 'POST' and 'kirim_ulasan' in request.POST:
        Testimonial.objects.create(
            user=request.user,
            nama_pengulas=request.user.first_name or request.user.username,
            ulasan=request.POST.get('ulasan'),
            rating_bintang=request.POST.get('rating_bintang', 5)
        )
        messages.success(request, 'Terima kasih! Ulasan Anda berhasil dikirim.')
        return redirect('user_dashboard')

    context = {
        'profile': profile,
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
        return redirect('user_dashboard')

    return render(request, 'user_edit_profile.html', {'profile': profile})

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
        'list_furnitur': list_furnitur,
        'list_fasilitas': list_fasilitas,
        'properti_serupa': properti_serupa,
    }
    return render(request, 'detail_unit.html', context)


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


def article_list_view(request):
    articles = Article.objects.filter(
        status=Article.Status.PUBLISHED,
        tanggal_terbit__lte=timezone.now(),
    ).select_related('kategori', 'penulis')
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
        tanggal_terbit__lte=timezone.now(),
    )
    related_articles = Article.objects.filter(
        status=Article.Status.PUBLISHED,
        tanggal_terbit__lte=timezone.now(),
    ).exclude(pk=article.pk).select_related('kategori', 'penulis')[:3]
    if article.kategori_id:
        category_articles = Article.objects.filter(
            kategori=article.kategori,
            status=Article.Status.PUBLISHED,
            tanggal_terbit__lte=timezone.now(),
        ).exclude(pk=article.pk).select_related('kategori', 'penulis')[:3]
        if category_articles:
            related_articles = category_articles

    description = article.deskripsi_seo or article.ringkasan
    canonical_url = article.url_canonical or request.build_absolute_uri(article.get_absolute_url())
    image_url = request.build_absolute_uri(article.gambar_utama.url) if article.gambar_utama else None
    author_name = 'Tim Agang Property'
    if article.penulis:
        author_name = article.penulis.get_full_name().strip() or article.penulis.username

    structured_data = {
        '@context': 'https://schema.org',
        '@type': 'BlogPosting',
        'mainEntityOfPage': {'@type': 'WebPage', '@id': canonical_url},
        'headline': article.judul_seo or article.judul,
        'description': description,
        'datePublished': (article.tanggal_terbit or article.dibuat).isoformat(),
        'dateModified': article.diperbarui.isoformat(),
        'author': {'@type': 'Person' if article.penulis else 'Organization', 'name': author_name},
        'publisher': {'@type': 'Organization', 'name': 'Agang Property'},
    }
    if image_url:
        structured_data['image'] = [image_url]
    if article.kategori:
        structured_data['articleSection'] = article.kategori.nama_kategori
    if article.kata_kunci:
        structured_data['keywords'] = [word.strip() for word in article.kata_kunci.split(',') if word.strip()]
    json_ld = json.dumps(structured_data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')

    context = {
        'article': article,
        'related_articles': related_articles,
        'canonical_url': canonical_url,
        'meta_description': description,
        'article_author': author_name,
        'key_points': [line.strip() for line in article.poin_utama.splitlines() if line.strip()],
        'json_ld': mark_safe(json_ld),
    }
    return render(request, 'article_detail.html', context)


def sitemap_view(request):
    namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    urlset = ElementTree.Element('urlset', {'xmlns': namespace})
    for route_name in ('home', 'catalog', 'article_list'):
        item = ElementTree.SubElement(urlset, 'url')
        ElementTree.SubElement(item, 'loc').text = request.build_absolute_uri(reverse(route_name))
    articles = Article.objects.filter(
        status=Article.Status.PUBLISHED,
        tanggal_terbit__lte=timezone.now(),
    )
    for article in articles:
        item = ElementTree.SubElement(urlset, 'url')
        ElementTree.SubElement(item, 'loc').text = request.build_absolute_uri(article.get_absolute_url())
        ElementTree.SubElement(item, 'lastmod').text = (article.diperbarui or article.tanggal_terbit).date().isoformat()
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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import CustomerProfile, Category, Property, Testimonial, UpcomingProject

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
    # Admin bisa menambahkan properti baru langsung dari dashboard jika ada request POST
    if request.method == 'POST' and 'tambah_properti' in request.POST:
        kategori_id = request.POST.get('kategori')
        kategori_obj = get_object_or_404(Category, id=kategori_id)
        Property.objects.create(
            kategori=kategori_obj,
            nama_properti=request.POST.get('nama_properti'),
            kota=request.POST.get('kota'),
            lokasi_detail=request.POST.get('lokasi_detail'),
            harga=request.POST.get('harga'),
            badge_status=request.POST.get('badge_status'),
            kamar_tidur=request.POST.get('kamar_tidur'),
            kamar_mandi=request.POST.get('kamar_mandi'),
            luas_bangunan=request.POST.get('luas_bangunan'),
            status_furnitur_sertifikat=request.POST.get('status_furnitur_sertifikat', 'Full Furnished'),
            deskripsi_singkat=request.POST.get('deskripsi_singkat'),
            gambar_utama=request.FILES.get('gambar_utama'),
        )
        messages.success(request, 'Data properti baru berhasil ditambahkan!')
        return redirect('admin_dashboard')

    context = {
        'total_properti': Property.objects.count(),
        'total_customer': User.objects.filter(is_superuser=False).count(),
        'total_testimoni': Testimonial.objects.count(),
        'total_upcoming': UpcomingProject.objects.count(),
        'properties': Property.objects.all().order_by('-tanggal_dibuat'),
        'categories': Category.objects.all(),
        'customers': CustomerProfile.objects.select_related('user').filter(user__is_superuser=False),
    }
    return render(request, 'admin_dashboard.html', context)


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

    return render(request, 'admin_edit_profile.html', {'profile': profile})


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
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# 1. MODEL PROFIL CUSTOMER (Login, Registrasi, Profil & Edit Profil)
class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    no_telepon = models.CharField(max_length=20, blank=True, null=True)
    alamat = models.TextField(blank=True, null=True)
    foto_profil = models.ImageField(upload_to='profil_customer/', blank=True, null=True)
    tanggal_daftar = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Profil Customer'
        verbose_name_plural = 'Profil Customer'

    def __str__(self):
        return f"Profil {self.user.username}"


# 2. MODEL KATEGORI HUNIAN (Filter Tab & Dropdown Tipe Properti)
class Category(models.Model):
    # Contoh: Cluster Tengah Kota, Villa & Resort, Modern Minimalis
    nama_kategori = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, help_text="Contoh: cluster-tengah-kota")

    class Meta:
        verbose_name = 'Kategori Properti'
        verbose_name_plural = 'Kategori Properti'

    def __str__(self):
        return self.nama_kategori


# 3. MODEL KATALOG PROPERTI (Mendukung Halaman Home & Halaman Katalog)
class Property(models.Model):
    STATUS_UNIT_CHOICES = [
        ('Siap Huni', 'Siap Huni (Ready Stock)'),
        ('SHM Ready', 'SHM Ready Makassar'),
        ('Indent', 'Indent / Pre-Booking'),
    ]

    kategori = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='properties')
    nama_cluster = models.CharField(max_length=100, default="CLUSTER EXCLUSIVE", help_text="Contoh: CLUSTER GREEN RIVER")
    nama_properti = models.CharField(max_length=200, help_text="Contoh: Rumah Tinggal Cluster...")
    
    # Lokasi untuk filter Wilayah Strategis & teks lokasi
    kota = models.CharField(max_length=100, default="Makassar", help_text="Contoh: Makassar, Gowa, Maros")
    lokasi_detail = models.CharField(max_length=150, help_text="Contoh: Green River, Tanjung Bunga, Makassar")
    
    # Harga & Estimasi Cicilan KPR (Tampil di atas gambar pada halaman Katalog)
    harga = models.DecimalField(max_digits=15, decimal_places=0, help_text="Contoh: 460000000")
    estimasi_cicilan = models.CharField(max_length=50, default="Cicilan ~3,1 Jt/bln", help_text="Contoh: Cicilan ~3,1 Jt/bln")
    
    # Dua Badge di Pojok Kiri Atas Gambar & Filter Legalitas
    badge_status = models.CharField(max_length=50, default="SIAP HUNI", help_text="Badge 1 (Merah), contoh: SIAP HUNI, ECO-LIVING, BEST SELLER")
    badge_kedua = models.CharField(max_length=50, blank=True, null=True, default="SHM READY", help_text="Badge 2 (Gelap), contoh: SHM READY, SOLAR READY, PRIVATE POOL")
    status_legalitas = models.CharField(max_length=50, choices=STATUS_UNIT_CHOICES, default='Siap Huni')
    
    gambar_utama = models.ImageField(upload_to='properti/')
    deskripsi_singkat = models.TextField()
    
    # 4 Spesifikasi Utama (Lantai, K. Tidur, K. Mandi, Luas)
    jumlah_lantai = models.PositiveSmallIntegerField(default=1, help_text="Jumlah Lantai, misal: 1 atau 2")
    kamar_tidur = models.CharField(max_length=20, default="2", help_text="Jumlah K. Tidur, bisa angka '2' atau teks '4+1'")
    kamar_mandi = models.PositiveSmallIntegerField(default=1, help_text="Jumlah K. Mandi")
    luas_bangunan = models.PositiveIntegerField(default=60, help_text="Luas Bangunan dalam m2, misal: 60, 110, 180")
    
    tampil_di_home = models.BooleanField(default=True)
    tanggal_dibuat = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Katalog Properti'
        verbose_name_plural = 'Katalog Properti'

    def __str__(self):
        return f"{self.nama_properti} ({self.lokasi_detail})"

    @property
    def harga_format_titik(self):
        return f"{int(self.harga):,}".replace(",", ".")


# 4. MODEL TESTIMONI ("Kata Mereka")
class Testimonial(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nama_pengulas = models.CharField(max_length=100, help_text="Contoh: Rustang, Tamring, Hj. Tenri")
    waktu_relatif = models.CharField(max_length=50, default="a week ago", help_text="Contoh: a week ago, a month ago")
    ulasan = models.TextField()
    rating_bintang = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    tampil_di_home = models.BooleanField(default=True)
    tanggal_ulasan = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Testimoni (Kata Mereka)'
        verbose_name_plural = 'Testimoni (Kata Mereka)'

    def __str__(self):
        return f"{self.nama_pengulas} - {self.rating_bintang} Bintang"


# 5. MODEL PROYEK MENDATANG ("Upcoming Private Phase - Dates Available for Handover")
class UpcomingProject(models.Model):
    # --- Kolom untuk Header Section (Diambil dari proyek urutan pertama / Highlight Utama) ---
    tag_section = models.CharField(
        max_length=100, 
        default="● UPCOMING PRIVATE PHASE", 
        help_text="Teks label kecil di bagian paling atas section"
    )
    judul_periode = models.CharField(
        max_length=150, 
        default="Spring / Summer 2026", 
        help_text="Judul utama baris pertama"
    )
    subjudul_emas = models.CharField(
        max_length=150, 
        default="Dates Available for Handover", 
        help_text="Sub-judul miring berwarna emas di baris kedua"
    )
    deskripsi_header = models.TextField(
        default="Pemesanan tahap perdana untuk kawasan residensial terpadu dengan fasilitas clubhouse privat, jogging track hutan kota, dan gerbang akses RFID terpadu.",
        help_text="Paragraf penjelasan di sebelah kanan judul utama"
    )

    # --- Kolom untuk Isi Kartu Proyek (Kartu Besar Kiri & Kartu Kecil Kanan) ---
    nama_proyek = models.CharField(max_length=200, help_text="Contoh: Grand Agang Boulevard & Eco Precinct")
    badge_info = models.CharField(max_length=100, help_text="Contoh: TAHAP 1 - OPEN PRE-BOOKING, 12 Unit Sisa, VIP Launch")
    ikon_kartu = models.CharField(max_length=10, default="⌂", blank=True, null=True, help_text="Ikon khusus kartu kecil di kanan, contoh: ⌂ atau ≈")
    deskripsi = models.TextField(help_text="Deskripsi singkat proyek di dalam kartu")
    harga_mulai = models.CharField(max_length=100, blank=True, null=True, help_text="Khusus kartu besar kiri, contoh: Mulai Rp 720 Jt")
    estimasi_serah_terima = models.CharField(max_length=100, help_text="Contoh: Serah Terima Juni 2026 atau Indikasi: Q3 2026")
    gambar = models.ImageField(upload_to='upcoming_projects/', blank=True, null=True, help_text="Foto background khusus untuk kartu besar di sebelah kiri")
    
    # --- Pengaturan Posisi Kartu ---
    is_highlight_utama = models.BooleanField(
        default=False,
        help_text="Centang (True) agar tampil sebagai Kartu Besar di Kiri. Biarkan kosong (False) untuk Kartu Kecil di Kanan."
    )
    urutan_tampil = models.PositiveIntegerField(default=1, help_text="Urutan tampil (isi angka 1 untuk proyek utama)")

    class Meta:
        ordering = ['urutan_tampil']
        verbose_name = 'Proyek Mendatang (Handover)'
        verbose_name_plural = 'Proyek Mendatang (Handover)'

    def __str__(self):
        posisi = "Kartu Utama Kiri" if self.is_highlight_utama else "Kartu Samping Kanan"
        return f"{self.nama_proyek} ({posisi})"
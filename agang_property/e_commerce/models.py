from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# 1. MODEL UNTUK REGISTRASI, LOGIN, PROFIL & EDIT PROFIL CUSTOMER
class CustomerProfile(models.Model):
    # Terhubung 1-ke-1 dengan tabel User bawaan Django (menyimpan username, email, nama, password)
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


# 2. MODEL KATEGORI HUNIAN (Untuk Tab Filter & Pencarian Tipe Hunian di Home)
class Category(models.Model):
    # Contoh isi: Cluster Tengah Kota, Villa & Resort, Modern Minimalis
    nama_kategori = models.CharField(max_length=100, null=True, blank=True, help_text="Contoh: Cluster Tengah Kota, Villa & Resort, Modern Minimalis")
    slug = models.SlugField(unique=True, null=True, default=True, help_text="Ketik huruf kecil semua dengan tanda strip, misal: cluster-tengah-kota")

    class Meta:
        verbose_name = 'Kategori Properti'
        verbose_name_plural = 'Kategori Properti'

    def __str__(self):
        return self.nama_kategori


# 3. MODEL KATALOG PROPERTI (Bagian "Explore your Homies" & Bar Pencarian)
class Property(models.Model):
    kategori = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='properties')
    nama_properti = models.CharField(max_length=200, help_text="Contoh: Rumah Tinggal Cluster...")
    
    # Untuk filter pencarian Lokasi & label lokasi di foto
    kota = models.CharField(max_length=100, help_text="Contoh: Makassar, Maros, Gowa")
    lokasi_detail = models.CharField(max_length=150, help_text="Contoh: Panakkukang, Makassar")
    
    # Harga & Label
    label_harga = models.CharField(max_length=50, default="HARGA MULAI DARI", help_text="Contoh: HARGA MULAI DARI atau PENAWARAN SPESIAL")
    harga = models.DecimalField(max_digits=15, decimal_places=0, help_text="Masukkan angka saja, misal: 450000000")
    
    # Badge pojok kanan atas foto & Gambar
    badge_status = models.CharField(max_length=50, blank=True, null=True, help_text="Contoh: Sisa 1 Unit, Tersisa 2 Unit, Eksklusif")
    gambar_utama = models.ImageField(upload_to='properti/')
    deskripsi_singkat = models.TextField()
    
    # 4 Ikon Spesifikasi di Kartu Properti
    kamar_tidur = models.PositiveIntegerField(help_text="Jumlah KT, misal: 2")
    kamar_mandi = models.PositiveIntegerField(help_text="Jumlah KM, misal: 2")
    luas_bangunan = models.PositiveIntegerField(help_text="Luas dalam m2, misal: 90")
    status_furnitur_sertifikat = models.CharField(max_length=50, default="Full Furnished", help_text="Contoh: SHM atau Full Furnished")
    
    tampil_di_home = models.BooleanField(default=True)
    tanggal_dibuat = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Katalog Properti'
        verbose_name_plural = 'Katalog Properti'

    def __str__(self):
        return f"{self.nama_properti} - {self.lokasi_detail}"


# 4. MODEL REVIEW / TESTIMONI (Bagian "Kata Mereka")
class Testimonial(models.Model):
    # Opsional terhubung ke User jika customer yang login menekan tombol "BERI REVIEW +"
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nama_pengulas = models.CharField(max_length=100, help_text="Contoh: Rahmat, Sartika")
    ulasan = models.TextField()
    rating_bintang = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Nilai bintang 1 sampai 5"
    )
    tampil_di_home = models.BooleanField(default=True)
    tanggal_ulasan = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Testimoni (Kata Mereka)'
        verbose_name_plural = 'Testimoni (Kata Mereka)'

    def __str__(self):
        return f"{self.nama_pengulas} ({self.rating_bintang} Bintang)"


# 5. MODEL PROYEK MENDATANG (Bagian "Spring / Summer 2026 - Dates Available for Handover")
class UpcomingProject(models.Model):
    nama_proyek = models.CharField(max_length=200, help_text="Contoh: Grand Agang Boulevard & Eco Precinct")
    badge_info = models.CharField(max_length=100, help_text="Contoh: 12 Unit Tersisa, VIP Launching")
    deskripsi = models.TextField()
    lokasi = models.CharField(max_length=150, blank=True, null=True, help_text="Contoh: Hertasning Baru")
    estimasi_serah_terima = models.CharField(max_length=100, help_text="Contoh: Serah Terima Q3 2026 atau Estimasi Q2 2026")
    gambar = models.ImageField(upload_to='upcoming_projects/', blank=True, null=True, help_text="Diisi khusus untuk kartu highlight utama yang besar di sebelah kiri")
    is_highlight_utama = models.BooleanField(
        default=False, 
        help_text="Centang jika proyek ini ditampilkan sebagai kartu bergambar besar di sebelah kiri"
    )
    urutan_tampil = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['urutan_tampil']
        verbose_name = 'Proyek Mendatang (Handover)'
        verbose_name_plural = 'Proyek Mendatang (Handover)'

    def __str__(self):
        return self.nama_proyek
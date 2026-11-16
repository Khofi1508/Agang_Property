from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from django.utils.text import slugify
import uuid

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
    class StatusPenjualan(models.TextChoices):
        AVAILABLE = 'available', 'Tersedia'
        SOLD = 'sold', 'Sold'

    STATUS_UNIT_CHOICES = [
        ('Siap Huni', 'Siap Huni (Ready Stock)'),
        ('SHM Ready', 'SHM Ready Makassar'),
        ('Indent', 'Indent / Pre-Booking'),
    ]

    kategori = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='properties')
    nama_cluster = models.CharField(max_length=100, default="CLUSTER EXCLUSIVE")
    nama_properti = models.CharField(max_length=200)
    kode_properti = models.CharField(max_length=50, default="AG-CT-048", help_text="Contoh: AG-CT-048")
    
    # Lokasi
    kota = models.CharField(max_length=100, default="Makassar")
    lokasi_detail = models.CharField(max_length=150, help_text="Contoh: Kawasan Green River, Tanjung Bunga, Makassar")
    
    # Harga & Cicilan
    harga = models.DecimalField(max_digits=15, decimal_places=0)
    harga_coret = models.DecimalField(max_digits=15, decimal_places=0, blank=True, null=True, help_text="Harga sebelum diskon/promo")
    estimasi_cicilan = models.CharField(max_length=50, default="Cicilan mulai Rp 3,3 Jt-an / bulan")
    
    # Badge & Status
    badge_status = models.CharField(max_length=50, default="SIAP HUNI (READY STOCK)")
    badge_kedua = models.CharField(max_length=50, blank=True, null=True, default="SHM & IMB LENGKAP")
    badge_ketiga = models.CharField(max_length=50, blank=True, null=True, default="HADAP UTARA")
    status_legalitas = models.CharField(max_length=50, choices=STATUS_UNIT_CHOICES, default='Siap Huni')
    status_penjualan = models.CharField(
        max_length=12,
        choices=StatusPenjualan.choices,
        default=StatusPenjualan.AVAILABLE,
        db_index=True,
        verbose_name='Status penjualan',
    )
    
    # Foto & Deskripsi
    gambar_utama = models.ImageField(upload_to='properti/')
    deskripsi_singkat = models.TextField()
    deskripsi_panjang = models.TextField(blank=True, null=True, help_text="Paragraf penjelasan di bawah galeri foto")
    youtube_video_url = models.URLField(
        blank=True,
        help_text="Tautan video YouTube untuk galeri properti, contoh https://youtu.be/abc123",
    )
    
    # Spesifikasi Utama (6 Kotak Atas)
    jumlah_lantai = models.PositiveSmallIntegerField(default=1)
    kamar_tidur = models.CharField(max_length=20, default="2 KT")
    kamar_mandi = models.PositiveSmallIntegerField(default=1)
    luas_bangunan = models.PositiveIntegerField(default=60)
    luas_tanah = models.PositiveIntegerField(default=72)
    arah_hadap = models.CharField(max_length=50, default="Utara")
    daftar_furnitur = models.TextField(
        default="Sofa Ruang Tamu, Meja Makan Set, Tempat Tidur Utama, Kitchen Set, AC tiap kamar",
        help_text="Pisahkan item dengan tanda koma (,).",
    )
    fasilitas_lingkungan = models.TextField(
        default="One Gate System, Keamanan 24 Jam & CCTV, Taman Bermain, Jalan Paving Lebar",
        help_text="Pisahkan item dengan tanda koma (,).",
    )

    # Spesifikasi Konstruksi & Material (Tabel Kiri Bawah)
    status_kepemilikan = models.CharField(max_length=150, default="SHM (Hak Milik) + IMB / PBG")
    daya_listrik = models.CharField(max_length=100, default="2.200 VA (Token Prabayar)")
    sumber_air = models.CharField(max_length=100, default="PDAM Kota & Jet Pump Otomatis")
    pondasi = models.CharField(max_length=150, default="Batu Kali & Beton Bertulang")
    struktur_dinding = models.CharField(max_length=150, default="Bata Merah Plester Aci Fin. Jotun")
    kusen_jendela = models.CharField(max_length=150, default="Aluminium Powder Coating YKK")
    lantai_utama = models.CharField(max_length=150, default="Granite Tile 60 x 60 Glazed Polish")
    sanitari_km = models.CharField(max_length=150, default="Monoblok TOTO, Shower Set Germany Brilliant")
    rangka_atap = models.CharField(max_length=150, default="Baja Ringan & Genteng Keramik Kanmuri")
    lebar_jalan_row = models.CharField(max_length=150, default="Paving 8 Meter (Bisa Papasan 2 Mobil)")

    # Ulasan & Nilai Investasi (Teks bawah)
    ulasan_investasi = models.TextField(blank=True, null=True, help_text="Teks untuk bagian Ulasan & Nilai Investasi Properti")

    tampil_di_home = models.BooleanField(default=True)
    tanggal_dibuat = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nama_properti} ({self.lokasi_detail})"

    @property
    def harga_format_titik(self):
        return f"{int(self.harga):,}".replace(",", ".")

    @property
    def harga_coret_format(self):
        if self.harga_coret:
            return f"{int(self.harga_coret):,}".replace(",", ".")
        return ""


class PropertyGalleryImage(models.Model):
    properti = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='foto_galeri')
    gambar = models.ImageField(upload_to='properti/galeri/')
    keterangan = models.CharField(max_length=150, blank=True)
    urutan = models.PositiveSmallIntegerField(default=1)
    diunggah = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['urutan', 'id']
        verbose_name = 'Foto Galeri Properti'
        verbose_name_plural = 'Foto Galeri Properti'

    def __str__(self):
        return f'{self.properti.nama_properti} - foto {self.urutan}'


class PaymentOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Menunggu Pembayaran'
        PAID = 'paid', 'Lunas'
        EXPIRED = 'expired', 'Kedaluwarsa'
        FAILED = 'failed', 'Gagal'

    PAYMENT_GATEWAY_CHOICES = [
        ('midtrans', 'Midtrans Sandbox'),
        ('doku', 'DOKU Checkout Sandbox'),
        ('doku_legacy', 'DOKU (transaksi lama)'),
    ]

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    invoice_number = models.CharField(max_length=30, unique=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='property_payments')
    properti = models.ForeignKey(Property, on_delete=models.PROTECT, related_name='payment_orders')
    jumlah_dp = models.DecimalField(max_digits=15, decimal_places=0)
    persentase_dp = models.DecimalField(max_digits=5, decimal_places=2)
    bunga_tetap = models.DecimalField(max_digits=5, decimal_places=2, default=4.50)
    masa_bunga_tetap = models.PositiveSmallIntegerField(default=1)
    tenor_tahun = models.PositiveSmallIntegerField(default=15)
    metode_pembayaran = models.CharField(max_length=50, default='Midtrans Snap')
    payment_gateway = models.CharField(max_length=20, choices=PAYMENT_GATEWAY_CHOICES, default='midtrans')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    payment_url = models.URLField(max_length=1000, blank=True)
    payment_token = models.CharField(max_length=120, blank=True)
    payment_transaction_id = models.CharField(max_length=100, blank=True)
    payment_type = models.CharField(max_length=50, blank=True)
    nomor_virtual_account = models.CharField(max_length=80, blank=True)
    nama_bank = models.CharField(max_length=80, blank=True)
    payment_channel = models.CharField(max_length=80, blank=True)
    payment_payload = models.JSONField(default=dict, blank=True)
    jatuh_tempo = models.DateTimeField()
    dibayar_pada = models.DateTimeField(blank=True, null=True)
    dibuat = models.DateTimeField(auto_now_add=True)
    diperbarui = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-dibuat']
        verbose_name = 'Pembayaran Down Payment'
        verbose_name_plural = 'Pembayaran Down Payment'

    def __str__(self):
        return f'{self.invoice_number} - {self.get_status_display()}'

    @property
    def jumlah_dp_format(self):
        return f'{int(self.jumlah_dp):,}'.replace(',', '.')


class PaymentNotificationEvent(models.Model):
    event_key = models.CharField(max_length=128, unique=True)
    payment = models.ForeignKey(PaymentOrder, on_delete=models.CASCADE, related_name='notifications')
    diterima = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notifikasi Pembayaran Gateway'
        verbose_name_plural = 'Notifikasi Pembayaran Gateway'

    def __str__(self):
        return f'{self.event_key} - {self.payment.invoice_number}'


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



# 6. MODEL JADWAL SURVEI LOKASI (Diakses dari Halaman Detail Unit)
class SurveyBooking(models.Model):
    STATUS_SURVEI = [
        ('Menunggu Konfirmasi', 'Menunggu Konfirmasi'),
        ('Terjadwal', 'Terjadwal'),
        ('Selesai', 'Selesai Survei'),
        ('Dibatalkan', 'Dibatalkan'),
    ]

    SESI_WAKTU = [
        ('Pagi (09:00 - 11:30 WITA)', 'Pagi (09:00 - 11:30 WITA)'),
        ('Siang (13:00 - 15:00 WITA)', 'Siang (13:00 - 15:00 WITA)'),
        ('Sore (15:30 - 17:30 WITA)', 'Sore (15:30 - 17:30 WITA)'),
    ]

    properti = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='surveys')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nama_pemohon = models.CharField(max_length=150)
    no_whatsapp = models.CharField(max_length=25)
    tanggal_survei = models.DateField()
    sesi_waktu = models.CharField(max_length=50, choices=SESI_WAKTU, default='Pagi (09:00 - 11:30 WITA)')
    catatan = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_SURVEI, default='Menunggu Konfirmasi')
    tanggal_dibuat = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-tanggal_survei']
        verbose_name = 'Jadwal Survei Lokasi'
        verbose_name_plural = 'Jadwal Survei Lokasi'

    def __str__(self):
        return f"Survei {self.properti.nama_properti} - {self.nama_pemohon} ({self.tanggal_survei})"


#7 Artikel & Kategori Artikel (Blog, Tips Properti, Berita Properti)
class ArticleCategory(models.Model):
    nama_kategori = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    deskripsi = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ['nama_kategori']
        verbose_name = 'Kategori Artikel'
        verbose_name_plural = 'Kategori Artikel'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.nama_kategori) or 'artikel'
            slug = base_slug
            suffix = 2
            while ArticleCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{suffix}'
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nama_kategori


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Terbit'

    kategori = models.ForeignKey(
        ArticleCategory,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='artikel',
    )
    penulis = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='artikel_agang',
    )
    judul = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    ringkasan = models.TextField(help_text='Deskripsi singkat artikel.')
    isi = models.TextField(help_text='Isi lengkap artikel.')
    gambar_utama = models.ImageField(upload_to='artikel/', blank=True, null=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    dibuat = models.DateTimeField(auto_now_add=True)
    diperbarui = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-dibuat']
        verbose_name = 'Artikel'
        verbose_name_plural = 'Artikel'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.judul) or 'artikel'
            slug = base_slug
            suffix = 2
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{suffix}'
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('article_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.judul

# 10 Halaman
class WebsitePage(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Terbit'

    judul = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    ringkasan = models.CharField(max_length=320, blank=True)
    isi = models.TextField(help_text='Tulis isi halaman dengan paragraf yang jelas.')
    penulis = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='halaman_agang',
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    dibuat = models.DateTimeField(auto_now_add=True)
    diperbarui = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['judul']
        verbose_name = 'Halaman Website'
        verbose_name_plural = 'Halaman Website'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.judul) or 'halaman'
            slug = base_slug
            suffix = 2
            while WebsitePage.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{suffix}'
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('website_page_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.judul

#8 Web Setting
class WebSetting(models.Model):
    """Pengaturan umum website. Hanya satu record yang digunakan."""
    nama_website = models.CharField(max_length=120, default='Agang Property')
    tagline = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(
        upload_to='website/',
        blank=True,
        null=True,
        help_text='Logo ini digunakan pada brand/header, footer, dan area admin website.',
    )
    favicon = models.ImageField(
        upload_to='website/',
        blank=True,
        null=True,
        help_text='Ikon kecil pada tab browser. Gunakan PNG persegi atau file ICO.',
    )
    email_kontak = models.EmailField(blank=True)
    telepon_kontak = models.CharField(max_length=30, blank=True)
    whatsapp = models.CharField(
        max_length=30,
        blank=True,
        help_text='Gunakan format internasional, contoh: 628118900234.',
    )
    alamat = models.TextField(blank=True)
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    deskripsi_seo = models.CharField(max_length=320, blank=True)
    teks_footer = models.CharField(
        max_length=200,
        default='Seluruh hak cipta dilindungi undang-undang.',
    )
    diperbarui = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pengaturan Website'
        verbose_name_plural = 'Pengaturan Website'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nama_website

#9 Hero Slide
class HeroSlide(models.Model):
    tagline = models.CharField(max_length=100, default='MASTERPIECE COLLECTION')
    judul = models.CharField(max_length=140)
    judul_aksen = models.CharField(max_length=140)
    deskripsi = models.TextField(max_length=500)
    gambar = models.ImageField(upload_to='hero_slides/')
    label_tombol = models.CharField(max_length=50, default='JELAJAHI PROPERTI')
    urutan = models.PositiveSmallIntegerField(default=1)
    aktif = models.BooleanField(default=True)
    dibuat = models.DateTimeField(auto_now_add=True)
    diperbarui = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['urutan', '-dibuat']
        verbose_name = 'Hero Slide'
        verbose_name_plural = 'Hero Slides'

    def __str__(self):
        return f'{self.urutan}. {self.judul} {self.judul_aksen}'

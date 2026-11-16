from django.contrib import admin
from .models import (
    Article,
    ArticleCategory,
    CustomerProfile,
    Category,
    HeroSlide,
    PaymentOrder,
    PaymentNotificationEvent,
    Property,
    PropertyGalleryImage,
    Testimonial,
    UpcomingProject,
    SurveyBooking,
    WebSetting,
    WebsitePage,
)


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ('judul', 'judul_aksen', 'urutan', 'aktif', 'diperbarui')
    list_filter = ('aktif',)
    list_editable = ('urutan', 'aktif')
    search_fields = ('judul', 'judul_aksen', 'tagline', 'deskripsi')


@admin.register(WebSetting)
class WebSettingAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Identitas Website', {'fields': ('nama_website', 'tagline', 'logo', 'favicon')}),
        ('Informasi Kontak', {'fields': ('email_kontak', 'telepon_kontak', 'whatsapp', 'alamat')}),
        ('Media Sosial', {'fields': ('instagram_url', 'facebook_url', 'youtube_url')}),
        ('SEO dan Footer', {'fields': ('deskripsi_seo', 'teks_footer', 'diperbarui')}),
    )
    readonly_fields = ('diperbarui',)

    def has_add_permission(self, request):
        return not WebSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ('nama_kategori', 'slug')
    search_fields = ('nama_kategori',)
    prepopulated_fields = {'slug': ('nama_kategori',)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('judul', 'kategori', 'penulis', 'status', 'diperbarui')
    list_filter = ('status', 'kategori')
    search_fields = ('judul', 'ringkasan', 'isi')
    prepopulated_fields = {'slug': ('judul',)}
    readonly_fields = ('dibuat', 'diperbarui')
    fieldsets = (
        ('Konten artikel', {'fields': ('judul', 'slug', 'ringkasan', 'isi', 'gambar_utama')}),
        ('Kategori dan publikasi', {'fields': ('kategori', 'penulis', 'status')}),
        ('Waktu', {'fields': ('dibuat', 'diperbarui')}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.penulis_id:
            obj.penulis = request.user
        super().save_model(request, obj, form, change)


@admin.register(WebsitePage)
class WebsitePageAdmin(admin.ModelAdmin):
    list_display = ('judul', 'slug', 'status', 'diperbarui')
    list_filter = ('status',)
    search_fields = ('judul', 'ringkasan', 'isi')
    prepopulated_fields = {'slug': ('judul',)}
    readonly_fields = ('dibuat', 'diperbarui')

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'no_telepon', 'tanggal_daftar')
    search_fields = ('user__username', 'user__email', 'no_telepon')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('nama_kategori', 'slug')
    prepopulated_fields = {'slug': ('nama_kategori',)}

class PropertyGalleryImageInline(admin.TabularInline):
    model = PropertyGalleryImage
    extra = 1


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('nama_properti', 'nama_cluster', 'kategori', 'kota', 'harga', 'status_penjualan', 'badge_status', 'tampil_di_home')
    list_filter = ('status_penjualan', 'kategori', 'kota', 'tampil_di_home')
    search_fields = ('nama_properti', 'nama_cluster', 'lokasi_detail', 'kota')
    list_editable = ('status_penjualan', 'tampil_di_home', 'badge_status')
    inlines = (PropertyGalleryImageInline,)


@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'user', 'properti', 'jumlah_dp', 'payment_gateway', 'status', 'jatuh_tempo', 'dibayar_pada')
    list_filter = ('status', 'dibuat')
    search_fields = ('invoice_number', 'user__username', 'user__email', 'properti__nama_properti', 'nomor_virtual_account')
    readonly_fields = ('reference', 'invoice_number', 'user', 'properti', 'jumlah_dp', 'persentase_dp', 'bunga_tetap', 'masa_bunga_tetap', 'tenor_tahun', 'metode_pembayaran', 'payment_gateway', 'payment_url', 'payment_token', 'payment_transaction_id', 'payment_type', 'nomor_virtual_account', 'nama_bank', 'payment_channel', 'payment_payload', 'jatuh_tempo', 'dibayar_pada', 'dibuat', 'diperbarui')

    def has_add_permission(self, request):
        return False


@admin.register(PaymentNotificationEvent)
class PaymentNotificationEventAdmin(admin.ModelAdmin):
    list_display = ('event_key', 'payment', 'diterima')
    search_fields = ('event_key', 'payment__invoice_number')
    readonly_fields = ('event_key', 'payment', 'diterima')

    def has_add_permission(self, request):
        return False

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('nama_pengulas', 'rating_bintang', 'tampil_di_home', 'tanggal_ulasan')
    list_filter = ('rating_bintang', 'tampil_di_home')
    list_editable = ('tampil_di_home',)

@admin.register(UpcomingProject)
class UpcomingProjectAdmin(admin.ModelAdmin):
    list_display = ('nama_proyek', 'badge_info', 'estimasi_serah_terima', 'is_highlight_utama', 'urutan_tampil')
    list_editable = ('is_highlight_utama', 'urutan_tampil')
    fieldsets = (
        ('Pengaturan Teks Header Section (Diambil dari Proyek Urutan Ke-1)', {
            'fields': ('tag_section', 'judul_periode', 'subjudul_emas', 'deskripsi_header')
        }),
        ('Detail Kartu Proyek (Kiri & Kanan)', {
            'fields': (
                'nama_proyek', 'badge_info', 'ikon_kartu', 'deskripsi', 
                'harga_mulai', 'estimasi_serah_terima', 'gambar', 
                'is_highlight_utama', 'urutan_tampil'
            )
        }),
    )

@admin.register(SurveyBooking)
class SurveyBookingAdmin(admin.ModelAdmin):
    list_display = ('nama_pemohon', 'properti', 'tanggal_survei', 'sesi_waktu', 'no_whatsapp', 'status')
    list_filter = ('status', 'tanggal_survei', 'sesi_waktu')
    search_fields = ('nama_pemohon', 'no_whatsapp', 'properti__nama_properti')
    list_editable = ('status',)

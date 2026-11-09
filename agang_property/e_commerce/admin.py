from django.contrib import admin
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


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ('judul', 'judul_aksen', 'urutan', 'aktif', 'diperbarui')
    list_filter = ('aktif',)
    list_editable = ('urutan', 'aktif')
    search_fields = ('judul', 'judul_aksen', 'tagline', 'deskripsi')


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ('nama_kategori', 'slug')
    search_fields = ('nama_kategori',)
    prepopulated_fields = {'slug': ('nama_kategori',)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('judul', 'kategori', 'status', 'unggulan', 'tanggal_terbit', 'diperbarui')
    list_filter = ('status', 'unggulan', 'kategori')
    search_fields = ('judul', 'ringkasan', 'isi', 'kata_kunci')
    prepopulated_fields = {'slug': ('judul',)}
    readonly_fields = ('dibuat', 'diperbarui')
    fieldsets = (
        ('Konten artikel', {
            'fields': ('judul', 'slug', 'kategori', 'ringkasan', 'jawaban_ringkas', 'poin_utama', 'isi', 'gambar_utama')
        }),
        ('SEO dan GEO', {
            'fields': ('judul_seo', 'deskripsi_seo', 'kata_kunci', 'url_canonical')
        }),
        ('Publikasi', {
            'fields': ('penulis', 'status', 'unggulan', 'tanggal_terbit', 'dibuat', 'diperbarui')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.penulis_id:
            obj.penulis = request.user
        super().save_model(request, obj, form, change)

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'no_telepon', 'tanggal_daftar')
    search_fields = ('user__username', 'user__email', 'no_telepon')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('nama_kategori', 'slug')
    prepopulated_fields = {'slug': ('nama_kategori',)}

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('nama_properti', 'nama_cluster', 'kategori', 'kota', 'harga', 'badge_status', 'tampil_di_home')
    list_filter = ('kategori', 'kota', 'tampil_di_home')
    search_fields = ('nama_properti', 'nama_cluster', 'lokasi_detail', 'kota')
    list_editable = ('tampil_di_home', 'badge_status')

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

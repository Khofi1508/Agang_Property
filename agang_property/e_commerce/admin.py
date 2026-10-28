from django.contrib import admin
from .models import CustomerProfile, Category, Property, Testimonial, UpcomingProject

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
    list_display = ('nama_properti', 'kategori', 'kota', 'harga', 'badge_status', 'tampil_di_home')
    list_filter = ('kategori', 'kota', 'tampil_di_home')
    search_fields = ('nama_properti', 'lokasi_detail', 'kota')
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
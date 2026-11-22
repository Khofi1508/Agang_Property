from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import (
    Article,
    ArticleCategory,
    Category,
    CustomerProfile,
    HeroSlide,
    Property,
    SurveyBooking,
    WebSetting,
    WebsitePage,
)


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = (
            'kategori', 'nama_cluster', 'nama_properti', 'kode_properti',
            'kota', 'lokasi_detail', 'harga', 'harga_coret', 'estimasi_cicilan',
            'badge_status', 'badge_kedua', 'badge_ketiga', 'status_legalitas',
            'status_penjualan', 'gambar_utama', 'deskripsi_singkat',
            'deskripsi_panjang', 'youtube_video_url', 'jumlah_lantai',
            'kamar_tidur', 'kamar_mandi', 'luas_bangunan', 'luas_tanah',
            'arah_hadap', 'daftar_furnitur', 'fasilitas_lingkungan',
            'status_kepemilikan', 'daya_listrik', 'sumber_air', 'pondasi',
            'struktur_dinding', 'kusen_jendela', 'lantai_utama', 'sanitari_km',
            'rangka_atap', 'lebar_jalan_row', 'ulasan_investasi', 'tampil_di_home',
        )
        widgets = {
            'deskripsi_singkat': forms.Textarea(attrs={'rows': 4}),
            'deskripsi_panjang': forms.Textarea(attrs={'rows': 5}),
            'daftar_furnitur': forms.Textarea(attrs={'rows': 3}),
            'fasilitas_lingkungan': forms.Textarea(attrs={'rows': 3}),
            'ulasan_investasi': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'kategori': 'Kategori properti', 'nama_cluster': 'Nama cluster',
            'nama_properti': 'Nama properti', 'kode_properti': 'Kode properti',
            'kota': 'Kota', 'lokasi_detail': 'Lokasi detail', 'harga': 'Harga (Rp)',
            'harga_coret': 'Harga sebelum promo (opsional)',
            'estimasi_cicilan': 'Teks estimasi cicilan', 'badge_status': 'Badge utama',
            'badge_kedua': 'Badge kedua', 'badge_ketiga': 'Badge ketiga',
            'status_legalitas': 'Status unit / legalitas',
            'status_penjualan': 'Status penjualan', 'gambar_utama': 'Foto utama',
            'deskripsi_singkat': 'Deskripsi singkat',
            'deskripsi_panjang': 'Deskripsi lengkap',
            'youtube_video_url': 'Tautan video YouTube',
            'jumlah_lantai': 'Jumlah lantai', 'kamar_tidur': 'Kamar tidur',
            'kamar_mandi': 'Kamar mandi', 'luas_bangunan': 'Luas bangunan (m²)',
            'luas_tanah': 'Luas tanah (m²)', 'arah_hadap': 'Arah hadap',
            'daftar_furnitur': 'Furnitur (pisahkan dengan koma)',
            'fasilitas_lingkungan': 'Fasilitas lingkungan (pisahkan dengan koma)',
            'status_kepemilikan': 'Status kepemilikan', 'daya_listrik': 'Daya listrik',
            'sumber_air': 'Sumber air bersih', 'pondasi': 'Pondasi',
            'struktur_dinding': 'Struktur dinding', 'kusen_jendela': 'Kusen dan jendela',
            'lantai_utama': 'Lantai utama', 'sanitari_km': 'Sanitasi kamar mandi',
            'rangka_atap': 'Rangka dan penutup atap',
            'lebar_jalan_row': 'Lebar jalan (ROW)',
            'ulasan_investasi': 'Ulasan dan nilai investasi',
            'tampil_di_home': 'Tampilkan di halaman beranda',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'admin-input'
        self.fields['tampil_di_home'].widget.attrs['class'] = 'admin-check'


class PropertyCategoryForm(forms.ModelForm):
    slug = forms.SlugField(required=False, help_text='Boleh dikosongkan agar dibuat otomatis.')

    class Meta:
        model = Category
        fields = ('nama_kategori', 'slug')
        labels = {'nama_kategori': 'Nama kategori properti', 'slug': 'Slug kategori'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'admin-input'

    def clean_slug(self):
        slug = self.cleaned_data.get('slug') or slugify(self.cleaned_data.get('nama_kategori', ''))
        base_slug = slug or 'properti'
        slug = base_slug
        suffix = 2
        while Category.objects.filter(slug=slug).exclude(pk=self.instance.pk).exists():
            slug = f'{base_slug}-{suffix}'
            suffix += 1
        return slug


class AdminUserForm(forms.ModelForm):
    no_telepon = forms.CharField(label='Nomor telepon / WhatsApp', required=False, max_length=20)
    alamat = forms.CharField(label='Alamat', required=False, widget=forms.Textarea(attrs={'rows': 3}))
    foto_profil = forms.ImageField(label='Foto profil', required=False)
    password = forms.CharField(
        label='Password baru', required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text='Saat membuat akun wajib diisi; saat mengedit, kosongkan jika tidak ingin mengganti password.',
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active')
        labels = {
            'username': 'Username', 'first_name': 'Nama depan',
            'last_name': 'Nama belakang', 'email': 'Email',
            'is_active': 'Akun aktif',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'admin-input'
        self.fields['is_active'].widget.attrs['class'] = 'admin-check'
        profile = None
        if self.instance and self.instance.pk:
            profile = CustomerProfile.objects.filter(user=self.instance).first()
        if profile:
            self.fields['no_telepon'].initial = profile.no_telepon
            self.fields['alamat'].initial = profile.alamat
            self.fields['foto_profil'].initial = profile.foto_profil
        if not self.instance.pk:
            self.fields['password'].required = True

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password and not self.instance.pk:
            raise forms.ValidationError('Password wajib diisi untuk akun baru.')
        if password:
            try:
                validate_password(password, self.instance if self.instance.pk else None)
            except ValidationError as exc:
                raise forms.ValidationError(exc.messages)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
            profile, _ = CustomerProfile.objects.get_or_create(user=user)
            profile.no_telepon = self.cleaned_data.get('no_telepon', '')
            profile.alamat = self.cleaned_data.get('alamat', '')
            if 'foto_profil' in self.changed_data:
                profile.foto_profil = self.cleaned_data.get('foto_profil') or None
            profile.save()
        return user


class SurveyBookingForm(forms.ModelForm):
    class Meta:
        model = SurveyBooking
        fields = (
            'properti', 'user', 'nama_pemohon', 'no_whatsapp',
            'tanggal_survei', 'sesi_waktu', 'catatan', 'status',
        )
        widgets = {
            'tanggal_survei': forms.DateInput(attrs={'type': 'date'}),
            'catatan': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'properti': 'Properti', 'user': 'Akun pelanggan (opsional)',
            'nama_pemohon': 'Nama pemohon', 'no_whatsapp': 'Nomor WhatsApp',
            'tanggal_survei': 'Tanggal survei', 'sesi_waktu': 'Sesi waktu',
            'catatan': 'Catatan', 'status': 'Status survei',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'admin-input'
        self.fields['user'].required = False
        self.fields['user'].queryset = User.objects.filter(is_superuser=False).order_by('username')


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ('judul', 'slug', 'ringkasan', 'isi', 'gambar_utama', 'kategori', 'status')
        widgets = {
            'ringkasan': forms.Textarea(attrs={'rows': 3}),
            'isi': forms.Textarea(attrs={'rows': 12, 'class': 'admin-input summernote-editor'}),
        }
        labels = {
            'judul': 'Judul artikel',
            'slug': 'Slug (kosongkan untuk dibuat otomatis)',
            'ringkasan': 'Deskripsi artikel',
            'isi': 'Isi artikel',
            'gambar_utama': 'Gambar artikel',
            'kategori': 'Kategori artikel',
            'status': 'Status artikel',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'admin-input'
        self.fields['isi'].widget.attrs['class'] = 'admin-input summernote-editor'
        self.fields['kategori'].required = False
        self.fields['slug'].required = False
        self.fields['gambar_utama'].required = False


class WebsitePageForm(forms.ModelForm):
    class Meta:
        model = WebsitePage
        fields = ('judul', 'slug', 'ringkasan', 'isi', 'status')
        widgets = {
            'ringkasan': forms.Textarea(attrs={'rows': 3}),
            'isi': forms.Textarea(attrs={'rows': 12, 'class': 'admin-input summernote-editor'}),
        }
        labels = {
            'judul': 'Nama halaman',
            'slug': 'Slug (kosongkan untuk dibuat otomatis)',
            'ringkasan': 'Deskripsi singkat (opsional)',
            'isi': 'Isi halaman',
            'status': 'Status halaman',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'admin-input'
        self.fields['isi'].widget.attrs['class'] = 'admin-input summernote-editor'
        self.fields['slug'].required = False


class ArticleCategoryForm(forms.ModelForm):
    class Meta:
        model = ArticleCategory
        fields = ('nama_kategori', 'slug', 'deskripsi')
        widgets = {'deskripsi': forms.Textarea(attrs={'rows': 3})}
        labels = {
            'nama_kategori': 'Nama kategori',
            'slug': 'Slug kategori (opsional)',
            'deskripsi': 'Deskripsi kategori',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'admin-input'
        self.fields['slug'].required = False


class HeroSlideForm(forms.ModelForm):
    class Meta:
        model = HeroSlide
        fields = (
            'tagline',
            'judul',
            'judul_aksen',
            'deskripsi',
            'gambar',
            'label_tombol',
            'urutan',
            'aktif',
        )
        widgets = {'deskripsi': forms.Textarea(attrs={'rows': 4})}
        labels = {
            'tagline': 'Label kecil',
            'judul': 'Judul utama',
            'judul_aksen': 'Judul aksen (baris emas)',
            'deskripsi': 'Deskripsi slide',
            'gambar': 'Gambar background',
            'label_tombol': 'Teks tombol',
            'urutan': 'Urutan tampil',
            'aktif': 'Tampilkan slide ini di halaman utama',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs['class'] = 'admin-check' if name == 'aktif' else 'admin-input'


class WebSettingForm(forms.ModelForm):
    class Meta:
        model = WebSetting
        fields = (
            'nama_website',
            'tagline',
            'logo',
            'favicon',
            'email_kontak',
            'telepon_kontak',
            'whatsapp',
            'alamat',
            'instagram_url',
            'facebook_url',
            'youtube_url',
            'deskripsi_seo',
            'teks_footer',
        )
        widgets = {
            'alamat': forms.Textarea(attrs={'rows': 3}),
            'deskripsi_seo': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'nama_website': 'Nama website',
            'tagline': 'Tagline',
            'logo': 'Logo website',
            'favicon': 'Favicon website',
            'email_kontak': 'Email kontak',
            'telepon_kontak': 'Telepon kontak',
            'whatsapp': 'Nomor WhatsApp',
            'alamat': 'Alamat kantor',
            'instagram_url': 'URL Instagram',
            'facebook_url': 'URL Facebook',
            'youtube_url': 'URL YouTube',
            'deskripsi_seo': 'Deskripsi SEO default',
            'teks_footer': 'Teks hak cipta footer',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'admin-input'
        self.fields['logo'].help_text = 'Logo ini tampil di brand/header, footer, dan panel admin.'
        self.fields['favicon'].help_text = 'Ikon tab browser. Unggah PNG persegi atau ICO.'

from django import forms

from .models import Article, ArticleCategory, HeroSlide, WebSetting, WebsitePage


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
        fields = ('nama_kategori', 'deskripsi')
        widgets = {'deskripsi': forms.Textarea(attrs={'rows': 3})}
        labels = {
            'nama_kategori': 'Nama kategori',
            'deskripsi': 'Deskripsi kategori',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'admin-input'


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

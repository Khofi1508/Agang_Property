from django import forms

from .models import Article, ArticleCategory, HeroSlide


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = (
            'kategori',
            'judul',
            'slug',
            'ringkasan',
            'jawaban_ringkas',
            'poin_utama',
            'isi',
            'gambar_utama',
            'judul_seo',
            'deskripsi_seo',
            'kata_kunci',
            'url_canonical',
            'status',
            'unggulan',
        )
        widgets = {
            'ringkasan': forms.Textarea(attrs={'rows': 3}),
            'jawaban_ringkas': forms.Textarea(attrs={'rows': 3}),
            'poin_utama': forms.Textarea(attrs={'rows': 4}),
            'isi': forms.Textarea(attrs={'rows': 12}),
            'deskripsi_seo': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'kategori': 'Kategori artikel',
            'judul': 'Judul artikel',
            'slug': 'Slug URL (kosongkan untuk dibuat otomatis)',
            'ringkasan': 'Ringkasan artikel',
            'jawaban_ringkas': 'Jawaban singkat untuk pembaca',
            'poin_utama': 'Poin utama (satu per baris)',
            'isi': 'Isi artikel',
            'gambar_utama': 'Gambar utama',
            'judul_seo': 'Judul SEO',
            'deskripsi_seo': 'Deskripsi SEO',
            'kata_kunci': 'Topik terkait (pisahkan dengan koma)',
            'url_canonical': 'URL canonical (opsional)',
            'status': 'Status publikasi',
            'unggulan': 'Tampilkan sebagai artikel unggulan',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'unggulan':
                field.widget.attrs['class'] = 'admin-check'
            else:
                field.widget.attrs['class'] = 'admin-input'
        self.fields['kategori'].required = False
        self.fields['slug'].required = False
        self.fields['gambar_utama'].required = False


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

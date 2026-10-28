from django.urls import path
from . import views

urlpatterns = [
    # Halaman Utama (Home)
    path('', views.home_view, name='home'),

    # Autentikasi (Login Satu Pintu & Registrasi Khusus Pengguna)
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Rute Khusus Admin (Superuser)
    path('dashboard/admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('dashboard/admin/profile/edit/', views.admin_edit_profile_view, name='admin_edit_profile'),

    # Rute Khusus Pengguna (Customer)
    path('dashboard/user/', views.user_dashboard_view, name='user_dashboard'),
    path('dashboard/user/profile/edit/', views.user_edit_profile_view, name='user_edit_profile'),
]
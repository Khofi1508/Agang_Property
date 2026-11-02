from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('catalog/', views.catalog_view, name='catalog'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/admin/', views.admin_dashboard_view, name='admin_dashboard'),
    path('dashboard/admin/profile/edit/', views.admin_edit_profile_view, name='admin_edit_profile'),
    path('dashboard/user/', views.user_dashboard_view, name='user_dashboard'),
    path('dashboard/user/profile/edit/', views.user_edit_profile_view, name='user_edit_profile'),
]
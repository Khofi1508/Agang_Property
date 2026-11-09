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
    path('dashboard/admin/properties/', views.admin_properties_view, name='admin_properties'),
    path('dashboard/admin/articles/', views.admin_articles_view, name='admin_articles'),
    path('dashboard/admin/hero-slides/', views.admin_hero_slides_view, name='admin_hero_slides'),
    path('dashboard/admin/hero-slides/<int:pk>/edit/', views.admin_hero_slide_edit_view, name='admin_hero_slide_edit'),
    path('dashboard/admin/hero-slides/<int:pk>/toggle/', views.admin_hero_slide_toggle_view, name='admin_hero_slide_toggle'),
    path('dashboard/admin/hero-slides/<int:pk>/delete/', views.admin_hero_slide_delete_view, name='admin_hero_slide_delete'),
    path('dashboard/admin/articles/<int:pk>/edit/', views.admin_article_edit_view, name='admin_article_edit'),
    path('dashboard/admin/articles/<int:pk>/delete/', views.admin_article_delete_view, name='admin_article_delete'),
    path('dashboard/user/', views.user_dashboard_view, name='user_dashboard'),
    path('dashboard/user/profile/edit/', views.user_edit_profile_view, name='user_edit_profile'),
    path('artikel/', views.article_list_view, name='article_list'),
    path('artikel/<slug:slug>/', views.article_detail_view, name='article_detail'),
    path('sitemap.xml', views.sitemap_view, name='sitemap'),
    path('robots.txt', views.robots_txt_view, name='robots_txt'),
    path('property/<int:pk>/', views.property_detail_view, name='property_detail'),
]

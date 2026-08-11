from django.urls import path

from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('recuperar-contrasena/', views.recuperar_contrasena_view, name='recuperar_contrasena'),
    path('pregunta-seguridad/', views.pregunta_seguridad_view, name='pregunta_seguridad'),
    path('nueva-contrasena/', views.nueva_contrasena_view, name='nueva_contrasena'),
]

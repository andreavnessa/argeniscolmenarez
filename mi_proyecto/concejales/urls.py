from django.urls import path

from . import views

urlpatterns = [
    # Concejales (Módulo 2)
    path('concejales/', views.lista_concejales_view, name='lista_concejales'),
    path('concejales/nuevo/', views.crear_concejal_view, name='crear_concejal'),
    path('concejales/<uuid:pk>/', views.detalle_concejal_view, name='detalle_concejal'),
    path('concejales/<uuid:pk>/editar/', views.editar_concejal_view, name='editar_concejal'),
    path('concejales/<uuid:pk>/desactivar/', views.desactivar_concejal_view, name='desactivar_concejal'),
    path('concejales/<uuid:pk>/activar/', views.activar_concejal_view, name='activar_concejal'),

    # Personal de Despacho (Módulo 3)
    path('personal-despacho/', views.lista_personal_view, name='lista_personal'),
    path('personal-despacho/nuevo/', views.crear_personal_view, name='crear_personal'),
    path('personal-despacho/<uuid:pk>/editar/', views.editar_personal_view, name='editar_personal'),
    path('personal-despacho/<uuid:pk>/reasignar/', views.reasignar_personal_view, name='reasignar_personal'),
    path('personal-despacho/<uuid:pk>/desactivar/', views.desactivar_personal_view, name='desactivar_personal'),
    path('personal-despacho/<uuid:pk>/activar/', views.activar_personal_view, name='activar_personal'),
]

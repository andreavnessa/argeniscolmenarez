from django.urls import path

from . import views

urlpatterns = [
    # Incidentes y Permisos (Módulo 4)
    path('incidentes/', views.lista_incidentes_view, name='lista_incidentes'),
    path('incidentes/nuevo/', views.crear_incidente_view, name='crear_incidente'),
    path('incidentes/<uuid:pk>/', views.detalle_incidente_view, name='detalle_incidente'),
    path('incidentes/<uuid:pk>/editar/', views.editar_incidente_view, name='editar_incidente'),
    path('incidentes/<uuid:pk>/estado/', views.cambiar_estado_incidente_view, name='cambiar_estado_incidente'),
    path('incidentes/<uuid:pk>/eliminar/', views.eliminar_incidente_view, name='eliminar_incidente'),
]

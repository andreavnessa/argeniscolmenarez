from django.urls import path

from . import views

urlpatterns = [
    # Asistencia (RF-04): registro de entrada y salida
    path('asistencia/', views.lista_asistencia_view, name='lista_asistencia'),
    path('asistencia/entrada/', views.marcar_entrada_view, name='marcar_entrada'),
    path('asistencia/salida/', views.marcar_salida_view, name='marcar_salida'),
    path('asistencia/nueva/', views.crear_asistencia_view, name='crear_asistencia'),
]

from django.urls import path

from . import views

urlpatterns = [
    # Reportes (RF-09): en pantalla y descargables
    path('reportes/', views.panel_reporte_view, name='reportes'),
    path('reportes/asistencia/', views.reporte_asistencia_view, name='reporte_asistencia'),
    path('reportes/asistencia/csv/', views.reporte_asistencia_csv_view, name='reporte_asistencia_csv'),
    path('reportes/incidencias/', views.reporte_incidencias_view, name='reporte_incidencias'),
    path('reportes/incidencias/csv/', views.reporte_incidencias_csv_view, name='reporte_incidencias_csv'),
    path('reportes/concejales/', views.reporte_concejales_view, name='reporte_concejales'),
    path('reportes/concejales/csv/', views.reporte_concejales_csv_view, name='reporte_concejales_csv'),
]

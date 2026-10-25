from django.contrib import admin

from .models import Incidente


@admin.register(Incidente)
class IncidenteAdmin(admin.ModelAdmin):
    """Panel de administración para el modelo de incidentes y permisos."""

    list_display = (
        'get_afectado_nombre',
        'get_afectado_tipo_display',
        'get_tipo_permiso_display',
        'fecha_inicio',
        'fecha_fin',
        'get_duracion_dias',
        'get_estado_display',
        'registrado_por',
        'created_at',
    )
    list_filter = ('estado', 'tipo_permiso', 'afectado_tipo')
    search_fields = (
        'concejal__nombres',
        'concejal__apellidos',
        'personal_despacho__nombres',
        'personal_despacho__apellidos',
        'motivo',
    )
    readonly_fields = ('id', 'registrado_por', 'created_at', 'updated_at')
    list_select_related = (
        'concejal',
        'personal_despacho',
        'personal_despacho__concejal',
        'registrado_por',
    )
    list_per_page = 25
    fieldsets = (
        ('Afectado', {
            'fields': ('afectado_tipo', 'concejal', 'personal_despacho'),
        }),
        ('Detalles del permiso', {
            'fields': ('tipo_permiso', 'motivo', 'adjunto', 'fecha_inicio', 'fecha_fin'),
        }),
        ('Gestión', {
            'fields': ('estado', 'registrado_por'),
        }),
        ('Auditoría', {
            'fields': ('id', 'created_at', 'updated_at'),
        }),
    )

    def get_afectado_nombre(self, obj):
        return obj.get_afectado_nombre()
    get_afectado_nombre.short_description = 'Afectado'

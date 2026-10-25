from django.contrib import admin

from .models import Asistencia


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    """Panel de administración para el registro de asistencia."""

    list_display = (
        'get_afectado_nombre',
        'get_afectado_tipo_display',
        'fecha',
        'hora_entrada',
        'hora_salida',
        'get_duracion_horas',
        'registrado_por',
        'created_at',
    )
    list_filter = ('afectado_tipo', 'fecha')
    search_fields = (
        'concejal__nombres',
        'concejal__apellidos',
        'personal_despacho__nombres',
        'personal_despacho__apellidos',
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
        ('Registro', {
            'fields': ('fecha', 'hora_entrada', 'hora_salida'),
        }),
        ('Auditoría', {
            'fields': ('id', 'registrado_por', 'created_at', 'updated_at'),
        }),
    )

    def get_afectado_nombre(self, obj):
        return obj.get_afectado_nombre()
    get_afectado_nombre.short_description = 'Afectado'

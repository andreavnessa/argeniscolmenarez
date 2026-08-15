from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Configuración del panel de administración para Usuario."""

    # Campos para la lista de usuarios
    list_display = (
        'email',
        'get_full_name',
        'is_active',
        'is_staff',
        'fecha_registro',
        'ultimo_acceso',
        'intentos_fallidos',
    )
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'pregunta_seguridad', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'telefono')
    ordering = ('-date_joined',)

    # Campos para el formulario de creación
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'first_name',
                'last_name',
                'password1',
                'password2',
            ),
        }),
        ('Información personal', {
            'fields': ('telefono', 'fecha_nacimiento'),
        }),
        ('Seguridad', {
            'fields': ('pregunta_seguridad', 'respuesta_seguridad'),
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
    )

    # Campos para el formulario de edición
    fieldsets = (
        (None, {
            'fields': ('email', 'password'),
        }),
        ('Información personal', {
            'fields': ('first_name', 'last_name', 'telefono', 'fecha_nacimiento'),
        }),
        ('Seguridad', {
            'fields': ('pregunta_seguridad', 'respuesta_seguridad'),
            'description': 'La respuesta de seguridad se almacena en texto plano. Se recomienda usar una respuesta difícil de adivinar.',
        }),
        ('Estado de la cuenta', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'intentos_fallidos',
                'bloqueado_hasta',
                'ultimo_acceso',
            ),
        }),
        ('Fechas', {
            'fields': ('last_login', 'date_joined'),
        }),
        ('Grupos y permisos', {
            'fields': ('groups', 'user_permissions'),
        }),
    )

    readonly_fields = ('last_login', 'date_joined', 'fecha_registro', 'ultimo_acceso')

    def get_readonly_fields(self, request, obj=None):
        """Hacer algunos campos de solo lectura en edición."""
        readonly = list(self.readonly_fields)
        if obj:  # En edición
            readonly.extend(['intentos_fallidos', 'bloqueado_hasta'])
        return readonly
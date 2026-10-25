from django.contrib import admin

from .models import Concejal, PersonalDespacho


class PersonalDespachoInline(admin.TabularInline):
    model = PersonalDespacho
    extra = 0
    fields = ('cedula', 'nombres', 'apellidos', 'cargo', 'estado')
    readonly_fields = ('cedula', 'nombres', 'apellidos', 'cargo', 'estado')
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Concejal)
class ConcejalAdmin(admin.ModelAdmin):
    list_display = ('get_nombre_completo', 'cedula', 'comision_asignada', 'estado', 'get_conteo_personal_activo', 'usuario')
    list_filter = ('estado', 'comision_asignada')
    search_fields = ('nombres', 'apellidos', 'cedula', 'correo')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [PersonalDespachoInline]

    def get_conteo_personal_activo(self, obj):
        return obj.get_conteo_personal_activo()
    get_conteo_personal_activo.short_description = 'Personal activo'


@admin.register(PersonalDespacho)
class PersonalDespachoAdmin(admin.ModelAdmin):
    list_display = ('get_nombre_completo', 'cedula', 'cargo', 'concejal', 'estado', 'usuario')
    list_filter = ('estado', 'cargo', 'concejal')
    search_fields = ('nombres', 'apellidos', 'cedula', 'correo')
    readonly_fields = ('id', 'created_at', 'updated_at')

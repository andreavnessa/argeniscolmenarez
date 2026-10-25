import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Incidente(models.Model):
    """Modelo que representa un incidente / permiso de un concejal o personal.

    Ejemplos: permisos por enfermedad, situaciones personales o familiares,
    trámites institucionales, vacaciones, etc.
    """

    # Tipo de persona afectada
    AFECTADO_CONCEJAL = 'concejal'
    AFECTADO_PERSONAL = 'personal'
    AFECTADO_TIPOS = [
        (AFECTADO_CONCEJAL, 'Concejal'),
        (AFECTADO_PERSONAL, 'Personal de Despacho'),
    ]

    # Tipos de permiso / incidente
    PERMISO_ENFERMEDAD = 'enfermedad'
    PERMISO_REPOSO = 'reposo'
    PERMISO_SITUACION_PERSONAL = 'situacion_personal'
    PERMISO_SITUACION_FAMILIAR = 'situacion_familiar'
    PERMISO_VACACIONES = 'vacaciones'
    PERMISO_TRAMITE = 'tramite_institucional'
    PERMISO_COMISION_SERVICIO = 'comision_servicio'
    PERMISO_OTRO = 'otro'
    TIPOS_PERMISO = [
        (PERMISO_ENFERMEDAD, 'Permiso médico / Enfermedad'),
        (PERMISO_REPOSO, 'Reposo médico'),
        (PERMISO_SITUACION_PERSONAL, 'Situación personal'),
        (PERMISO_SITUACION_FAMILIAR, 'Situación familiar'),
        (PERMISO_VACACIONES, 'Vacaciones'),
        (PERMISO_TRAMITE, 'Trámite institucional'),
        (PERMISO_COMISION_SERVICIO, 'Comisión de servicio'),
        (PERMISO_OTRO, 'Otro'),
    ]

    # Estados del incidente
    ESTADO_PENDIENTE = 'pendiente'
    ESTADO_APROBADO = 'aprobado'
    ESTADO_RECHAZADO = 'rechazado'
    ESTADO_FINALIZADO = 'finalizado'
    ESTADOS = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_APROBADO, 'Aprobado'),
        (ESTADO_RECHAZADO, 'Rechazado'),
        (ESTADO_FINALIZADO, 'Finalizado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    afectado_tipo = models.CharField(
        'Tipo de afectado',
        max_length=10,
        choices=AFECTADO_TIPOS,
        help_text='¿El incidente es de un concejal o de un personal de despacho?',
    )
    concejal = models.ForeignKey(
        'concejales.Concejal',
        on_delete=models.CASCADE,
        related_name='incidentes',
        verbose_name='Concejal',
        null=True,
        blank=True,
        help_text='Solo si el afectado es un concejal.',
    )
    personal_despacho = models.ForeignKey(
        'concejales.PersonalDespacho',
        on_delete=models.CASCADE,
        related_name='incidentes',
        verbose_name='Personal de Despacho',
        null=True,
        blank=True,
        help_text='Solo si el afectado es personal de despacho.',
    )
    tipo_permiso = models.CharField(
        'Tipo de permiso / incidente',
        max_length=30,
        choices=TIPOS_PERMISO,
    )
    motivo = models.TextField(
        'Motivo / Descripción',
        help_text='Describa brevemente el motivo del permiso o incidente.',
    )
    adjunto = models.FileField(
        'Documento adjunto (permiso médico / reposo)',
        upload_to='incidentes/adjuntos/',
        null=True,
        blank=True,
        help_text='Cargue el permiso médico, reposo o documento de respaldo.',
    )
    fecha_inicio = models.DateField('Fecha de inicio')
    fecha_fin = models.DateField(
        'Fecha de fin',
        null=True,
        blank=True,
        help_text='Dejar vacío si es por tiempo indefinido.',
    )
    estado = models.CharField(
        'Estado',
        max_length=15,
        choices=ESTADOS,
        default=ESTADO_PENDIENTE,
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidentes_registrados',
        verbose_name='Registrado por',
    )
    created_at = models.DateTimeField('Fecha de registro', auto_now_add=True)
    updated_at = models.DateTimeField('Fecha de actualización', auto_now=True)

    class Meta:
        verbose_name = 'Incidente / Permiso'
        verbose_name_plural = 'Incidentes y Permisos'
        ordering = ['-fecha_inicio', '-created_at']

    def __str__(self):
        return f'{self.get_afectado_display()} - {self.get_tipo_permiso_display()} ({self.fecha_inicio})'

    def get_afectado(self):
        """Devuelve el objeto afectado (Concejal o PersonalDespacho)."""
        if self.afectado_tipo == self.AFECTADO_CONCEJAL:
            return self.concejal
        return self.personal_despacho

    def get_afectado_nombre(self):
        afectado = self.get_afectado()
        return afectado.get_nombre_completo() if afectado else '—'

    def get_duracion_dias(self):
        """Retorna la duración en días del permiso."""
        if self.fecha_fin and self.fecha_inicio:
            return max((self.fecha_fin - self.fecha_inicio).days + 1, 0)
        return None

    def clean(self):
        super().clean()
        # Debe existir un afectado (concejal o personal) según el tipo
        if self.afectado_tipo == self.AFECTADO_CONCEJAL and not self.concejal_id:
            raise ValidationError({'concejal': 'Debe seleccionar el concejal afectado.'})
        if self.afectado_tipo == self.AFECTADO_PERSONAL and not self.personal_despacho_id:
            raise ValidationError({'personal_despacho': 'Debe seleccionar el personal de despacho afectado.'})

        # Validar fechas
        if self.fecha_fin and self.fecha_inicio and self.fecha_fin < self.fecha_inicio:
            raise ValidationError({
                'fecha_fin': 'La fecha de fin no puede ser anterior a la fecha de inicio.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

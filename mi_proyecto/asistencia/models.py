import uuid

from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Asistencia(models.Model):
    """Registro de entrada y salida (asistencia) de concejales y personal."""

    AFECTADO_CONCEJAL = 'concejal'
    AFECTADO_PERSONAL = 'personal'
    AFECTADO_TIPOS = [
        (AFECTADO_CONCEJAL, 'Concejal'),
        (AFECTADO_PERSONAL, 'Personal de Despacho'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    afectado_tipo = models.CharField(
        'Tipo de afectado',
        max_length=10,
        choices=AFECTADO_TIPOS,
        help_text='¿La asistencia es de un concejal o de un personal de despacho?',
    )
    concejal = models.ForeignKey(
        'concejales.Concejal',
        on_delete=models.CASCADE,
        related_name='asistencias',
        verbose_name='Concejal',
        null=True,
        blank=True,
        help_text='Solo si la asistencia es de un concejal.',
    )
    personal_despacho = models.ForeignKey(
        'concejales.PersonalDespacho',
        on_delete=models.CASCADE,
        related_name='asistencias',
        verbose_name='Personal de Despacho',
        null=True,
        blank=True,
        help_text='Solo si la asistencia es de personal de despacho.',
    )
    fecha = models.DateField('Fecha')
    hora_entrada = models.TimeField('Hora de entrada', null=True, blank=True)
    hora_salida = models.TimeField('Hora de salida', null=True, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asistencias_registradas',
        verbose_name='Registrado por',
    )
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Fecha de actualización', auto_now=True)

    class Meta:
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'
        ordering = ['-fecha', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['fecha', 'concejal'],
                condition=Q(concejal__isnull=False),
                name='uniq_asistencia_concejal_por_dia',
            ),
            models.UniqueConstraint(
                fields=['fecha', 'personal_despacho'],
                condition=Q(personal_despacho__isnull=False),
                name='uniq_asistencia_personal_por_dia',
            ),
        ]

    def __str__(self):
        return f'{self.get_afectado_nombre()} - {self.fecha}'

    def get_afectado(self):
        """Devuelve el objeto afectado (Concejal o PersonalDespacho)."""
        if self.afectado_tipo == self.AFECTADO_CONCEJAL:
            return self.concejal
        return self.personal_despacho

    def get_afectado_nombre(self):
        afectado = self.get_afectado()
        return afectado.get_nombre_completo() if afectado else '—'

    def get_duracion(self):
        """Retorna la duración trabajada (timedelta) o None."""
        if self.hora_entrada and self.hora_salida:
            e = datetime.combine(self.fecha, self.hora_entrada)
            s = datetime.combine(self.fecha, self.hora_salida)
            duracion = s - e
            return duracion if duracion.total_seconds() >= 0 else None
        return None

    def get_duracion_horas(self):
        """Retorna la duración formateada, ej: '8h 30m'."""
        duracion = self.get_duracion()
        if duracion is None:
            return '—'
        total_min = int(duracion.total_seconds() // 60)
        h, m = divmod(total_min, 60)
        return f'{h}h {m:02d}m'

    def clean(self):
        super().clean()
        if self.afectado_tipo == self.AFECTADO_CONCEJAL and not self.concejal_id:
            raise ValidationError({'concejal': 'Debe seleccionar el concejal.'})
        if self.afectado_tipo == self.AFECTADO_PERSONAL and not self.personal_despacho_id:
            raise ValidationError({'personal_despacho': 'Debe seleccionar el personal de despacho.'})
        if self.hora_entrada and self.hora_salida and self.hora_salida < self.hora_entrada:
            raise ValidationError({
                'hora_salida': 'La hora de salida no puede ser anterior a la hora de entrada.'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

import uuid

from django.core.exceptions import ValidationError
from django.db import models


class Concejal(models.Model):
    """Modelo que representa a un concejal del municipio."""

    ESTADO_ACTIVO = 'Activo'
    ESTADO_INACTIVO = 'Inactivo'
    ESTADOS = [
        (ESTADO_ACTIVO, 'Activo'),
        (ESTADO_INACTIVO, 'Inactivo'),
    ]

    LIMITE_PERSONAL_DESPACHO = 8

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cedula = models.CharField('Cédula', max_length=20, unique=True)
    nombres = models.CharField('Nombres', max_length=100)
    apellidos = models.CharField('Apellidos', max_length=100)
    foto = models.ImageField(
        'Foto',
        upload_to='concejales/fotos/',
        blank=True,
        null=True,
    )
    telefono = models.CharField('Teléfono', max_length=20)
    correo = models.EmailField('Correo electrónico', unique=True)
    direccion = models.TextField('Dirección')
    comision_asignada = models.CharField(
        'Comisión asignada',
        max_length=150,
        help_text='Ej: Comisión de Servicios Públicos, Comisión de Salud',
    )
    fecha_inicio_gestion = models.DateField('Fecha de inicio de gestión')
    horario_atencion = models.CharField(
        'Horario de atención',
        max_length=100,
        help_text='Ej: Lunes a Viernes 8:00 AM - 2:00 PM',
    )
    estado = models.CharField(
        'Estado',
        max_length=10,
        choices=ESTADOS,
        default=ESTADO_ACTIVO,
    )
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Fecha de actualización', auto_now=True)

    class Meta:
        verbose_name = 'Concejal'
        verbose_name_plural = 'Concejales'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f'{self.nombres} {self.apellidos}'

    def get_nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'

    def get_iniciales(self):
        """Retorna las iniciales para el avatar."""
        return f'{self.nombres[0]}{self.apellidos[0]}'.upper()

    def get_personal_activo(self):
        """Retorna el personal de despacho activo."""
        return self.personal_despacho.filter(estado=PersonalDespacho.ESTADO_ACTIVO)

    def get_conteo_personal_activo(self):
        """Retorna el número de personal activo en el despacho."""
        return self.get_personal_activo().count()

    def get_conteo_personal_total(self):
        """Retorna el número total de personal en el despacho."""
        return self.personal_despacho.count()

    def puede_agregar_personal(self):
        """Verifica si el concejal puede agregar más personal a su despacho."""
        return self.get_conteo_personal_activo() < self.LIMITE_PERSONAL_DESPACHO

    def get_personal_restante(self):
        """Retorna cuántas personas más puede agregar al despacho."""
        restante = self.LIMITE_PERSONAL_DESPACHO - self.get_conteo_personal_activo()
        return max(restante, 0)


class PersonalDespacho(models.Model):
    """Modelo que representa al personal de despacho de un concejal."""

    ESTADO_ACTIVO = 'Activo'
    ESTADO_INACTIVO = 'Inactivo'
    ESTADOS = [
        (ESTADO_ACTIVO, 'Activo'),
        (ESTADO_INACTIVO, 'Inactivo'),
    ]

    CARGOS = [
        ('Asistente Ejecutivo', 'Asistente Ejecutivo'),
        ('Promotor de Campo', 'Promotor de Campo'),
        ('Asesor Jurídico', 'Asesor Jurídico'),
        ('Atención Ciudadana', 'Atención Ciudadana'),
        ('Prensa', 'Prensa'),
        ('Secretario(a)', 'Secretario(a)'),
        ('Chofer', 'Chofer'),
        ('Otro', 'Otro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    concejal = models.ForeignKey(
        Concejal,
        on_delete=models.CASCADE,
        related_name='personal_despacho',
        verbose_name='Concejal',
    )
    cedula = models.CharField('Cédula', max_length=20, unique=True)
    nombres = models.CharField('Nombres', max_length=100)
    apellidos = models.CharField('Apellidos', max_length=100)
    foto = models.ImageField(
        'Foto',
        upload_to='personal_despacho/fotos/',
        blank=True,
        null=True,
    )
    telefono = models.CharField('Teléfono', max_length=20)
    correo = models.EmailField('Correo electrónico')
    cargo = models.CharField('Cargo', max_length=50, choices=CARGOS)
    fecha_ingreso = models.DateField('Fecha de ingreso')
    horario_trabajo = models.CharField(
        'Horario de trabajo',
        max_length=100,
        help_text='Ej: Lunes a Viernes 8:00 AM - 4:00 PM',
    )
    estado = models.CharField(
        'Estado',
        max_length=10,
        choices=ESTADOS,
        default=ESTADO_ACTIVO,
    )
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Fecha de actualización', auto_now=True)

    class Meta:
        verbose_name = 'Personal de Despacho'
        verbose_name_plural = 'Personal de Despacho'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f'{self.nombres} {self.apellidos} ({self.cargo})'

    def get_nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'

    def get_iniciales(self):
        """Retorna las iniciales para el avatar."""
        return f'{self.nombres[0]}{self.apellidos[0]}'.upper()

    def clean(self):
        """Valida la regla de negocio del límite de personal por despacho."""
        super().clean()
        if self.concejal_id:
            concejal = self.concejal
            # Excluir el registro actual al contar (para ediciones)
            personal_activo = concejal.get_personal_activo().exclude(pk=self.pk).count()
            if personal_activo >= Concejal.LIMITE_PERSONAL_DESPACHO:
                raise ValidationError(
                    f'El concejal {concejal.get_nombre_completo()} ya tiene '
                    f'{Concejal.LIMITE_PERSONAL_DESPACHO} personas activas en su despacho. '
                    'No puede agregar más personal.'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
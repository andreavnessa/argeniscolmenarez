from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UsuarioManager(BaseUserManager):
    """Manager personalizado para el modelo Usuario."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    """Modelo de usuario personalizado con preguntas de seguridad."""

    # Eliminar el campo username, usar email como identificador
    username = None
    email = models.EmailField('Correo electrónico', unique=True)

    # Preguntas de seguridad
    PREGUNTAS_SEGURIDAD = [
        ('mascota', '¿Cuál es el nombre de tu primera mascota?'),
        ('madre', '¿Cuál es el apellido de soltera de tu madre?'),
        ('ciudad', '¿En qué ciudad naciste?'),
        ('comida', '¿Cuál es tu comida favorita?'),
        ('escuela', '¿Cuál es el nombre de tu primera escuela?'),
        ('pelicula', '¿Cuál es tu película favorita?'),
        ('libro', '¿Cuál es tu libro favorito?'),
        ('deporte', '¿Cuál es tu deporte favorito?'),
        ('color', '¿Cuál es tu color favorito?'),
        ('pais', '¿Cuál es tu país favorito?'),
    ]

    pregunta_seguridad = models.CharField(
        'Pregunta de seguridad',
        max_length=50,
        choices=PREGUNTAS_SEGURIDAD,
        blank=True,
        null=True,
    )
    respuesta_seguridad = models.CharField(
        'Respuesta de seguridad',
        max_length=200,
        blank=True,
        null=True,
        help_text='Se almacena en texto plano. Se recomienda usar una respuesta que no sea fácil de adivinar.',
    )

    # Campos adicionales
    telefono = models.CharField('Teléfono', max_length=20, blank=True, null=True)
    fecha_nacimiento = models.DateField('Fecha de nacimiento', blank=True, null=True)
    fecha_registro = models.DateTimeField('Fecha de registro', auto_now_add=True)
    ultimo_acceso = models.DateTimeField('Último acceso', blank=True, null=True)
    intentos_fallidos = models.PositiveIntegerField('Intentos fallidos', default=0)
    bloqueado_hasta = models.DateTimeField('Bloqueado hasta', blank=True, null=True)

    # Configuración
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UsuarioManager()

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.get_full_name()} ({self.email})'

    def get_full_name(self):
        """Retorna el nombre completo del usuario."""
        if self.first_name and self.last_name:
            return f'{self.first_name} {self.last_name}'
        return self.email

    def get_initials(self):
        """Retorna las iniciales del usuario para el avatar."""
        if self.first_name and self.last_name:
            return f'{self.first_name[0]}{self.last_name[0]}'.upper()
        return self.email[0:2].upper()

    def registrar_intento_fallido(self):
        """Registra un intento fallido de login."""
        self.intentos_fallidos += 1
        if self.intentos_fallidos >= 5:
            self.bloqueado_hasta = timezone.now() + timezone.timedelta(minutes=15)
            self.intentos_fallidos = 0
        self.save(update_fields=['intentos_fallidos', 'bloqueado_hasta'])

    def reset_intentos_fallidos(self):
        """Reinicia los intentos fallidos tras un login exitoso."""
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None
        self.ultimo_acceso = timezone.now()
        self.save(update_fields=['intentos_fallidos', 'bloqueado_hasta', 'ultimo_acceso'])

    def esta_bloqueado(self):
        """Verifica si el usuario está bloqueado."""
        if self.bloqueado_hasta and self.bloqueado_hasta > timezone.now():
            return True
        return False
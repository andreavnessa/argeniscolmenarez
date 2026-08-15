from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Usuario


class LoginForm(forms.Form):
    """Formulario de inicio de sesión con correo y contraseña."""
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ejemplo@correo.com',
            'autocomplete': 'email',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña',
            'autocomplete': 'current-password',
        })
    )
    remember_me = forms.BooleanField(
        label='Recordarme',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            try:
                usuario = Usuario.objects.get(email__iexact=email)
            except Usuario.DoesNotExist:
                raise ValidationError('Las credenciales ingresadas no son válidas.')

            if usuario.esta_bloqueado():
                tiempo_restante = usuario.bloqueado_hasta - timezone.now()
                minutos = int(tiempo_restante.total_seconds() // 60)
                raise ValidationError(
                    f'Cuenta bloqueada temporalmente. Intente nuevamente en {minutos} minutos.'
                )

            if not usuario.is_active:
                raise ValidationError('Esta cuenta está desactivada. Contacte al administrador.')

            if not usuario.check_password(password):
                usuario.registrar_intento_fallido()
                if usuario.esta_bloqueado():
                    raise ValidationError(
                        'Cuenta bloqueada por 15 minutos por múltiples intentos fallidos.'
                    )
                intentos_restantes = max(5 - usuario.intentos_fallidos, 0)
                raise ValidationError(
                    f'Contraseña incorrecta. Le quedan {intentos_restantes} intentos.'
                )

            # Credenciales válidas
            self.usuario = usuario

        return cleaned_data

    def get_user(self):
        """Retorna el usuario autenticado."""
        return getattr(self, 'usuario', None)


class RecuperarContrasenaForm(forms.Form):
    """Formulario para iniciar la recuperación de contraseña."""
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su correo electrónico',
            'autocomplete': 'email',
            'autofocus': True,
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            usuario = Usuario.objects.get(email__iexact=email)
        except Usuario.DoesNotExist:
            raise ValidationError('No existe una cuenta con este correo electrónico.')
        self.usuario = usuario
        return email

    def get_usuario(self):
        return getattr(self, 'usuario', None)


class PreguntaSeguridadForm(forms.Form):
    """Formulario para responder la pregunta de seguridad."""
    respuesta = forms.CharField(
        label='Respuesta de seguridad',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su respuesta',
            'autocomplete': 'off',
            'autofocus': True,
        })
    )

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)

    def clean_respuesta(self):
        respuesta = self.cleaned_data.get('respuesta', '').strip().lower()
        if not self.usuario:
            raise ValidationError('Usuario no válido.')

        if not self.usuario.respuesta_seguridad:
            raise ValidationError(
                'Este usuario no tiene configurada una pregunta de seguridad. '
                'Contacte al administrador.'
            )

        respuesta_guardada = self.usuario.respuesta_seguridad.lower()
        if respuesta != respuesta_guardada:
            raise ValidationError('La respuesta de seguridad es incorrecta.')

        return respuesta


class NuevaContrasenaForm(forms.Form):
    """Formulario para establecer una nueva contraseña."""
    nueva_contrasena = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese la nueva contraseña',
            'autocomplete': 'new-password',
        })
    )
    confirmar_contrasena = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repita la nueva contraseña',
            'autocomplete': 'new-password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        nueva = cleaned_data.get('nueva_contrasena')
        confirmar = cleaned_data.get('confirmar_contrasena')

        if nueva and confirmar and nueva != confirmar:
            raise ValidationError('Las contraseñas no coinciden.')

        if nueva and len(nueva) < 8:
            raise ValidationError('La contraseña debe tener al menos 8 caracteres.')

        return cleaned_data
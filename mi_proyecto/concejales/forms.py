import re

from django import forms
from django.core.exceptions import ValidationError

from .models import Concejal, PersonalDespacho


def validar_cedula(value):
    """Valida que la cédula solo contenga números (formato venezolano)."""
    if not re.match(r'^[0-9]{6,10}$', value):
        raise ValidationError(
            'La cédula debe contener solo números (entre 6 y 10 dígitos).'
        )


def validar_telefono(value):
    """Valida el formato de teléfono venezolano: 0412-1234567 o 04121234567."""
    # Permitir formatos: 0412-1234567, 04121234567, +58 412-1234567
    patron = r'^(\+?\d{1,3}[\s-]?)?\d{3}[\s-]?\d{7}$'
    if not re.match(patron, value):
        raise ValidationError(
            'El teléfono debe tener un formato válido. Ej: 0412-1234567'
        )


class ConcejalForm(forms.ModelForm):
    """Formulario para crear y editar concejales."""

    class Meta:
        model = Concejal
        fields = [
            'cedula',
            'nombres',
            'apellidos',
            'foto',
            'telefono',
            'correo',
            'direccion',
            'comision_asignada',
            'fecha_inicio_gestion',
            'horario_atencion',
            'estado',
        ]
        widgets = {
            'cedula': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 12345678',
            }),
            'nombres': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese los nombres',
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese los apellidos',
            }),
            'foto': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 0412-1234567',
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'ejemplo@correo.com',
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ingrese la dirección',
            }),
            'comision_asignada': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Comisión de Servicios Públicos',
            }),
            'fecha_inicio_gestion': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'horario_atencion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Lunes a Viernes 8:00 AM - 2:00 PM',
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select',
            }),
        }

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula', '').strip()
        validar_cedula(cedula)
        # Verificar unicidad (excluyendo el registro actual en edición)
        qs = Concejal.objects.filter(cedula=cedula)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Ya existe un concejal registrado con esta cédula.')
        return cedula

    def clean_correo(self):
        correo = self.cleaned_data.get('correo', '').strip().lower()
        qs = Concejal.objects.filter(correo__iexact=correo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Ya existe un concejal registrado con este correo.')
        return correo

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        validar_telefono(telefono)
        return telefono


class PersonalDespachoForm(forms.ModelForm):
    """Formulario para crear y editar personal de despacho."""

    class Meta:
        model = PersonalDespacho
        fields = [
            'concejal',
            'cedula',
            'nombres',
            'apellidos',
            'foto',
            'telefono',
            'correo',
            'cargo',
            'fecha_ingreso',
            'horario_trabajo',
            'estado',
        ]
        widgets = {
            'concejal': forms.Select(attrs={
                'class': 'form-select',
            }),
            'cedula': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 12345678',
            }),
            'nombres': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese los nombres',
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese los apellidos',
            }),
            'foto': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 0412-1234567',
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'ejemplo@correo.com',
            }),
            'cargo': forms.Select(attrs={
                'class': 'form-select',
            }),
            'fecha_ingreso': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'horario_trabajo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Lunes a Viernes 8:00 AM - 4:00 PM',
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select',
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Limitar el selector de concejales a los activos
        self.fields['concejal'].queryset = Concejal.objects.filter(
            estado=Concejal.ESTADO_ACTIVO
        ).order_by('apellidos', 'nombres')

        # Si el usuario es un concejal, restringir a su propio despacho
        if user is not None and user.is_authenticated and user.es_concejal:
            concejal = getattr(user, 'concejal_perfil', None)
            if concejal:
                self.fields['concejal'].queryset = Concejal.objects.filter(pk=concejal.pk)
                self.fields['concejal'].initial = concejal.pk
                self.fields['concejal'].disabled = True
                self.fields['concejal'].help_text = (
                    'Solo puede registrar personal en su propio despacho.'
                )

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula', '').strip()
        validar_cedula(cedula)
        qs = PersonalDespacho.objects.filter(cedula=cedula)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Ya existe un miembro del personal con esta cédula.')
        return cedula

    def clean_correo(self):
        correo = self.cleaned_data.get('correo', '').strip().lower()
        qs = PersonalDespacho.objects.filter(correo__iexact=correo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Ya existe un miembro del personal con este correo.')
        return correo

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        validar_telefono(telefono)
        return telefono

    def clean(self):
        cleaned_data = super().clean()
        concejal = cleaned_data.get('concejal')
        estado = cleaned_data.get('estado')

        # Validar límite de personal activo solo si el nuevo registro está activo
        if concejal and estado == PersonalDespacho.ESTADO_ACTIVO:
            personal_activo = concejal.get_personal_activo().exclude(pk=self.instance.pk).count()
            if personal_activo >= Concejal.LIMITE_PERSONAL_DESPACHO:
                raise ValidationError(
                    f'El concejal {concejal.get_nombre_completo()} ya tiene '
                    f'{Concejal.LIMITE_PERSONAL_DESPACHO} personas activas en su despacho. '
                    'Debe desactivar a alguien antes de agregar más personal.'
                )
        return cleaned_data


class ReasignarPersonalForm(forms.ModelForm):
    """Formulario para reasignar personal a otro concejal."""

    class Meta:
        model = PersonalDespacho
        fields = ['concejal']
        widgets = {
            'concejal': forms.Select(attrs={
                'class': 'form-select',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['concejal'].queryset = Concejal.objects.filter(
            estado=Concejal.ESTADO_ACTIVO
        ).order_by('apellidos', 'nombres')
        self.fields['concejal'].label = 'Nuevo concejal'

    def clean_concejal(self):
        nuevo_concejal = self.cleaned_data.get('concejal')
        if self.instance.pk and nuevo_concejal:
            if nuevo_concejal.pk == self.instance.concejal_id:
                raise ValidationError('El personal ya está asignado a este concejal.')

            # Validar límite en el concejal destino
            if self.instance.estado == PersonalDespacho.ESTADO_ACTIVO:
                personal_activo = nuevo_concejal.get_personal_activo().exclude(
                    pk=self.instance.pk
                ).count()
                if personal_activo >= Concejal.LIMITE_PERSONAL_DESPACHO:
                    raise ValidationError(
                        f'El concejal {nuevo_concejal.get_nombre_completo()} ya tiene '
                        f'{Concejal.LIMITE_PERSONAL_DESPACHO} personas activas en su despacho. '
                        'No puede reasignar personal a este concejal.'
                    )
        return nuevo_concejal
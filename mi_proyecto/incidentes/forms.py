from django import forms

from concejales.models import Concejal, PersonalDespacho

from .models import Incidente


class IncidenteForm(forms.ModelForm):
    """Formulario para crear y editar incidentes / permisos."""

    class Meta:
        model = Incidente
        fields = [
            'afectado_tipo',
            'concejal',
            'personal_despacho',
            'tipo_permiso',
            'motivo',
            'adjunto',
            'fecha_inicio',
            'fecha_fin',
            'estado',
        ]
        widgets = {
            'afectado_tipo': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_afectado_tipo',
            }),
            'concejal': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_concejal',
            }),
            'personal_despacho': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_personal_despacho',
            }),
            'tipo_permiso': forms.Select(attrs={
                'class': 'form-select',
            }),
            'motivo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describa el motivo del permiso o incidente...',
            }),
            'adjunto': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
            'fecha_inicio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'fecha_fin': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['concejal'].queryset = Concejal.objects.all().order_by('apellidos', 'nombres')
        self.fields['personal_despacho'].queryset = PersonalDespacho.objects.select_related(
            'concejal'
        ).order_by('apellidos', 'nombres')

        # Etiquetas con nombre completo
        self.fields['concejal'].label_from_instance = lambda obj: obj.get_nombre_completo()
        self.fields['personal_despacho'].label_from_instance = (
            lambda obj: f'{obj.get_nombre_completo()} ({obj.concejal.get_nombre_completo()})'
        )

        # Hacer opcional el estado al crear (por defecto Pendiente)
        self.fields['afectado_tipo'].initial = Incidente.AFECTADO_PERSONAL

    def clean(self):
        cleaned_data = super().clean()
        afectado_tipo = cleaned_data.get('afectado_tipo')
        concejal = cleaned_data.get('concejal')
        personal = cleaned_data.get('personal_despacho')

        if afectado_tipo == Incidente.AFECTADO_CONCEJAL and not concejal:
            self.add_error('concejal', 'Debe seleccionar el concejal afectado.')
        if afectado_tipo == Incidente.AFECTADO_PERSONAL and not personal:
            self.add_error('personal_despacho', 'Debe seleccionar el personal de despacho afectado.')

        # Limpiar el campo no usado según el tipo de afectado
        if afectado_tipo == Incidente.AFECTADO_CONCEJAL:
            cleaned_data['personal_despacho'] = None
        elif afectado_tipo == Incidente.AFECTADO_PERSONAL:
            cleaned_data['concejal'] = None


        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            self.add_error('fecha_fin', 'La fecha de fin no puede ser anterior a la fecha de inicio.')

        return cleaned_data

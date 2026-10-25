from django import forms

from concejales.models import Concejal, PersonalDespacho

from .models import Asistencia


class AsistenciaForm(forms.ModelForm):
    """Formulario para registrar/editar manualmente una asistencia."""

    class Meta:
        model = Asistencia
        fields = [
            'afectado_tipo',
            'concejal',
            'personal_despacho',
            'fecha',
            'hora_entrada',
            'hora_salida',
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
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'hora_entrada': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
            }),
            'hora_salida': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['concejal'].queryset = Concejal.objects.all().order_by('apellidos', 'nombres')
        self.fields['personal_despacho'].queryset = PersonalDespacho.objects.select_related(
            'concejal'
        ).order_by('apellidos', 'nombres')
        self.fields['concejal'].label_from_instance = lambda obj: obj.get_nombre_completo()
        self.fields['personal_despacho'].label_from_instance = (
            lambda obj: f'{obj.get_nombre_completo()} ({obj.concejal.get_nombre_completo()})'
        )
        self.fields['afectado_tipo'].initial = Asistencia.AFECTADO_PERSONAL

    def clean(self):
        cleaned_data = super().clean()
        afectado_tipo = cleaned_data.get('afectado_tipo')
        concejal = cleaned_data.get('concejal')
        personal = cleaned_data.get('personal_despacho')

        if afectado_tipo == Asistencia.AFECTADO_CONCEJAL and not concejal:
            self.add_error('concejal', 'Debe seleccionar el concejal.')
        if afectado_tipo == Asistencia.AFECTADO_PERSONAL and not personal:
            self.add_error('personal_despacho', 'Debe seleccionar el personal de despacho.')

        # Limpiar el campo no usado según el tipo de afectado
        if afectado_tipo == Asistencia.AFECTADO_CONCEJAL:
            cleaned_data['personal_despacho'] = None
        elif afectado_tipo == Asistencia.AFECTADO_PERSONAL:
            cleaned_data['concejal'] = None

        hora_entrada = cleaned_data.get('hora_entrada')
        hora_salida = cleaned_data.get('hora_salida')
        if hora_entrada and hora_salida and hora_salida < hora_entrada:
            self.add_error('hora_salida', 'La hora de salida no puede ser anterior a la hora de entrada.')

        return cleaned_data

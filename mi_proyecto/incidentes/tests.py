from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from concejales.models import Concejal, PersonalDespacho

from .models import Incidente

Usuario = get_user_model()


class IncidentesTest(TestCase):

    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            email='admin@test.com',
            password='clave12345',
            first_name='Admin',
            last_name='Sistema',
        )
        self.usuario_concejal = Usuario.objects.create_user(
            email='concejal@test.com',
            password='clave12345',
            first_name='Carla',
            last_name='Concejal',
            rol=Usuario.ROL_CONCEJAL,
        )
        self.usuario_despacho = Usuario.objects.create_user(
            email='despacho@test.com',
            password='clave12345',
            first_name='Pedro',
            last_name='Despacho',
            rol=Usuario.ROL_DESPACHO,
        )

        self.concejal = Concejal.objects.create(
            cedula='12345678',
            nombres='Carla',
            apellidos='Concejal',
            telefono='0412-1234567',
            correo='carla@test.com',
            direccion='Av. Principal',
            comision_asignada='Comision de Salud',
            fecha_inicio_gestion='2025-01-10',
            horario_atencion='Lunes a Viernes 8:00 AM - 2:00 PM',
            estado=Concejal.ESTADO_ACTIVO,
            usuario=self.usuario_concejal,
        )
        self.personal = PersonalDespacho.objects.create(
            concejal=self.concejal,
            cedula='87654321',
            nombres='Pedro',
            apellidos='Despacho',
            telefono='0414-1234567',
            correo='pedro@test.com',
            cargo='Asistente Ejecutivo',
            fecha_ingreso='2025-01-15',
            horario_trabajo='Lunes a Viernes 8:00 AM - 4:00 PM',
            estado=PersonalDespacho.ESTADO_ACTIVO,
            usuario=self.usuario_despacho,
        )

    def crear_incidente(self, afectado_tipo=Incidente.AFECTADO_PERSONAL, estado=Incidente.ESTADO_PENDIENTE):
        return Incidente.objects.create(
            afectado_tipo=afectado_tipo,
            concejal=self.concejal if afectado_tipo == Incidente.AFECTADO_CONCEJAL else None,
            personal_despacho=self.personal if afectado_tipo == Incidente.AFECTADO_PERSONAL else None,
            tipo_permiso=Incidente.PERMISO_ENFERMEDAD,
            motivo='Reposo medico por 5 dias.',
            fecha_inicio='2026-08-10',
            fecha_fin='2026-08-15',
            estado=estado,
            registrado_por=self.admin,
        )

    def test_crear_incidente_personal(self):
        inc = self.crear_incidente(Incidente.AFECTADO_PERSONAL)
        self.assertEqual(inc.get_afectado_nombre(), 'Pedro Despacho')
        self.assertEqual(inc.get_duracion_dias(), 6)

    def test_crear_incidente_concejal(self):
        inc = self.crear_incidente(Incidente.AFECTADO_CONCEJAL)
        self.assertEqual(inc.get_afectado_nombre(), 'Carla Concejal')

    def test_incidente_sin_afectado_invalido(self):
        with self.assertRaises(ValidationError):
            Incidente.objects.create(
                afectado_tipo=Incidente.AFECTADO_CONCEJAL,
                concejal=None,
                personal_despacho=None,
                tipo_permiso=Incidente.PERMISO_OTRO,
                motivo='Sin afectado.',
                fecha_inicio='2026-08-10',
            )

    def test_fecha_fin_no_puede_ser_anterior(self):
        with self.assertRaises(ValidationError):
            Incidente.objects.create(
                afectado_tipo=Incidente.AFECTADO_PERSONAL,
                concejal=None,
                personal_despacho=self.personal,
                tipo_permiso=Incidente.PERMISO_ENFERMEDAD,
                motivo='Fechas invalidas.',
                fecha_inicio='2026-08-10',
                fecha_fin='2026-08-01',
            )

    def test_administrador_puede_registrar_incidente(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('crear_incidente'), {
            'afectado_tipo': Incidente.AFECTADO_PERSONAL,
            'personal_despacho': self.personal.pk,
            'tipo_permiso': Incidente.PERMISO_ENFERMEDAD,
            'motivo': 'Reposo medico.',
            'fecha_inicio': '2026-08-10',
            'fecha_fin': '2026-08-15',
            'estado': Incidente.ESTADO_PENDIENTE,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Incidente.objects.count(), 1)
        self.assertEqual(Incidente.objects.first().registrado_por, self.admin)

    def test_concejal_no_puede_registrar(self):
        self.client.force_login(self.usuario_concejal)
        response = self.client.get(reverse('crear_incidente'))
        self.assertEqual(response.status_code, 302)

    def test_despacho_no_puede_registrar(self):
        self.client.force_login(self.usuario_despacho)
        response = self.client.get(reverse('crear_incidente'))
        self.assertEqual(response.status_code, 302)

    def test_despacho_solo_ve_su_despacho(self):
        self.crear_incidente(Incidente.AFECTADO_PERSONAL)
        otro_concejal = Concejal.objects.create(
            cedula='11111111',
            nombres='Otro',
            apellidos='Concejal',
            telefono='0416-1234567',
            correo='otro@test.com',
            direccion='Calle 1',
            comision_asignada='Comision de Obras',
            fecha_inicio_gestion='2025-02-01',
            horario_atencion='Lunes a Viernes 8:00 AM - 2:00 PM',
            estado=Concejal.ESTADO_ACTIVO,
        )
        Incidente.objects.create(
            afectado_tipo=Incidente.AFECTADO_CONCEJAL,
            concejal=otro_concejal,
            personal_despacho=None,
            tipo_permiso=Incidente.PERMISO_VACACIONES,
            motivo='Vacaciones.',
            fecha_inicio='2026-08-20',
            registrado_por=self.admin,
        )
        self.client.force_login(self.usuario_despacho)
        response = self.client.get(reverse('lista_incidentes'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['incidentes']), 1)

    def test_administrador_cambia_estado(self):
        inc = self.crear_incidente()
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('cambiar_estado_incidente', args=[inc.pk]),
            {'estado': Incidente.ESTADO_APROBADO},
        )
        self.assertEqual(response.status_code, 302)
        inc.refresh_from_db()
        self.assertEqual(inc.estado, Incidente.ESTADO_APROBADO)

    def test_administrador_elimina_incidente(self):
        inc = self.crear_incidente()
        self.client.force_login(self.admin)
        response = self.client.post(reverse('eliminar_incidente', args=[inc.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Incidente.objects.count(), 0)
    def test_plantillas_renderizan(self):
        """Verifica que las plantillas del modulo rendericen sin errores."""
        inc = self.crear_incidente(Incidente.AFECTADO_PERSONAL)
        self.client.force_login(self.admin)
        # Detalle
        r = self.client.get(reverse('detalle_incidente', args=[inc.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Pedro Despacho')
        # Formulario nuevo
        r = self.client.get(reverse('crear_incidente'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Registrar Incidente')
        # Lista
        r = self.client.get(reverse('lista_incidentes'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Pedro Despacho')

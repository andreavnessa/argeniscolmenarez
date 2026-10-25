"""Pruebas del modulo de Reportes (RF-09)."""

from datetime import time

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from asistencia.models import Asistencia
from autenticacion.models import Usuario
from concejales.models import Concejal, PersonalDespacho
from incidentes.models import Incidente


class ReportesTest(TestCase):

    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            email='admin@test.com', password='Admin2026!',
            first_name='Admin', last_name='Sistema',
        )
        self.concejal_usuario = Usuario.objects.create_user(
            email='concejal@test.com', password='Clave2026!',
            first_name='Luis', last_name='Rodriguez', rol=Usuario.ROL_CONCEJAL,
        )
        self.despacho_usuario = Usuario.objects.create_user(
            email='despacho@test.com', password='Clave2026!',
            first_name='Ana', last_name='Despacho', rol=Usuario.ROL_DESPACHO,
        )
        self.concejal = Concejal.objects.create(
            cedula='123456', nombres='Luis', apellidos='Rodriguez',
            telefono='0412-1234567', correo='luis@concejo.com',
            direccion='Av Principal', comision_asignada='Comision de Salud',
            fecha_inicio_gestion='2025-01-10',
            horario_atencion='Lunes a Viernes 8:00 AM - 2:00 PM',
            estado=Concejal.ESTADO_ACTIVO, usuario=self.concejal_usuario,
        )
        self.personal = PersonalDespacho.objects.create(
            concejal=self.concejal, cedula='654321', nombres='Ana',
            apellidos='Despacho', telefono='0414-1234567',
            correo='ana@concejo.com', cargo='Asistente Ejecutivo',
            fecha_ingreso='2025-02-01', horario_trabajo='L-V 8-4',
            estado=PersonalDespacho.ESTADO_ACTIVO, usuario=self.despacho_usuario,
        )

    def login(self, rol='admin'):
        self.client.logout()
        claves = {
            'admin': ('admin@test.com', 'Admin2026!'),
            'concejal': ('concejal@test.com', 'Clave2026!'),
            'despacho': ('despacho@test.com', 'Clave2026!'),
        }
        email, pw = claves[rol]
        return self.client.login(email=email, password=pw)

    def test_panel_requiere_login(self):
        r = self.client.get(reverse('reportes'))
        self.assertEqual(r.status_code, 302)

    def test_panel_admin_visto(self):
        self.assertTrue(self.login('admin'))
        r = self.client.get(reverse('reportes'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Reporte de Asistencia')

    def test_reportes_renderizan(self):
        self.assertTrue(self.login('admin'))
        for nombre in ('reporte_asistencia', 'reporte_incidencias', 'reporte_concejales'):
            r = self.client.get(reverse(nombre))
            self.assertEqual(r.status_code, 200, nombre)

    def test_csv_descarga(self):
        self.assertTrue(self.login('admin'))
        for nombre in ('reporte_asistencia_csv', 'reporte_incidencias_csv', 'reporte_concejales_csv'):
            r = self.client.get(reverse(nombre))
            self.assertEqual(r.status_code, 200, nombre)
            self.assertIn('text/csv', r['Content-Type'], nombre)
            self.assertIn('attachment', r['Content-Disposition'], nombre)

    def test_despacho_solo_ve_su_despacho(self):
        otro = Concejal.objects.create(
            cedula='999999', nombres='Otro', apellidos='Concejal',
            telefono='0412-2222222', correo='otro@concejo.com',
            direccion='Calle 1', comision_asignada='Obras',
            fecha_inicio_gestion='2025-01-01', horario_atencion='L-V',
            estado=Concejal.ESTADO_ACTIVO,
        )
        personal_otro = PersonalDespacho.objects.create(
            concejal=otro, cedula='888888', nombres='Maria', apellidos='Otro',
            telefono='0412-3333333', correo='maria@otro.com', cargo='Otro',
            fecha_ingreso='2025-01-01', horario_trabajo='L-V',
            estado=PersonalDespacho.ESTADO_ACTIVO,
        )
        hoy = timezone.localdate()
        Asistencia.objects.create(
            afectado_tipo=Asistencia.AFECTADO_PERSONAL,
            personal_despacho=self.personal, fecha=hoy, hora_entrada=time(8, 0),
        )
        Asistencia.objects.create(
            afectado_tipo=Asistencia.AFECTADO_PERSONAL,
            personal_despacho=personal_otro, fecha=hoy, hora_entrada=time(8, 0),
        )
        Incidente.objects.create(
            afectado_tipo=Incidente.AFECTADO_CONCEJAL, concejal=self.concejal,
            personal_despacho=None, tipo_permiso=Incidente.PERMISO_REPOSO,
            motivo='Reposo.', fecha_inicio=hoy, estado=Incidente.ESTADO_PENDIENTE,
            registrado_por=self.admin,
        )
        Incidente.objects.create(
            afectado_tipo=Incidente.AFECTADO_CONCEJAL, concejal=otro,
            personal_despacho=None, tipo_permiso=Incidente.PERMISO_VACACIONES,
            motivo='Vacaciones.', fecha_inicio=hoy, estado=Incidente.ESTADO_PENDIENTE,
            registrado_por=self.admin,
        )
        self.assertTrue(self.login('despacho'))
        r = self.client.get(reverse('reporte_asistencia'))
        self.assertContains(r, 'Ana Despacho')
        self.assertNotContains(r, 'Maria Otro')
        r = self.client.get(reverse('reporte_incidencias'))
        self.assertContains(r, 'Luis Rodriguez')
        self.assertNotContains(r, 'Otro Concejal')
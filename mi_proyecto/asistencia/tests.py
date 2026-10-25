"""Pruebas del modulo de Asistencia (entrada y salida)."""

from datetime import time

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from autenticacion.models import Usuario
from concejales.models import Concejal, PersonalDespacho

from .models import Asistencia


class AsistenciaTest(TestCase):

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

    def login_admin(self):
        return self.client.login(email='admin@test.com', password='Admin2026!')

    def test_admin_marca_entrada_y_salida(self):
        self.assertTrue(self.login_admin())
        r = self.client.post(reverse('marcar_entrada'), {'afectado': f'personal:{self.personal.pk}'})
        self.assertEqual(r.status_code, 302)
        reg = Asistencia.objects.get(personal_despacho=self.personal, fecha=timezone.localdate())
        self.assertIsNotNone(reg.hora_entrada)

        r = self.client.post(reverse('marcar_salida'), {'afectado': f'personal:{self.personal.pk}'})
        self.assertEqual(r.status_code, 302)
        reg.refresh_from_db()
        self.assertIsNotNone(reg.hora_salida)
        self.assertEqual(Asistencia.objects.count(), 1)

    def test_admin_no_duplica_entrada(self):
        self.assertTrue(self.login_admin())
        dato = {'afectado': f'personal:{self.personal.pk}'}
        self.client.post(reverse('marcar_entrada'), dato)
        self.client.post(reverse('marcar_entrada'), dato)
        self.assertEqual(Asistencia.objects.filter(fecha=timezone.localdate()).count(), 1)

    def test_salida_sin_entrada_advierte(self):
        self.assertTrue(self.login_admin())
        r = self.client.post(reverse('marcar_salida'), {'afectado': f'personal:{self.personal.pk}'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Asistencia.objects.count(), 0)

    def test_solo_admin_puede_marcar(self):
        self.client.login(email='concejal@test.com', password='Clave2026!')
        r = self.client.post(reverse('marcar_entrada'), {'afectado': f'concejal:{self.concejal.pk}'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Asistencia.objects.count(), 0)

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
        self.client.logout()
        self.client.login(email='despacho@test.com', password='Clave2026!')
        r = self.client.get(reverse('lista_asistencia'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ana Despacho')
        self.assertNotContains(r, 'Maria Otro')

    def test_duracion_calculada(self):
        a = Asistencia.objects.create(
            afectado_tipo=Asistencia.AFECTADO_PERSONAL,
            personal_despacho=self.personal, fecha=timezone.localdate(),
            hora_entrada=time(8, 0), hora_salida=time(16, 30),
        )
        self.assertEqual(a.get_duracion_horas(), '8h 30m')

    def test_salida_anterior_a_entrada_invalida(self):
        with self.assertRaises(ValidationError):
            Asistencia.objects.create(
                afectado_tipo=Asistencia.AFECTADO_PERSONAL,
                personal_despacho=self.personal, fecha=timezone.localdate(),
                hora_entrada=time(16, 0), hora_salida=time(8, 0),
            )

    def test_no_duplicado_mismo_dia_misma_persona(self):
        Asistencia.objects.create(
            afectado_tipo=Asistencia.AFECTADO_PERSONAL,
            personal_despacho=self.personal, fecha=timezone.localdate(),
            hora_entrada=time(8, 0),
        )
        with self.assertRaises(Exception):
            Asistencia.objects.create(
                afectado_tipo=Asistencia.AFECTADO_PERSONAL,
                personal_despacho=self.personal, fecha=timezone.localdate(),
                hora_entrada=time(9, 0),
            )

    def test_plantillas_renderizan(self):
        self.assertTrue(self.login_admin())
        r = self.client.get(reverse('lista_asistencia'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Asistencia')
        r = self.client.get(reverse('crear_asistencia'))
        self.assertEqual(r.status_code, 200)
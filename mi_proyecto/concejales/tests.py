"""Pruebas del módulo de Concejales y Personal de Despacho + flujo de trabajo completo."""

from django.test import Client, TestCase

from autenticacion.models import Usuario
from incidentes.models import Incidente

from .models import Concejal, PersonalDespacho


def datos_concejal(cedula, correo):
    return {
        'cedula': cedula,
        'nombres': 'Luis',
        'apellidos': 'Rodriguez',
        'telefono': '0412-1234567',
        'correo': correo,
        'direccion': 'Av. Principal 123',
        'comision_asignada': 'Comision de Salud',
        'fecha_inicio_gestion': '2025-01-10',
        'horario_atencion': 'Lunes a Viernes 8:00 AM - 2:00 PM',
        'estado': Concejal.ESTADO_ACTIVO,
    }


def datos_personal(cedula, correo):
    return {
        'cedula': cedula,
        'nombres': 'Ana',
        'apellidos': 'Despacho',
        'telefono': '0414-1234567',
        'correo': correo,
        'cargo': 'Asistente Ejecutivo',
        'fecha_ingreso': '2025-02-01',
        'horario_trabajo': 'Lunes a Viernes 8:00 AM - 4:00 PM',
        'estado': PersonalDespacho.ESTADO_ACTIVO,
    }


class BaseConcejalesTest(TestCase):

    def setUp(self):
        self.client = Client()
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
            **datos_concejal('123456', 'luis@concejo.com'),
            usuario=self.concejal_usuario,
        )
        self.personal = PersonalDespacho.objects.create(
            **datos_personal('654321', 'ana@concejo.com'),
            concejal=self.concejal,
            usuario=self.despacho_usuario,
        )
        self.client.login(email='admin@test.com', password='Admin2026!')


class ConcejalCrudTest(BaseConcejalesTest):
    """CRUD de concejales por el administrador."""

    def test_admin_crea_concejal(self):
        r = self.client.post('/concejales/nuevo/', datos_concejal('234567', 'nuevo@concejo.com'))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Concejal.objects.filter(cedula='234567').exists())

    def test_admin_edita_concejal(self):
        r = self.client.post(f'/concejales/{self.concejal.pk}/editar/', {
            **datos_concejal('123456', 'luis@concejo.com'),
            'nombres': 'Luis Alberto',
        })
        self.assertEqual(r.status_code, 302)
        self.concejal.refresh_from_db()
        self.assertEqual(self.concejal.nombres, 'Luis Alberto')

    def test_cedula_duplicada_rechazada(self):
        datos = datos_concejal('123456', 'otrocorreo@concejo.com')
        r = self.client.post('/concejales/nuevo/', datos)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ya existe un concejal')

    def test_no_administrador_no_crea_concejal(self):
        self.client.logout()
        self.client.login(email='concejal@test.com', password='Clave2026!')
        r = self.client.get('/concejales/nuevo/')
        self.assertEqual(r.status_code, 302)


class PersonalCrudTest(BaseConcejalesTest):
    """CRUD de personal de despacho y reglas de negocio."""

    def test_admin_crea_personal(self):
        r = self.client.post('/personal-despacho/nuevo/', {
            'concejal': self.concejal.pk,
            **datos_personal('111222', 'pedro@concejo.com'),
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(PersonalDespacho.objects.filter(cedula='111222').exists())

    def test_cedula_duplicada_personal_rechazada(self):
        r = self.client.post('/personal-despacho/nuevo/', {
            'concejal': self.concejal.pk,
            **datos_personal('654321', 'otro@concejo.com'),
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ya existe un miembro del personal')

    def test_limite_8_personal_activo(self):
        # Ya hay 1 personal activo; agrego 7 más para llegar al límite (8)
        for i in range(7):
            PersonalDespacho.objects.create(
                concejal=self.concejal,
                cedula=f'3000000{i}',
                nombres=f'P{i}',
                apellidos='Prueba',
                telefono='0412-1111111',
                correo=f'p{i}@concejo.com',
                cargo='Otro',
                fecha_ingreso='2025-01-01',
                horario_trabajo='L - V 8-4',
                estado=PersonalDespacho.ESTADO_ACTIVO,
            )
        self.assertFalse(self.concejal.puede_agregar_personal())
        # El intento de agregar el 9no activo debe fallar
        r = self.client.post('/personal-despacho/nuevo/', {
            'concejal': self.concejal.pk,
            **datos_personal('777888', 'nueve@concejo.com'),
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'antes de agregar más personal')

    def test_desactivar_y_activar_personal(self):
        self.client.post(f'/personal-despacho/{self.personal.pk}/desactivar/')
        self.personal.refresh_from_db()
        self.assertEqual(self.personal.estado, PersonalDespacho.ESTADO_INACTIVO)
        self.client.post(f'/personal-despacho/{self.personal.pk}/activar/')
        self.personal.refresh_from_db()
        self.assertEqual(self.personal.estado, PersonalDespacho.ESTADO_ACTIVO)

    def test_admin_reasigna_personal(self):
        otro = Concejal.objects.create(**datos_concejal('345678', 'otra@concejo.com'))
        r = self.client.post(f'/personal-despacho/{self.personal.pk}/reasignar/', {'concejal': otro.pk})
        self.assertEqual(r.status_code, 302)
        self.personal.refresh_from_db()
        self.assertEqual(self.personal.concejal_id, otro.pk)


class ActivacionConcejalTest(BaseConcejalesTest):
    """Activación / desactivación de concejales."""

    def test_desactivar_concejal_desactiva_personal(self):
        r = self.client.post(f'/concejales/{self.concejal.pk}/desactivar/')
        self.assertEqual(r.status_code, 302)
        self.concejal.refresh_from_db()
        self.personal.refresh_from_db()
        self.assertEqual(self.concejal.estado, Concejal.ESTADO_INACTIVO)
        self.assertEqual(self.personal.estado, PersonalDespacho.ESTADO_INACTIVO)

    def test_activar_concejal(self):
        self.concejal.estado = Concejal.ESTADO_INACTIVO
        self.concejal.save()
        self.client.post(f'/concejales/{self.concejal.pk}/activar/')
        self.concejal.refresh_from_db()
        self.assertEqual(self.concejal.estado, Concejal.ESTADO_ACTIVO)


class RolesTest(BaseConcejalesTest):
    """Restricciones de acceso por rol."""

    def test_concejal_ve_solo_su_despacho(self):
        otro = Concejal.objects.create(**datos_concejal('999999', 'otro@concejo.com'))
        PersonalDespacho.objects.create(
            concejal=otro, cedula='888888', nombres='Pedro', apellidos='Otro',
            telefono='0412-2222222', correo='pedro@otro.com', cargo='Otro',
            fecha_ingreso='2025-01-01', horario_trabajo='L - V 8-4',
            estado=PersonalDespacho.ESTADO_ACTIVO,
        )
        self.client.logout()
        self.client.login(email='concejal@test.com', password='Clave2026!')
        # La lista de concejales redirige a su propio despacho
        r = self.client.get('/concejales/')
        self.assertEqual(r.status_code, 302)
        self.assertIn(str(self.concejal.pk), r.url)
        # Detalle de OTRO concejal -> redirige
        r = self.client.get(f'/concejales/{otro.pk}/')
        self.assertEqual(r.status_code, 302)
        # Lista de personal: solo su despacho
        r = self.client.get('/personal-despacho/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ana Despacho')
        self.assertNotContains(r, 'Pedro Otro')
        # No puede crear concejales (solo admin)
        r = self.client.get('/concejales/nuevo/')
        self.assertEqual(r.status_code, 302)
        # Sí puede crear personal en su despacho
        r = self.client.get('/personal-despacho/nuevo/')
        self.assertEqual(r.status_code, 200)
        # No puede reasignar personal (solo admin)
        r = self.client.get(f'/personal-despacho/{self.personal.pk}/reasignar/')
        self.assertEqual(r.status_code, 302)

    def test_concejal_no_edita_personal_de_otro(self):
        otro = Concejal.objects.create(**datos_concejal('999998', 'otro2@concejo.com'))
        personal_otro = PersonalDespacho.objects.create(
            concejal=otro, cedula='888887', nombres='Maria', apellidos='Otro',
            telefono='0412-3333333', correo='maria@otro.com', cargo='Otro',
            fecha_ingreso='2025-01-01', horario_trabajo='L - V 8-4',
            estado=PersonalDespacho.ESTADO_ACTIVO,
        )
        self.client.logout()
        self.client.login(email='concejal@test.com', password='Clave2026!')
        r = self.client.get(f'/personal-despacho/{personal_otro.pk}/editar/')
        self.assertEqual(r.status_code, 302)

    def test_despacho_solo_lectura(self):
        self.client.logout()
        self.client.login(email='despacho@test.com', password='Clave2026!')
        r = self.client.get('/personal-despacho/')
        self.assertEqual(r.status_code, 200)
        # No puede crear
        r = self.client.get('/personal-despacho/nuevo/')
        self.assertEqual(r.status_code, 302)
        # No puede editar
        r = self.client.get(f'/personal-despacho/{self.personal.pk}/editar/')
        self.assertEqual(r.status_code, 302)
        # No puede ver otro despacho
        otro = Concejal.objects.create(**datos_concejal('999997', 'otro3@concejo.com'))
        r = self.client.get(f'/concejales/{otro.pk}/')
        self.assertEqual(r.status_code, 302)
        # No accede al panel admin
        r = self.client.get('/admin/')
        self.assertTrue(r.status_code != 200)


class FlujoCompletoTest(BaseConcejalesTest):
    """Flujo de trabajo completo: concejal -> personal -> incidente -> aprobación."""

    def test_flujo_completo_administrador(self):
        # 1. El admin registra un concejal y su personal
        r = self.client.post('/concejales/nuevo/', datos_concejal('765432', 'flujo@concejo.com'))
        self.assertEqual(r.status_code, 302)
        nuevo = Concejal.objects.get(cedula='765432')

        r = self.client.post('/personal-despacho/nuevo/', {
            'concejal': nuevo.pk,
            'cedula': '443322',
            'nombres': 'Maria',
            'apellidos': 'Gomez',
            'telefono': '0424-5556677',
            'correo': 'maria@concejo.com',
            'cargo': 'Secretario(a)',
            'fecha_ingreso': '2025-01-10',
            'horario_trabajo': 'L - V 8-4',
            'estado': PersonalDespacho.ESTADO_ACTIVO,
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(PersonalDespacho.objects.filter(cedula='443322').exists())

        # 2. El admin registra un incidente para el personal de su propio despacho
        r = self.client.post('/incidentes/nuevo/', {
            'afectado_tipo': Incidente.AFECTADO_PERSONAL,
            'personal_despacho': self.personal.pk,
            'tipo_permiso': Incidente.PERMISO_ENFERMEDAD,
            'motivo': 'Permiso por enfermedad.',
            'fecha_inicio': '2026-08-10',
            'fecha_fin': '2026-08-12',
            'estado': Incidente.ESTADO_PENDIENTE,
        })
        self.assertEqual(r.status_code, 302)
        incidente = Incidente.objects.get(personal_despacho=self.personal)
        self.assertEqual(incidente.estado, Incidente.ESTADO_PENDIENTE)
        self.assertEqual(incidente.registrado_por, self.admin)

        # 3. El admin aprueba y luego finaliza el incidente
        r = self.client.post(f'/incidentes/{incidente.pk}/estado/', {'estado': Incidente.ESTADO_APROBADO})
        self.assertEqual(r.status_code, 302)
        incidente.refresh_from_db()
        self.assertEqual(incidente.estado, Incidente.ESTADO_APROBADO)

        r = self.client.post(f'/incidentes/{incidente.pk}/estado/', {'estado': Incidente.ESTADO_FINALIZADO})
        self.assertEqual(r.status_code, 302)
        incidente.refresh_from_db()
        self.assertEqual(incidente.estado, Incidente.ESTADO_FINALIZADO)

        # 4. El concejal puede consultar el incidente de su despacho
        self.client.logout()
        self.client.login(email='concejal@test.com', password='Clave2026!')
        r = self.client.get('/incidentes/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ana Despacho')

        # 5. El personal de despacho también puede consultarlo (solo lectura)
        self.client.logout()
        self.client.login(email='despacho@test.com', password='Clave2026!')
        r = self.client.get('/incidentes/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ana Despacho')
        r = self.client.get('/incidentes/nuevo/')
        self.assertEqual(r.status_code, 302)




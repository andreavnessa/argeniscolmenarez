"""Pruebas del módulo de autenticación: login, bloqueo y recuperación de contraseña."""

from django.test import Client, TestCase

from .models import Usuario


class AutenticacionTests(TestCase):

    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            email='admin@test.com',
            password='Admin2026!',
            first_name='Admin',
            last_name='Sistema',
        )
        self.usuario = Usuario.objects.create_user(
            email='usuario@test.com',
            password='Clave2026!',
            first_name='Juan',
            last_name='Perez',
            rol=Usuario.ROL_DESPACHO,
            pregunta_seguridad=Usuario.PREGUNTAS_SEGURIDAD[0][0],
            respuesta_seguridad='rex',
        )
        self.client = Client()

    def test_login_exitoso_y_dashboard(self):
        r = self.client.post('/login/', {'email': 'admin@test.com', 'password': 'Admin2026!'})
        self.assertEqual(r.status_code, 302)
        r = self.client.get('/dashboard/')
        self.assertEqual(r.status_code, 200)

    def test_login_incorrecto_muestra_error(self):
        r = self.client.post('/login/', {'email': 'admin@test.com', 'password': 'clave-mala'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Contraseña incorrecta')

    def test_login_cuenta_inexistente(self):
        r = self.client.post('/login/', {'email': 'noexiste@test.com', 'password': 'x12345678'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'no son válidas')

    def test_bloqueo_despues_de_5_intentos(self):
        for _ in range(5):
            self.client.post('/login/', {'email': 'usuario@test.com', 'password': 'clave-mala'})
        usuario = Usuario.objects.get(email='usuario@test.com')
        self.assertTrue(usuario.esta_bloqueado())
        # Aun con la clave correcta, la cuenta sigue bloqueada
        r = self.client.post('/login/', {'email': 'usuario@test.com', 'password': 'Clave2026!'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'bloqueada')

    def test_flujo_recuperar_contrasena(self):
        # Paso 1: enviar correo
        r = self.client.post('/recuperar-contrasena/', {'email': 'usuario@test.com'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, '/pregunta-seguridad/')
        # Paso 2: responder pregunta de seguridad
        r = self.client.post('/pregunta-seguridad/', {'respuesta': 'rex'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, '/nueva-contrasena/')
        # Paso 3: establecer nueva contraseña
        r = self.client.post('/nueva-contrasena/', {
            'nueva_contrasena': 'NuevaClave2026!',
            'confirmar_contrasena': 'NuevaClave2026!',
        })
        self.assertEqual(r.status_code, 302)
        # La nueva contraseña debe funcionar
        self.client.logout()
        self.assertTrue(self.client.login(email='usuario@test.com', password='NuevaClave2026!'))

    def test_logout_cierra_sesion(self):
        self.client.login(email='admin@test.com', password='Admin2026!')
        r = self.client.get('/logout/')
        self.assertEqual(r.status_code, 302)
        r = self.client.get('/dashboard/')
        self.assertEqual(r.status_code, 302)  # requiere login de nuevo

    def test_dashboard_requiere_login(self):
        r = self.client.get('/dashboard/')
        self.assertEqual(r.status_code, 302)

    def test_dashboard_muestra_modulos(self):
        self.client.login(email='admin@test.com', password='Admin2026!')
        r = self.client.get('/dashboard/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Concejales')
        self.assertContains(r, 'Personal de Despacho')
        self.assertContains(r, 'Incidentes y Permisos')

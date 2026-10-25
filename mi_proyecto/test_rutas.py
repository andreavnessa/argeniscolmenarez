import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from autenticacion.models import Usuario
from concejales.models import Concejal

# Crear un usuario de prueba si no existe y asociarlo al personal de Ana Rodriguez
if not Usuario.objects.filter(email='test@test.com').exists():
    Usuario.objects.create_user(
        email='test@test.com',
        password='testpass123',
        first_name='Test',
        last_name='User',
        pregunta_seguridad='mascota',
        respuesta_seguridad='rex',
        rol=Usuario.ROL_DESPACHO,
    )
    print('Usuario de prueba creado')

test_user = Usuario.objects.get(email='test@test.com')
test_user.rol = Usuario.ROL_DESPACHO
test_user.save()

# Asociar al personal de despacho del concejal Ana Rodriguez (si no está asociado)
ana = Concejal.objects.get(cedula='99999999')
pedro = ana.personal_despacho.get(cedula='88888888')
if not hasattr(test_user, 'personal_despacho_perfil'):
    pedro.usuario = test_user
    pedro.save()
    print('Usuario test@test.com asociado al despacho de Ana Rodriguez')

# Probar login
c = Client(HTTP_HOST='localhost')
response = c.post('/login/', {'email': 'test@test.com', 'password': 'testpass123'})
print(f'POST /login/ -> {response.status_code} (redirect: {response.get("Location", "none")})')

# Probar dashboard autenticado
response = c.get('/dashboard/')
print(f'GET /dashboard/ -> {response.status_code}')

# Probar concejales autenticado (despacho: redirige a su propio despacho)
response = c.get('/concejales/')
print(f'GET /concejales/ -> {response.status_code} (redirect: {response.get("Location", "none")})')

# Probar personal autenticado (solo ve su despacho)
response = c.get('/personal-despacho/')
print(f'GET /personal-despacho/ -> {response.status_code}')

# Probar que NO puede crear personal (solo lectura)
response = c.get('/personal-despacho/nuevo/')
print(f'GET /personal-despacho/nuevo/ -> {response.status_code} (redirect: {response.get("Location", "none")})')

# Probar incidentes autenticado (despacho: solo lectura y solo su despacho)
response = c.get('/incidentes/')
print(f'GET /incidentes/ -> {response.status_code}')

# Probar que NO puede registrar incidentes (solo administrador)
response = c.get('/incidentes/nuevo/')
print(f'GET /incidentes/nuevo/ -> {response.status_code} (redirect: {response.get("Location", "none")})')


# Probar logout
response = c.get('/logout/')
print(f'GET /logout/ -> {response.status_code} (redirect: {response.get("Location", "none")})')

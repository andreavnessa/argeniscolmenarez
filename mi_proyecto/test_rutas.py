import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from autenticacion.models import Usuario

# Crear un usuario de prueba si no existe
if not Usuario.objects.filter(email='test@test.com').exists():
    Usuario.objects.create_user(
        email='test@test.com',
        password='testpass123',
        first_name='Test',
        last_name='User',
        pregunta_seguridad='mascota',
        respuesta_seguridad='rex'
    )
    print('Usuario de prueba creado')

# Probar login
c = Client()
response = c.post('/login/', {'email': 'test@test.com', 'password': 'testpass123'})
print(f'POST /login/ -> {response.status_code} (redirect: {response.get("Location", "none")})')

# Probar dashboard autenticado
response = c.get('/dashboard/')
print(f'GET /dashboard/ -> {response.status_code}')

# Probar concejales autenticado
response = c.get('/concejales/')
print(f'GET /concejales/ -> {response.status_code}')

# Probar personal autenticado
response = c.get('/personal-despacho/')
print(f'GET /personal-despacho/ -> {response.status_code}')

# Probar logout
response = c.get('/logout/')
print(f'GET /logout/ -> {response.status_code} (redirect: {response.get("Location", "none")})')
"""Verificación rápida del sistema de roles (usa la BD real).

Prueba los accesos permitidos/denegados para cada rol:
    - Administrador: permisos totales.
    - Concejal: solo su despacho, puede gestionar su personal.
    - Personal de Despacho: solo lectura de su propio despacho.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from autenticacion.models import Usuario
from concejales.models import Concejal

OK = '\033[92m[OK]\033[0m'
FAIL = '\033[91m[FAIL]\033[0m'


def login(client, email, password):
    return client.post('/login/', {'email': email, 'password': password})


def make_client():
    return Client(HTTP_HOST='localhost')


def check(nombre, condicion):
    print(f'{OK if condicion else FAIL} {nombre}')
    return condicion


# Datos de prueba
admin_u = Usuario.objects.get(email='admin@argenisc.com')
concejal_u = Usuario.objects.get(email='concejal@argenisc.com')
despacho_u = Usuario.objects.get(email='despacho@argenisc.com')

luis = Concejal.objects.get(cedula='123456')       # concejal de concejal@argenisc.com
ana = Concejal.objects.get(cedula='99999999')      # otro concejal
daniel = luis.personal_despacho.get(cedula='1234555')          # personal de Luis
pedro = ana.personal_despacho.get(cedula='88888888')           # personal de Ana

resultados = []
print('\n===== ADMINISTRADOR =====')
c = make_client()
check('login admin', login(c, 'admin@argenisc.com', 'Admin2026!Sistema').status_code == 302)
resultados.append(check('admin GET /concejales/ -> 200', c.get('/concejales/').status_code == 200))
resultados.append(check('admin GET detalle otro concejal -> 200', c.get(f'/concejales/{ana.pk}/').status_code == 200))
resultados.append(check('admin GET /concejales/nuevo/ -> 200', c.get('/concejales/nuevo/').status_code == 200))
resultados.append(check('admin GET /personal-despacho/nuevo/ -> 200', c.get('/personal-despacho/nuevo/').status_code == 200))
resultados.append(check('admin GET /personal-despacho/<pedro>/editar/ -> 200', c.get(f'/personal-despacho/{pedro.pk}/editar/').status_code == 200))
resultados.append(check('admin GET /personal-despacho/<pedro>/reasignar/ -> 200', c.get(f'/personal-despacho/{pedro.pk}/reasignar/').status_code == 200))
resultados.append(check('admin GET /admin/ -> 200', c.get('/admin/').status_code == 200))

print('\n===== CONCEJAL (Luis) =====')
c = make_client()
check('login concejal', login(c, 'concejal@argenisc.com', 'Concejal2026!Sistema').status_code == 302)
r = c.get('/concejales/')
resultados.append(check('concejal GET /concejales/ redirige a su despacho', r.status_code == 302 and '/concejales/' in r.get('Location', '')))
resultados.append(check('concejal GET detalle SU concejal -> 200', c.get(f'/concejales/{luis.pk}/').status_code == 200))
r = c.get(f'/concejales/{ana.pk}/')
resultados.append(check('concejal GET detalle OTRO concejal -> redirige', r.status_code == 302))
resultados.append(check('concejal GET /concejales/nuevo/ -> redirige (solo admin)', c.get('/concejales/nuevo/').status_code == 302))
resultados.append(check('concejal GET /concejales/<ana>/editar/ -> redirige (solo admin)', c.get(f'/concejales/{ana.pk}/editar/').status_code == 302))
r = c.get('/personal-despacho/')
resultados.append(check('concejal GET /personal-despacho/ -> 200', r.status_code == 200))
resultados.append(check('concejal solo ve SU personal en la lista', b'Daniel Perez' in r.content and b'Pedro Martinez' not in r.content))
resultados.append(check('concejal GET /personal-despacho/nuevo/ -> 200 (puede crear)', c.get('/personal-despacho/nuevo/').status_code == 200))
resultados.append(check('concejal GET editar SU personal -> 200', c.get(f'/personal-despacho/{daniel.pk}/editar/').status_code == 200))
r = c.get(f'/personal-despacho/{pedro.pk}/editar/')
resultados.append(check('concejal GET editar personal de OTRO -> redirige', r.status_code == 302))
r = c.get(f'/personal-despacho/{pedro.pk}/reasignar/')
resultados.append(check('concejal GET reasignar -> redirige (solo admin)', r.status_code == 302))
resultados.append(check('concejal GET /admin/ -> NO accede', c.get('/admin/').status_code != 200))

print('\n===== PERSONAL DE DESPACHO (Daniel) =====')
c = make_client()
check('login despacho', login(c, 'despacho@argenisc.com', 'Despacho2026!Sistema').status_code == 302)
r = c.get('/concejales/')
resultados.append(check('despacho GET /concejales/ redirige a su despacho', r.status_code == 302 and '/concejales/' in r.get('Location', '')))
resultados.append(check('despacho GET detalle SU concejal -> 200', c.get(f'/concejales/{luis.pk}/').status_code == 200))
r = c.get(f'/concejales/{ana.pk}/')
resultados.append(check('despacho GET detalle OTRO concejal -> redirige', r.status_code == 302))
r = c.get('/personal-despacho/')
resultados.append(check('despacho GET /personal-despacho/ -> 200', r.status_code == 200))
resultados.append(check('despacho solo ve compañeros de SU despacho', b'Daniel Perez' in r.content and b'Pedro Martinez' not in r.content))
resultados.append(check('despacho GET /personal-despacho/nuevo/ -> redirige (solo lectura)', c.get('/personal-despacho/nuevo/').status_code == 302))
r = c.get(f'/personal-despacho/{daniel.pk}/editar/')
resultados.append(check('despacho GET editar personal -> redirige (solo lectura)', r.status_code == 302))
r = c.get(f'/personal-despacho/{daniel.pk}/reasignar/')
resultados.append(check('despacho GET reasignar -> redirige (solo admin)', r.status_code == 302))
resultados.append(check('despacho GET /admin/ -> NO accede', c.get('/admin/').status_code != 200))

print('\n===== RESUMEN =====')
print(f'{sum(resultados)}/{len(resultados)} verificaciones correctas')

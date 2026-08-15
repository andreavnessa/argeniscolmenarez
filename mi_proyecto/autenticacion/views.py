from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from concejales.models import Concejal, PersonalDespacho

from .forms import (
    LoginForm,
    NuevaContrasenaForm,
    PreguntaSeguridadForm,
    RecuperarContrasenaForm,
)
from .models import Usuario


@require_http_methods(['GET', 'POST'])
def login_view(request):
    """Vista de inicio de sesión."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        usuario = form.get_user()
        if usuario:
            # Login exitoso
            login(request, usuario, backend='django.contrib.auth.backends.ModelBackend')
            usuario.reset_intentos_fallidos()

            # Configurar duración de sesión
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)  # Expira al cerrar el navegador
            else:
                request.session.set_expiry(60 * 60 * 24 * 7)  # 7 días

            messages.success(request, f'¡Bienvenido, {usuario.get_full_name()}!')
            return redirect('dashboard')

    return render(request, 'autenticacion/login.html', {'form': form})


@login_required
def logout_view(request):
    """Vista de cierre de sesión."""
    logout(request)
    messages.info(request, 'Ha cerrado sesión correctamente.')
    return redirect('login')


@login_required
def dashboard_view(request):
    """Vista del panel principal después del login."""
    # Estadísticas del sistema
    total_concejales = Concejal.objects.count()
    total_concejales_activos = Concejal.objects.filter(estado=Concejal.ESTADO_ACTIVO).count()
    total_personal = PersonalDespacho.objects.count()
    total_personal_activo = PersonalDespacho.objects.filter(estado=PersonalDespacho.ESTADO_ACTIVO).count()
    limite_personal = Concejal.LIMITE_PERSONAL_DESPACHO

    context = {
        'total_concejales': total_concejales,
        'total_concejales_activos': total_concejales_activos,
        'total_concejales_inactivos': total_concejales - total_concejales_activos,
        'total_personal': total_personal,
        'total_personal_activo': total_personal_activo,
        'total_personal_inactivo': total_personal - total_personal_activo,
        'limite_personal': limite_personal,
    }
    return render(request, 'autenticacion/dashboard.html', context)


@require_http_methods(['GET', 'POST'])
def recuperar_contrasena_view(request):
    """Paso 1: Solicitar recuperación de contraseña con el correo."""
    form = RecuperarContrasenaForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        usuario = form.get_usuario()
        if usuario:
            # Guardar el email en la sesión para el siguiente paso
            request.session['recuperar_email'] = usuario.email
            return redirect('pregunta_seguridad')

    return render(request, 'autenticacion/recuperar_contrasena.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def pregunta_seguridad_view(request):
    """Paso 2: Responder la pregunta de seguridad."""
    email = request.session.get('recuperar_email')
    if not email:
        messages.warning(request, 'Debe iniciar el proceso de recuperación primero.')
        return redirect('recuperar_contrasena')

    try:
        usuario = Usuario.objects.get(email__iexact=email)
    except Usuario.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('recuperar_contrasena')

    if not usuario.pregunta_seguridad:
        messages.error(
            request,
            'Este usuario no tiene configurada una pregunta de seguridad. '
            'Contacte al administrador.'
        )
        return redirect('recuperar_contrasena')

    # Obtener el texto de la pregunta
    pregunta_texto = dict(Usuario.PREGUNTAS_SEGURIDAD).get(usuario.pregunta_seguridad, '')

    form = PreguntaSeguridadForm(request.POST or None, usuario=usuario)

    if request.method == 'POST' and form.is_valid():
        # Respuesta correcta, pasar al siguiente paso
        return redirect('nueva_contrasena')

    return render(request, 'autenticacion/pregunta_seguridad.html', {
        'form': form,
        'pregunta_texto': pregunta_texto,
        'usuario': usuario,
    })


@require_http_methods(['GET', 'POST'])
def nueva_contrasena_view(request):
    """Paso 3: Establecer una nueva contraseña."""
    email = request.session.get('recuperar_email')
    if not email:
        messages.warning(request, 'Debe iniciar el proceso de recuperación primero.')
        return redirect('recuperar_contrasena')

    try:
        usuario = Usuario.objects.get(email__iexact=email)
    except Usuario.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('recuperar_contrasena')

    form = NuevaContrasenaForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        nueva_contrasena = form.cleaned_data['nueva_contrasena']
        usuario.set_password(nueva_contrasena)
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.save()

        # Limpiar la sesión de recuperación
        request.session.pop('recuperar_email', None)

        messages.success(
            request,
            '¡Contraseña actualizada correctamente! Ya puede iniciar sesión.'
        )
        return redirect('login')

    return render(request, 'autenticacion/nueva_contrasena.html', {'form': form})
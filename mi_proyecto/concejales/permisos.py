"""Helpers y decoradores de permisos por rol del sistema.

Roles definidos en autenticacion.Usuario.ROLES:

    - administrador: permisos totales (todo el sistema).
    - concejal: gestiona SOLO el personal de despacho de su propio despacho.
      No puede ver información de otros concejales.
    - despacho (Personal de Despacho): SOLO lectura, únicamente puede ver
      quiénes comparten el despacho de su concejal (no de otros concejales).
"""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def es_administrador(user):
    """True si el usuario es administrador (permisos totales)."""
    return user.is_authenticated and user.es_administrador


def es_concejal(user):
    """True si el usuario tiene rol Concejal."""
    return user.is_authenticated and user.es_concejal


def es_despacho(user):
    """True si el usuario tiene rol Personal de Despacho."""
    return user.is_authenticated and user.es_despacho


def get_concejal_de_usuario(user):
    """Devuelve el Concejal asociado al usuario (concejal o despacho), o None."""
    if not user.is_authenticated:
        return None
    return user.get_concejal()


def puede_ver_concejal(user, concejal):
    """El administrador ve todo; concejal/despacho solo su propio concejal."""
    if not user.is_authenticated or concejal is None:
        return False
    if es_administrador(user):
        return True
    return get_concejal_de_usuario(user) == concejal


def puede_gestionar_personal(user):
    """Pueden gestionar personal: administrador y concejal (solo su despacho)."""
    return es_administrador(user) or es_concejal(user)


def puede_gestionar_personal_de(user, personal):
    """Puede gestionar este personal: admin (todos) o concejal de su despacho."""
    if not user.is_authenticated or personal is None:
        return False
    if es_administrador(user):
        return True
    if es_concejal(user):
        return get_concejal_de_usuario(user) == personal.concejal
    return False


def administrador_required(view_func):
    """Solo el administrador puede acceder a la vista."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not es_administrador(request.user):
            messages.error(
                request,
                'No tiene permisos para realizar esta acción. '
                'Solo el administrador puede acceder aquí.'
            )
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


def concejal_o_administrador_required(view_func):
    """Solo el administrador o un concejal pueden acceder a la vista."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (es_administrador(request.user) or es_concejal(request.user)):
            messages.error(
                request,
                'No tiene permisos para realizar esta acción. '
                'Solo el concejal o el administrador pueden acceder aquí.'
            )
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped

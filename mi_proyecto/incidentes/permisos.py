"""Helpers de permisos para el módulo de incidentes.

Reglas:
    - Administrador: permisos totales (crear, editar, eliminar, estado).
    - Concejal: SOLO consulta los incidentes de su propio despacho.
    - Personal de Despacho: SOLO consulta los incidentes de su propio despacho.
"""
from concejales.permisos import es_administrador, get_concejal_de_usuario

from .models import Incidente


def puede_ver_incidente(user, incidente):
    """Verifica si el usuario puede ver un incidente según su rol."""
    if not user.is_authenticated or incidente is None:
        return False
    if es_administrador(user):
        return True
    concejal = get_concejal_de_usuario(user)
    if concejal is None:
        return False
    # El incidente es del propio concejal o de su personal de despacho
    if incidente.concejal_id == concejal.pk:
        return True
    if (
        incidente.personal_despacho_id
        and incidente.personal_despacho.concejal_id == concejal.pk
    ):
        return True
    return False


def puede_registrar_incidente(user):
    """Solo el administrador puede registrar incidentes."""
    return es_administrador(user)


def puede_editar_incidente(user):
    """Solo el administrador puede editar incidentes."""
    return es_administrador(user)


def puede_eliminar_incidente(user):
    """Solo el administrador puede eliminar incidentes."""
    return es_administrador(user)


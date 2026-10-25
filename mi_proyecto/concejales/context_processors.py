"""Context processor que expone el rol del usuario y su concejal a todas las plantillas."""

from .permisos import es_administrador, get_concejal_de_usuario


def permisos_roles(request):
    """Añade variables de rol al contexto de cada plantilla.

    Variables disponibles en las plantillas:
        - es_administrador (bool)
        - es_concejal (bool)
        - es_despacho (bool)
        - mi_concejal (Concejal o None): concejal asociado al usuario.
    """
    contexto = {
        'es_administrador': False,
        'es_concejal': False,
        'es_despacho': False,
        'mi_concejal': None,
    }
    user = request.user
    if user.is_authenticated:
        contexto['es_administrador'] = es_administrador(user)
        contexto['es_concejal'] = user.es_concejal
        contexto['es_despacho'] = user.es_despacho
        contexto['mi_concejal'] = get_concejal_de_usuario(user)
    return contexto

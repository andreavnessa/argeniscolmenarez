from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from concejales.models import Concejal, PersonalDespacho
from concejales.permisos import administrador_required, get_concejal_de_usuario

from .forms import IncidenteForm
from .models import Incidente
from .permisos import puede_ver_incidente


def _filtrar_por_despacho(request, qs):
    """Restringe el queryset al despacho del usuario (concejal o personal)."""
    if request.user.es_administrador:
        return qs, None
    concejal = get_concejal_de_usuario(request.user)
    if concejal is None:
        return qs.none(), None
    return qs.filter(
        Q(concejal_id=concejal.pk)
        | Q(personal_despacho__concejal_id=concejal.pk)
    ), concejal


@login_required
@require_http_methods(['GET'])
def lista_incidentes_view(request):
    """Lista de incidentes/permisos.

    - Administrador: ve todos los incidentes.
    - Concejal / Personal de Despacho: solo los de su propio despacho.
    """
    query = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    afectado = request.GET.get('afectado', '').strip()

    qs, mi_concejal = _filtrar_por_despacho(request, Incidente.objects.select_related(
        'concejal', 'personal_despacho', 'personal_despacho__concejal', 'registrado_por'
    ))
    # Conjunto base para estadísticas (antes de aplicar los filtros de la barra)
    base_qs = qs


    if query:
        qs = qs.filter(
            Q(concejal__nombres__icontains=query)
            | Q(concejal__apellidos__icontains=query)
            | Q(personal_despacho__nombres__icontains=query)
            | Q(personal_despacho__apellidos__icontains=query)
            | Q(motivo__icontains=query)
        )
    if estado:
        qs = qs.filter(estado=estado)
    if tipo:
        qs = qs.filter(tipo_permiso=tipo)
    if afectado:
        qs = qs.filter(afectado_tipo=afectado)

    # Paginación
    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Estadísticas (sobre el conjunto visible según el rol del usuario)
    total_incidentes = base_qs.count()
    total_pendientes = base_qs.filter(estado=Incidente.ESTADO_PENDIENTE).count()
    total_aprobados = base_qs.filter(estado=Incidente.ESTADO_APROBADO).count()
    total_rechazados = base_qs.filter(estado=Incidente.ESTADO_RECHAZADO).count()


    context = {
        'incidentes': page_obj.object_list,
        'total_incidentes': total_incidentes,
        'total_pendientes': total_pendientes,
        'total_aprobados': total_aprobados,
        'total_rechazados': total_rechazados,

        'page_obj': page_obj,
        'query': query,
        'estado': estado,
        'tipo': tipo,
        'afectado': afectado,
        'estados': Incidente.ESTADOS,
        'tipos_permiso': Incidente.TIPOS_PERMISO,
        'afectado_tipos': Incidente.AFECTADO_TIPOS,
    }
    return render(request, 'incidentes/lista_incidentes.html', context)


@login_required
@require_http_methods(['GET'])
def detalle_incidente_view(request, pk):
    """Detalle de un incidente (solo lectura para concejal/despacho)."""
    incidente = get_object_or_404(
        Incidente.objects.select_related(
            'concejal', 'personal_despacho', 'personal_despacho__concejal', 'registrado_por'
        ),
        pk=pk,
    )

    if not puede_ver_incidente(request.user, incidente):
        messages.error(
            request,
            'No tiene permisos para ver este incidente. '
            'Solo puede consultar los incidentes de su propio despacho.'
        )
        return redirect('lista_incidentes')

    context = {'incidente': incidente}
    return render(request, 'incidentes/detalle_incidente.html', context)


@login_required
@administrador_required
@require_http_methods(['GET', 'POST'])
def crear_incidente_view(request):
    """Vista para registrar un nuevo incidente/permiso. Solo administrador."""
    form = IncidenteForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        incidente = form.save(commit=False)
        incidente.registrado_por = request.user
        incidente.save()
        messages.success(
            request,
            f'Incidente registrado correctamente para {incidente.get_afectado_nombre()}.'
        )
        return redirect('detalle_incidente', pk=incidente.pk)

    context = {
        'form': form,
        'titulo': 'Registrar Incidente / Permiso',
        'es_edicion': False,
    }
    return render(request, 'incidentes/form_incidente.html', context)


@login_required
@administrador_required
@require_http_methods(['GET', 'POST'])
def editar_incidente_view(request, pk):
    """Vista para editar un incidente/permiso. Solo administrador."""
    incidente = get_object_or_404(Incidente, pk=pk)
    form = IncidenteForm(request.POST or None, instance=incidente)

    if request.method == 'POST' and form.is_valid():
        incidente = form.save()
        messages.success(
            request,
            f'Incidente de {incidente.get_afectado_nombre()} actualizado correctamente.'
        )
        return redirect('detalle_incidente', pk=incidente.pk)

    context = {
        'form': form,
        'incidente': incidente,
        'titulo': 'Editar Incidente / Permiso',
        'es_edicion': True,
    }
    return render(request, 'incidentes/form_incidente.html', context)


@login_required
@administrador_required
@require_http_methods(['POST'])
def cambiar_estado_incidente_view(request, pk):
    """Vista para cambiar el estado de un incidente. Solo administrador."""
    incidente = get_object_or_404(Incidente, pk=pk)
    nuevo_estado = request.POST.get('estado', '').strip()

    estados_validos = dict(Incidente.ESTADOS)
    if nuevo_estado not in estados_validos:
        messages.warning(request, 'El estado seleccionado no es válido.')
        return redirect('detalle_incidente', pk=incidente.pk)

    if nuevo_estado == incidente.estado:
        messages.warning(request, 'El incidente ya se encuentra en ese estado.')
        return redirect('detalle_incidente', pk=incidente.pk)

    incidente.estado = nuevo_estado
    incidente.save(update_fields=['estado', 'updated_at'])
    messages.success(
        request,
        f'El incidente pasó a estado "{estados_validos[nuevo_estado]}".'
    )
    return redirect('detalle_incidente', pk=incidente.pk)


@login_required
@administrador_required
@require_http_methods(['POST'])
def eliminar_incidente_view(request, pk):
    """Vista para eliminar un incidente/permiso. Solo administrador."""
    incidente = get_object_or_404(Incidente, pk=pk)
    nombre = incidente.get_afectado_nombre()
    incidente.delete()
    messages.success(request, f'El incidente de {nombre} fue eliminado correctamente.')
    return redirect('lista_incidentes')


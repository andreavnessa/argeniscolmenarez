from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from concejales.models import Concejal, PersonalDespacho
from concejales.permisos import administrador_required, get_concejal_de_usuario

from .forms import AsistenciaForm
from .models import Asistencia


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


def _parsear_afectado(codigo):
    """Convierte 'concejal:<uuid>' o 'personal:<uuid>' en (tipo, pk)."""
    codigo = (codigo or '').strip()
    tipo, sep, pk = codigo.rpartition(':')
    if not sep or not tipo or not pk:
        return None, None
    return tipo, pk


@login_required
@require_http_methods(['GET'])
def lista_asistencia_view(request):
    """Lista de registros de asistencia.

    - Administrador: ve todos los registros y puede marcar entrada/salida.
    - Concejal / Personal de Despacho: solo los de su propio despacho (lectura).
    """
    query = request.GET.get('q', '').strip()
    fecha = request.GET.get('fecha', '').strip()
    afectado = request.GET.get('afectado', '').strip()

    base_qs, _ = _filtrar_por_despacho(request, Asistencia.objects.select_related(
        'concejal', 'personal_despacho', 'personal_despacho__concejal', 'registrado_por'
    ))
    qs = base_qs

    if query:
        qs = qs.filter(
            Q(concejal__nombres__icontains=query)
            | Q(concejal__apellidos__icontains=query)
            | Q(personal_despacho__nombres__icontains=query)
            | Q(personal_despacho__apellidos__icontains=query)
        )
    if fecha:
        qs = qs.filter(fecha=fecha)
    if afectado:
        qs = qs.filter(afectado_tipo=afectado)

    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    hoy = timezone.localdate()
    asistencias_hoy = base_qs.filter(fecha=hoy)

    context = {
        'asistencias': page_obj.object_list,
        'page_obj': page_obj,
        'query': query,
        'fecha': fecha,
        'afectado': afectado,
        'afectado_tipos': Asistencia.AFECTADO_TIPOS,
        'concejales': Concejal.objects.filter(
            estado=Concejal.ESTADO_ACTIVO
        ).order_by('apellidos', 'nombres'),
        'personal': PersonalDespacho.objects.filter(
            estado=PersonalDespacho.ESTADO_ACTIVO
        ).select_related('concejal').order_by('apellidos', 'nombres'),
        'hoy': hoy,
        'asistencias_hoy': asistencias_hoy,
    }
    return render(request, 'asistencia/lista_asistencia.html', context)


@login_required
@administrador_required
@require_http_methods(['POST'])
def marcar_entrada_view(request):
    """Marca la entrada (hora actual) del afectado seleccionado para hoy."""
    tipo, pk = _parsear_afectado(request.POST.get('afectado', ''))
    if not tipo or not pk:
        messages.warning(request, 'Debe seleccionar un concejal o personal de despacho.')
        return redirect('lista_asistencia')

    hoy = timezone.localdate()
    ahora = timezone.localtime().time()

    if tipo == 'concejal':
        afectado = get_object_or_404(Concejal, pk=pk)
        registro, _ = Asistencia.objects.get_or_create(
            fecha=hoy, concejal=afectado,
            defaults={
                'afectado_tipo': Asistencia.AFECTADO_CONCEJAL,
                'registrado_por': request.user,
                'hora_entrada': ahora,
            },
        )
    else:
        afectado = get_object_or_404(PersonalDespacho, pk=pk)
        registro, _ = Asistencia.objects.get_or_create(
            fecha=hoy, personal_despacho=afectado,
            defaults={
                'afectado_tipo': Asistencia.AFECTADO_PERSONAL,
                'registrado_por': request.user,
                'hora_entrada': ahora,
            },
        )

    if registro.hora_entrada is None:
        registro.hora_entrada = ahora
        registro.save(update_fields=['hora_entrada', 'updated_at'])
        messages.success(
            request,
            f'Entrada registrada para {afectado.get_nombre_completo()} a las {ahora:%H:%M}.'
        )
    else:
        messages.info(
            request,
            f'{afectado.get_nombre_completo()} ya tiene entrada registrada a las '
            f'{registro.hora_entrada:%H:%M}.'
        )
    return redirect('lista_asistencia')


@login_required
@administrador_required
@require_http_methods(['POST'])
def marcar_salida_view(request):
    """Marca la salida (hora actual) del afectado seleccionado para hoy."""
    tipo, pk = _parsear_afectado(request.POST.get('afectado', ''))
    if not tipo or not pk:
        messages.warning(request, 'Debe seleccionar un concejal o personal de despacho.')
        return redirect('lista_asistencia')

    hoy = timezone.localdate()
    ahora = timezone.localtime().time()

    try:
        if tipo == 'concejal':
            registro = Asistencia.objects.get(fecha=hoy, concejal_id=pk)
        else:
            registro = Asistencia.objects.get(fecha=hoy, personal_despacho_id=pk)
        afectado = registro.get_afectado()
    except Asistencia.DoesNotExist:
        messages.warning(
            request,
            'No hay entrada registrada hoy para esta persona. Registre la entrada primero.'
        )
        return redirect('lista_asistencia')

    if registro.hora_entrada is None:
        messages.warning(request, 'Registre primero la entrada.')
        return redirect('lista_asistencia')

    if registro.hora_salida is not None:
        messages.info(
            request,
            f'{afectado.get_nombre_completo()} ya tiene salida a las {registro.hora_salida:%H:%M}.'
        )
        return redirect('lista_asistencia')

    registro.hora_salida = ahora
    registro.save(update_fields=['hora_salida', 'updated_at'])
    messages.success(
        request,
        f'Salida registrada para {afectado.get_nombre_completo()} a las {ahora:%H:%M}.'
    )
    return redirect('lista_asistencia')


@login_required
@administrador_required
@require_http_methods(['GET', 'POST'])
def crear_asistencia_view(request):
    """Registro manual de asistencia (fechas pasadas o correcciones). Solo admin."""
    form = AsistenciaForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        asistencia = form.save(commit=False)
        asistencia.registrado_por = request.user
        asistencia.save()
        messages.success(
            request,
            f'Asistencia de {asistencia.get_afectado_nombre()} guardada correctamente.'
        )
        return redirect('lista_asistencia')

    context = {
        'form': form,
        'titulo': 'Registrar Asistencia',
    }
    return render(request, 'asistencia/form_asistencia.html', context)


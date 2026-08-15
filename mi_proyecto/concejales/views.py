from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import ConcejalForm, PersonalDespachoForm, ReasignarPersonalForm
from .models import Concejal, PersonalDespacho


@login_required
@require_http_methods(['GET'])
def lista_concejales_view(request):
    """Vista para listar concejales con filtros y paginación."""
    query = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()

    concejales_qs = Concejal.objects.annotate(
        conteo_personal=Count(
            'personal_despacho',
            filter=Q(personal_despacho__estado=PersonalDespacho.ESTADO_ACTIVO),
            distinct=True,
        )
    ).order_by('apellidos', 'nombres')

    if query:
        concejales_qs = concejales_qs.filter(
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(cedula__icontains=query)
        )

    if estado:
        concejales_qs = concejales_qs.filter(estado=estado)

    # Estadísticas
    total_concejales = Concejal.objects.count()
    total_activos = Concejal.objects.filter(estado=Concejal.ESTADO_ACTIVO).count()
    total_inactivos = Concejal.objects.filter(estado=Concejal.ESTADO_INACTIVO).count()

    # Paginación
    paginator = Paginator(concejales_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    concejales = page_obj.object_list

    context = {
        'concejales': concejales,
        'page_obj': page_obj,
        'query': query,
        'estado': estado,
        'total_concejales': total_concejales,
        'total_activos': total_activos,
        'total_inactivos': total_inactivos,
        'limite_personal': Concejal.LIMITE_PERSONAL_DESPACHO,
    }
    return render(request, 'concejales/lista_concejales.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def crear_concejal_view(request):
    """Vista para crear un nuevo concejal."""
    form = ConcejalForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        concejal = form.save()
        messages.success(
            request,
            f'Concejal {concejal.get_nombre_completo()} registrado correctamente.'
        )
        return redirect('detalle_concejal', pk=concejal.pk)

    context = {
        'form': form,
        'titulo': 'Registrar Concejal',
        'es_edicion': False,
    }
    return render(request, 'concejales/form_concejal.html', context)


@login_required
@require_http_methods(['GET'])
def detalle_concejal_view(request, pk):
    """Vista de detalle de un concejal y su equipo de despacho."""
    concejal = get_object_or_404(Concejal, pk=pk)

    personal_activo = concejal.get_personal_activo()
    personal_inactivo = concejal.personal_despacho.filter(
        estado=PersonalDespacho.ESTADO_INACTIVO
    )

    context = {
        'concejal': concejal,
        'conteo_personal_activo': concejal.get_conteo_personal_activo(),
        'conteo_personal_total': concejal.get_conteo_personal_total(),
        'personal_restante': concejal.get_personal_restante(),
        'limite_personal': Concejal.LIMITE_PERSONAL_DESPACHO,
        'puede_agregar_personal': concejal.puede_agregar_personal(),
        'personal_activo': personal_activo,
        'personal_inactivo': personal_inactivo,
    }
    return render(request, 'concejales/detalle_concejal.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def editar_concejal_view(request, pk):
    """Vista para editar un concejal existente."""
    concejal = get_object_or_404(Concejal, pk=pk)
    form = ConcejalForm(request.POST or None, request.FILES or None, instance=concejal)

    if request.method == 'POST' and form.is_valid():
        concejal = form.save()
        messages.success(
            request,
            f'Concejal {concejal.get_nombre_completo()} actualizado correctamente.'
        )
        return redirect('detalle_concejal', pk=concejal.pk)

    context = {
        'form': form,
        'titulo': 'Editar Concejal',
        'es_edicion': True,
        'concejal': concejal,
    }
    return render(request, 'concejales/form_concejal.html', context)


@login_required
@require_http_methods(['POST'])
def desactivar_concejal_view(request, pk):
    """Vista para desactivar un concejal y su personal de despacho."""
    concejal = get_object_or_404(Concejal, pk=pk)

    if concejal.estado == Concejal.ESTADO_ACTIVO:
        concejal.estado = Concejal.ESTADO_INACTIVO
        concejal.save(update_fields=['estado', 'updated_at'])

        # Desactivar también el personal de despacho activo
        personal_activo = concejal.get_personal_activo()
        personal_activo.update(estado=PersonalDespacho.ESTADO_INACTIVO)

        messages.success(
            request,
            f'Concejal {concejal.get_nombre_completo()} desactivado. '
            'Su personal de despacho también fue desactivado.'
        )
    else:
        messages.warning(request, 'El concejal ya está desactivado.')

    return redirect('lista_concejales')


@login_required
@require_http_methods(['POST'])
def activar_concejal_view(request, pk):
    """Vista para activar un concejal."""
    concejal = get_object_or_404(Concejal, pk=pk)

    if concejal.estado == Concejal.ESTADO_INACTIVO:
        concejal.estado = Concejal.ESTADO_ACTIVO
        concejal.save(update_fields=['estado', 'updated_at'])
        messages.success(
            request,
            f'Concejal {concejal.get_nombre_completo()} activado correctamente.'
        )
    else:
        messages.warning(request, 'El concejal ya está activo.')

    return redirect('lista_concejales')


@login_required
@require_http_methods(['GET'])
def lista_personal_view(request):
    """Vista para listar el personal de despacho con filtros y paginación."""
    query = request.GET.get('q', '').strip()
    concejal_id = request.GET.get('concejal', '').strip()
    cargo = request.GET.get('cargo', '').strip()
    estado = request.GET.get('estado', '').strip()

    personal_qs = PersonalDespacho.objects.select_related('concejal').all().order_by(
        'apellidos', 'nombres'
    )

    if query:
        personal_qs = personal_qs.filter(
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(cedula__icontains=query)
        )

    if concejal_id:
        personal_qs = personal_qs.filter(concejal_id=concejal_id)

    if cargo:
        personal_qs = personal_qs.filter(cargo=cargo)

    if estado:
        personal_qs = personal_qs.filter(estado=estado)

    # Paginación
    paginator = Paginator(personal_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    personal = page_obj.object_list

    context = {
        'personal': personal,
        'page_obj': page_obj,
        'query': query,
        'concejal_id': concejal_id,
        'cargo': cargo,
        'estado': estado,
        'concejales': Concejal.objects.all().order_by('apellidos', 'nombres'),
        'cargos': PersonalDespacho.CARGOS,
    }
    return render(request, 'concejales/lista_personal.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def crear_personal_view(request):
    """Vista para crear un nuevo miembro del personal de despacho."""
    form = PersonalDespachoForm(request.POST or None, request.FILES or None)

    # Pre-seleccionar concejal si viene por parámetro
    if request.method == 'GET':
        concejal_id = request.GET.get('concejal')
        if concejal_id and not form.fields['concejal'].initial:
            try:
                concejal = Concejal.objects.get(pk=concejal_id)
                form.fields['concejal'].initial = concejal.pk
            except (Concejal.DoesNotExist, ValueError):
                pass

    if request.method == 'POST' and form.is_valid():
        personal = form.save()
        messages.success(
            request,
            f'{personal.get_nombre_completo()} registrado en el despacho de '
            f'{personal.concejal.get_nombre_completo()}.'
        )
        return redirect('detalle_concejal', pk=personal.concejal_id)

    context = {
        'form': form,
        'titulo': 'Registrar Personal de Despacho',
        'es_edicion': False,
    }
    return render(request, 'concejales/form_personal.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def editar_personal_view(request, pk):
    """Vista para editar un miembro del personal de despacho."""
    personal = get_object_or_404(PersonalDespacho, pk=pk)
    form = PersonalDespachoForm(
        request.POST or None,
        request.FILES or None,
        instance=personal,
    )

    if request.method == 'POST' and form.is_valid():
        personal = form.save()
        messages.success(
            request,
            f'{personal.get_nombre_completo()} actualizado correctamente.'
        )
        return redirect('detalle_concejal', pk=personal.concejal_id)

    context = {
        'form': form,
        'titulo': 'Editar Personal de Despacho',
        'es_edicion': True,
        'personal': personal,
    }
    return render(request, 'concejales/form_personal.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def reasignar_personal_view(request, pk):
    """Vista para reasignar personal a otro concejal."""
    personal = get_object_or_404(PersonalDespacho, pk=pk)
    form = ReasignarPersonalForm(request.POST or None, instance=personal)

    if request.method == 'POST' and form.is_valid():
        nuevo_concejal = form.cleaned_data['concejal']
        concejal_anterior = personal.concejal
        personal = form.save()

        if concejal_anterior.pk != nuevo_concejal.pk:
            messages.success(
                request,
                f'{personal.get_nombre_completo()} reasignado del despacho de '
                f'{concejal_anterior.get_nombre_completo()} al despacho de '
                f'{nuevo_concejal.get_nombre_completo()}.'
            )
        return redirect('detalle_concejal', pk=personal.concejal_id)

    context = {
        'form': form,
        'personal': personal,
    }
    return render(request, 'concejales/form_reasignar.html', context)


@login_required
@require_http_methods(['POST'])
def desactivar_personal_view(request, pk):
    """Vista para desactivar un miembro del personal de despacho."""
    personal = get_object_or_404(PersonalDespacho, pk=pk)

    if personal.estado == PersonalDespacho.ESTADO_ACTIVO:
        personal.estado = PersonalDespacho.ESTADO_INACTIVO
        personal.save(update_fields=['estado', 'updated_at'])
        messages.success(
            request,
            f'{personal.get_nombre_completo()} desactivado del despacho.'
        )
    else:
        messages.warning(request, 'El miembro del personal ya está desactivado.')

    return redirect('detalle_concejal', pk=personal.concejal_id)


@login_required
@require_http_methods(['POST'])
def activar_personal_view(request, pk):
    """Vista para activar un miembro del personal de despacho."""
    personal = get_object_or_404(PersonalDespacho, pk=pk)

    if personal.estado == PersonalDespacho.ESTADO_INACTIVO:
        # Verificar límite de personal en el despacho antes de activar
        if not personal.concejal.puede_agregar_personal():
            messages.error(
                request,
                f'El despacho de {personal.concejal.get_nombre_completo()} está al límite. '
                'No puede activar más personal.'
            )
            return redirect('detalle_concejal', pk=personal.concejal_id)

        personal.estado = PersonalDespacho.ESTADO_ACTIVO
        personal.save(update_fields=['estado', 'updated_at'])
        messages.success(
            request,
            f'{personal.get_nombre_completo()} activado en el despacho.'
        )
    else:
        messages.warning(request, 'El miembro del personal ya está activo.')

    return redirect('detalle_concejal', pk=personal.concejal_id)
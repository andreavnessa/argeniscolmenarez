import csv
import io
from collections import Counter
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from asistencia.models import Asistencia
from concejales.models import Concejal, PersonalDespacho
from concejales.permisos import get_concejal_de_usuario
from incidentes.models import Incidente


def _formatear_minutos(total_min):
    h, m = divmod(int(total_min), 60)
    return f'{h}h {m:02d}m'


def _rango_fechas(request):
    """Devuelve (desde, hasta) con valores por defecto razonables."""
    desde = request.GET.get('desde', '').strip()
    hasta = request.GET.get('hasta', '').strip()
    try:
        f_desde = date.fromisoformat(desde)
    except ValueError:
        f_desde = None
    try:
        f_hasta = date.fromisoformat(hasta)
    except ValueError:
        f_hasta = None
    if f_desde is None:
        f_desde = timezone.localdate() - timedelta(days=30)
    if f_hasta is None:
        f_hasta = timezone.localdate()
    if f_desde > f_hasta:
        f_desde, f_hasta = f_hasta, f_desde
    return f_desde, f_hasta


def _despacho_scope(request):
    """Devuelve un Q filtrando al despacho del usuario, o None si es admin."""
    if request.user.es_administrador:
        return None
    concejal = get_concejal_de_usuario(request.user)
    if concejal is None:
        return Q(pk__in=[])
    return Q(concejal_id=concejal.pk) | Q(personal_despacho__concejal_id=concejal.pk)


def _respuesta_csv(nombre_archivo, cabecera, filas):
    """Devuelve un HttpResponse CSV compatible con Excel."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(cabecera)
    for fila in filas:
        writer.writerow(fila)
    buf.seek(0)
    respuesta = HttpResponse('\ufeff' + buf.read(), content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return respuesta


@login_required
@require_http_methods(['GET'])
def panel_reporte_view(request):
    """Panel principal de reportes con accesos rápidos."""
    scope = _despacho_scope(request)
    asistencias = Asistencia.objects.all()
    incidentes = Incidente.objects.all()
    if scope is not None:
        asistencias = asistencias.filter(scope)
        incidentes = incidentes.filter(scope)

    context = {
        'total_asistencias': asistencias.count(),
        'total_incidentes': incidentes.count(),
        'total_incidentes_pendientes': incidentes.filter(
            estado=Incidente.ESTADO_PENDIENTE
        ).count(),
        'fecha_hoy': timezone.localdate(),
    }
    return render(request, 'reportes/panel.html', context)


@login_required
@require_http_methods(['GET'])
def reporte_asistencia_view(request):
    """Reporte de asistencia por rango de fechas (en pantalla)."""
    desde, hasta = _rango_fechas(request)
    q = request.GET.get('q', '').strip()
    afectado = request.GET.get('afectado', '').strip()

    qs = Asistencia.objects.filter(fecha__range=(desde, hasta)).select_related(
        'concejal', 'personal_despacho', 'personal_despacho__concejal', 'registrado_por'
    )
    scope = _despacho_scope(request)
    if scope is not None:
        qs = qs.filter(scope)
    if q:
        qs = qs.filter(
            Q(concejal__nombres__icontains=q)
            | Q(concejal__apellidos__icontains=q)
            | Q(personal_despacho__nombres__icontains=q)
            | Q(personal_despacho__apellidos__icontains=q)
        )
    if afectado:
        qs = qs.filter(afectado_tipo=afectado)

    registros = list(qs.order_by('fecha', 'afectado_tipo'))
    total_entradas = sum(1 for r in registros if r.hora_entrada)
    total_salidas = sum(1 for r in registros if r.hora_salida)
    total_minutos = 0
    resumen = {}
    for r in registros:
        nombre = r.get_afectado_nombre()
        datos = resumen.setdefault(nombre, {
            'dias': 0, 'minutos': 0, 'tipo': r.get_afectado_tipo_display(),
        })
        datos['dias'] += 1
        duracion = r.get_duracion()
        if duracion:
            m = int(duracion.total_seconds() // 60)
            datos['minutos'] += m
            total_minutos += m
    for _nombre, datos in resumen.items():
        datos['tiempo'] = _formatear_minutos(datos['minutos'])
    resumen = sorted(resumen.items(), key=lambda kv: -kv[1]['minutos'])

    context = {
        'registros': registros,
        'resumen': resumen,
        'desde': desde,
        'hasta': hasta,
        'q': q,
        'afectado': afectado,
        'afectado_tipos': Asistencia.AFECTADO_TIPOS,
        'total_registros': len(registros),
        'total_entradas': total_entradas,
        'total_salidas': total_salidas,
        'total_horas': _formatear_minutos(total_minutos),
    }
    return render(request, 'reportes/reporte_asistencia.html', context)


@login_required
@require_http_methods(['GET'])
def reporte_asistencia_csv_view(request):
    """Reporte de asistencia descargable en CSV (Excel)."""
    desde, hasta = _rango_fechas(request)
    q = request.GET.get('q', '').strip()
    afectado = request.GET.get('afectado', '').strip()

    qs = Asistencia.objects.filter(fecha__range=(desde, hasta)).select_related(
        'concejal', 'personal_despacho', 'personal_despacho__concejal'
    )
    scope = _despacho_scope(request)
    if scope is not None:
        qs = qs.filter(scope)
    if q:
        qs = qs.filter(
            Q(concejal__nombres__icontains=q)
            | Q(concejal__apellidos__icontains=q)
            | Q(personal_despacho__nombres__icontains=q)
            | Q(personal_despacho__apellidos__icontains=q)
        )
    if afectado:
        qs = qs.filter(afectado_tipo=afectado)

    filas = []
    for r in qs.order_by('fecha', 'afectado_tipo'):
        filas.append([
            r.fecha.isoformat(),
            r.get_afectado_nombre(),
            r.get_afectado_tipo_display(),
            r.hora_entrada.strftime('%H:%M') if r.hora_entrada else '',
            r.hora_salida.strftime('%H:%M') if r.hora_salida else '',
            r.get_duracion_horas(),
        ])
    nombre = f'asistencia_{desde.isoformat()}_{hasta.isoformat()}.csv'
    cabecera = ['Fecha', 'Afectado', 'Tipo', 'Entrada', 'Salida', 'Duracion']
    return _respuesta_csv(nombre, cabecera, filas)

@login_required
@require_http_methods(['GET'])
def reporte_incidencias_csv_view(request):
    """Reporte de incidencias descargable en CSV (Excel)."""
    desde, hasta = _rango_fechas(request)
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    estado = request.GET.get('estado', '').strip()

    qs = Incidente.objects.filter(fecha_inicio__range=(desde, hasta)).select_related(
        'concejal', 'personal_despacho', 'personal_despacho__concejal'
    )
    scope = _despacho_scope(request)
    if scope is not None:
        qs = qs.filter(scope)
    if q:
        qs = qs.filter(
            Q(concejal__nombres__icontains=q)
            | Q(concejal__apellidos__icontains=q)
            | Q(personal_despacho__nombres__icontains=q)
            | Q(personal_despacho__apellidos__icontains=q)
            | Q(motivo__icontains=q)
        )
    if tipo:
        qs = qs.filter(tipo_permiso=tipo)
    if estado:
        qs = qs.filter(estado=estado)

    filas = []
    for r in qs.order_by('fecha_inicio'):
        filas.append([
            r.fecha_inicio.isoformat(),
            r.get_afectado_nombre(),
            r.get_afectado_tipo_display(),
            r.get_tipo_permiso_display(),
            r.motivo,
            r.get_estado_display(),
            r.fecha_fin.isoformat() if r.fecha_fin else '',
            r.registrado_por.get_full_name() if r.registrado_por else '',
        ])
    nombre = f'incidencias_{desde.isoformat()}_{hasta.isoformat()}.csv'
    cabecera = ['Fecha inicio', 'Afectado', 'Tipo afectado', 'Permiso', 'Motivo', 'Estado', 'Fecha fin', 'Registrado por']
    return _respuesta_csv(nombre, cabecera, filas)


@login_required
@require_http_methods(['GET'])
def reporte_concejales_view(request):
    """Reporte de concejales y personal (en pantalla)."""
    concejales_qs = Concejal.objects.all()
    if not request.user.es_administrador:
        concejal = get_concejal_de_usuario(request.user)
        concejales_qs = Concejal.objects.filter(pk=concejal.pk) if concejal else Concejal.objects.none()

    registros = list(concejales_qs.order_by('apellidos', 'nombres'))
    total = len(registros)
    activos = sum(1 for c in registros if c.estado == Concejal.ESTADO_ACTIVO)
    inactivos = total - activos
    total_personal = sum(c.get_conteo_personal_total() for c in registros)
    total_personal_activo = sum(c.get_conteo_personal_activo() for c in registros)

    por_comision = Counter(c.comision_asignada for c in registros)
    comisiones = [{'comision': k, 'total': v} for k, v in sorted(por_comision.items())]

    por_cargo = Counter(
        PersonalDespacho.objects.filter(
            concejal__in=concejales_qs
        ).values_list('cargo', flat=True)
    )
    cargos = [{'cargo': k, 'total': v} for k, v in sorted(por_cargo.items(), key=lambda x: -x[1])]

    context = {
        'registros': registros,
        'total': total,
        'activos': activos,
        'inactivos': inactivos,
        'total_personal': total_personal,
        'total_personal_activo': total_personal_activo,
        'total_personal_inactivo': total_personal - total_personal_activo,
        'comisiones': comisiones,
        'cargos': cargos,
    }
    return render(request, 'reportes/reporte_concejales.html', context)


@login_required
@require_http_methods(['GET'])
def reporte_concejales_csv_view(request):
    """Reporte de concejales y personal descargable en CSV (Excel)."""
    concejales_qs = Concejal.objects.all()
    if not request.user.es_administrador:
        concejal = get_concejal_de_usuario(request.user)
        concejales_qs = Concejal.objects.filter(pk=concejal.pk) if concejal else Concejal.objects.none()

    filas = []
    for c in concejales_qs.order_by('apellidos', 'nombres'):
        filas.append([
            c.get_nombre_completo(),
            c.cedula,
            c.comision_asignada,
            c.estado,
            c.get_conteo_personal_activo(),
            c.get_conteo_personal_total(),
        ])
    nombre = f'concejales_{timezone.localdate().isoformat()}.csv'
    cabecera = ['Concejal', 'Cedula', 'Comision', 'Estado', 'Personal activo', 'Personal total']
    return _respuesta_csv(nombre, cabecera, filas)

@login_required
@require_http_methods(['GET'])
def reporte_incidencias_view(request):

    """Reporte de incidencias/permisos por rango de fechas (en pantalla)."""
    desde, hasta = _rango_fechas(request)
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    estado = request.GET.get('estado', '').strip()

    qs = Incidente.objects.filter(fecha_inicio__range=(desde, hasta)).select_related(
        'concejal', 'personal_despacho', 'personal_despacho__concejal', 'registrado_por'
    )
    scope = _despacho_scope(request)
    if scope is not None:
        qs = qs.filter(scope)
    if q:
        qs = qs.filter(
            Q(concejal__nombres__icontains=q)
            | Q(concejal__apellidos__icontains=q)
            | Q(personal_despacho__nombres__icontains=q)
            | Q(personal_despacho__apellidos__icontains=q)
            | Q(motivo__icontains=q)
        )
    if tipo:
        qs = qs.filter(tipo_permiso=tipo)
    if estado:
        qs = qs.filter(estado=estado)

    registros = list(qs.order_by('fecha_inicio'))
    conteo_estado = Counter(r.estado for r in registros)
    conteo_tipo = Counter(r.tipo_permiso for r in registros)
    estados = [{'valor': v, 'etiqueta': lbl, 'total': conteo_estado.get(v, 0)}
               for v, lbl in Incidente.ESTADOS]
    tipos = [{'valor': v, 'etiqueta': lbl, 'total': conteo_tipo.get(v, 0)}
             for v, lbl in Incidente.TIPOS_PERMISO if conteo_tipo.get(v, 0) > 0]

    context = {
        'registros': registros,
        'estados': estados,
        'tipos': tipos,
        'desde': desde,
        'hasta': hasta,
        'q': q,
        'tipo': tipo,
        'estado': estado,
        'tipos_permiso': Incidente.TIPOS_PERMISO,
        'estados_incidente': Incidente.ESTADOS,
        'total': len(registros),
    }
    return render(request, 'reportes/reporte_incidencias.html', context)


from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import text

from src.db import get_engine, run_db_with_retry


@st.cache_data(ttl=300, show_spinner=False)
def rf_get_proveedores() -> pd.DataFrame:
    def _op():
        with get_engine().connect() as conn:
            return pd.read_sql(
                text(
                    """
                    SELECT
                        id_proveedor,
                        ruc,
                        razon_social,
                        rubro_proveedor,
                        contacto,
                        correo
                    FROM dbo.proveedores
                    WHERE activo = 1
                      AND estado <> 'INACTIVO'
                    ORDER BY razon_social
                    """
                ),
                conn,
            )

    return run_db_with_retry(_op)


@st.cache_data(ttl=300, show_spinner=False)
def rf_get_productos_lookup() -> pd.DataFrame:
    def _op():
        with get_engine().connect() as conn:
            return pd.read_sql(
                text(
                    """
                    SELECT
                        p.id_producto,
                        p.sku,
                        p.ean_serie,
                        p.flag_aplica_ean,
                        p.nombre_producto,
                        p.descripcion,
                        p.requiere_lote,
                        p.precio_unitario,
                        p.vida_util_cuenta_dias,
                        c.nombre_categoria,
                        u.id_unidad,
                        u.codigo_unidad,
                        u.nombre_unidad
                    FROM dbo.productos p
                    INNER JOIN dbo.categorias_producto c ON c.id_categoria = p.id_categoria
                    INNER JOIN dbo.unidades_medida u ON u.id_unidad = p.id_unidad
                    WHERE p.activo = 1
                    ORDER BY p.sku
                    """
                ),
                conn,
            )

    return run_db_with_retry(_op)


@st.cache_data(ttl=300, show_spinner=False)
def rf_get_stage_recepcion() -> dict | None:
    def _op():
        with get_engine().connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT TOP 1
                        id_ubicacion,
                        codigo_ubicacion
                    FROM dbo.ubicaciones
                    WHERE codigo_ubicacion = 'B1.RE.01'
                      AND activo = 1
                    """
                )
            ).mappings().first()
            return dict(row) if row else None

    return run_db_with_retry(_op)


@st.cache_data(ttl=180, show_spinner=False)
def rf_get_ubicaciones_activas() -> pd.DataFrame:
    def _op():
        with get_engine().connect() as conn:
            return pd.read_sql(
                text(
                    """
                    SELECT
                        id_ubicacion,
                        codigo_ubicacion,
                        tipo_ubicacion,
                        ISNULL(secuencia, 999999) AS secuencia,
                        ISNULL(es_stage, 0) AS es_stage,
                        ISNULL(es_surtible, 1) AS es_surtible
                    FROM dbo.ubicaciones
                    WHERE activo = 1
                    ORDER BY codigo_ubicacion
                    """
                ),
                conn,
            )

    return run_db_with_retry(_op)


@st.cache_data(ttl=60, show_spinner=False)
def rf_get_stock_consulta(codigo: str = "", ubicacion: str = "") -> pd.DataFrame:
    codigo = str(codigo or "").strip()
    ubicacion = str(ubicacion or "").strip()

    def _op():
        with get_engine().connect() as conn:
            return pd.read_sql(
                text(
                    """
                    SELECT TOP 300
                        p.sku,
                        p.ean_serie,
                        p.nombre_producto,
                        u.codigo_unidad,
                        ub.codigo_ubicacion,
                        su.lote,
                        CAST(su.cantidad_actual AS DECIMAL(18,2)) AS cantidad_actual,
                        CAST(ISNULL(su.cantidad_en_picking, 0) AS DECIMAL(18,2)) AS cantidad_en_picking,
                        CAST(su.cantidad_actual - ISNULL(su.cantidad_en_picking, 0) AS DECIMAL(18,2)) AS cantidad_disponible
                    FROM dbo.stock_ubicacion su
                    INNER JOIN dbo.productos p ON p.id_producto = su.id_producto
                    INNER JOIN dbo.unidades_medida u ON u.id_unidad = p.id_unidad
                    INNER JOIN dbo.ubicaciones ub ON ub.id_ubicacion = su.id_ubicacion
                    WHERE p.activo = 1
                      AND ub.activo = 1
                      AND (su.cantidad_actual > 0 OR ISNULL(su.cantidad_en_picking, 0) > 0)
                      AND (
                            :codigo = ''
                            OR p.sku = :codigo
                            OR p.ean_serie = :codigo
                            OR p.nombre_producto LIKE '%' + :codigo + '%'
                          )
                      AND (
                            :ubicacion = ''
                            OR ub.codigo_ubicacion = :ubicacion
                            OR ub.codigo_ubicacion LIKE '%' + :ubicacion + '%'
                          )
                    ORDER BY ub.codigo_ubicacion, p.sku, su.lote
                    """
                ),
                conn,
                params={"codigo": codigo, "ubicacion": ubicacion},
            )

    return run_db_with_retry(_op)


@st.cache_data(ttl=45, show_spinner=False)
def rf_get_pickings_pendientes() -> pd.DataFrame:
    def _op():
        with get_engine().connect() as conn:
            return pd.read_sql(
                text(
                    """
                    SELECT
                        ph.id_picking,
                        ph.nro_picking,
                        ph.estado,
                        ph.fecha_creacion,
                        CAST(SUM(pd.cantidad_asignada) AS DECIMAL(18,2)) AS cantidad_total,
                        COUNT(*) AS tareas_pendientes,
                        COUNT(DISTINCT pd.id_producto) AS codigos,
                        COUNT(DISTINCT pd.id_ubicacion_origen) AS ubicaciones,
                        CASE
                            WHEN COUNT(DISTINCT pd.id_cuenta) > 1 THEN 'Consolidado'
                            ELSE MAX(c.codigo_cuenta + ' | ' + c.nombre_cuenta)
                        END AS cuenta_logistica,
                        CASE
                            WHEN COUNT(DISTINCT ped.solicitante) > 1 THEN 'Varios solicitantes'
                            ELSE MAX(ISNULL(ped.solicitante, ''))
                        END AS solicitante,
                        MIN(ISNULL(pd.secuencia, 999999)) AS primera_secuencia
                    FROM dbo.picking_header ph
                    INNER JOIN dbo.picking_detalle pd ON pd.id_picking = ph.id_picking
                    INNER JOIN dbo.cuentas_logisticas c ON c.id_cuenta = pd.id_cuenta
                    INNER JOIN dbo.pedidos ped ON ped.id_pedido = pd.id_pedido
                    WHERE pd.estado = 'LIBERADO'
                      AND ph.estado IN ('LIBERADO', 'LIBERADO-CORTO', 'COMPLETADO-PARCIAL')
                    GROUP BY
                        ph.id_picking,
                        ph.nro_picking,
                        ph.estado,
                        ph.fecha_creacion
                    ORDER BY MIN(ISNULL(pd.secuencia, 999999)), ph.fecha_creacion, ph.nro_picking
                    """
                ),
                conn,
            )

    return run_db_with_retry(_op)


@st.cache_data(ttl=20, show_spinner=False)
def rf_get_tareas_picking(id_picking: int) -> pd.DataFrame:
    def _op():
        with get_engine().connect() as conn:
            return pd.read_sql(
                text(
                    """
                    SELECT
                        pd.id_picking_detalle,
                        pd.id_picking,
                        ph.nro_picking,
                        pd.id_pedido,
                        pd.nro_pedido,
                        pd.id_producto,
                        p.sku,
                        p.ean_serie,
                        p.nombre_producto,
                        u.codigo_unidad,
                        u.nombre_unidad,
                        pd.lote,
                        CAST(pd.cantidad_asignada AS DECIMAL(18,2)) AS cantidad_picking,
                        ub.codigo_ubicacion,
                        z.codigo_zona,
                        z.nombre_zona,
                        c.codigo_cuenta,
                        c.nombre_cuenta,
                        ped.solicitante,
                        pd.secuencia,
                        pd.texto_item,
                        pd.estado
                    FROM dbo.picking_detalle pd
                    INNER JOIN dbo.picking_header ph ON ph.id_picking = pd.id_picking
                    INNER JOIN dbo.productos p ON p.id_producto = pd.id_producto
                    INNER JOIN dbo.unidades_medida u ON u.id_unidad = p.id_unidad
                    INNER JOIN dbo.ubicaciones ub ON ub.id_ubicacion = pd.id_ubicacion_origen
                    INNER JOIN dbo.zonas_almacen z ON z.id_zona = ub.id_zona
                    INNER JOIN dbo.cuentas_logisticas c ON c.id_cuenta = pd.id_cuenta
                    INNER JOIN dbo.pedidos ped ON ped.id_pedido = pd.id_pedido
                    WHERE pd.id_picking = :id_picking
                      AND pd.estado = 'LIBERADO'
                    ORDER BY ISNULL(pd.secuencia, 999999), ub.codigo_ubicacion, p.sku, pd.id_picking_detalle
                    """
                ),
                conn,
                params={"id_picking": int(id_picking)},
            )

    return run_db_with_retry(_op)


@st.cache_data(ttl=20, show_spinner=False)
def rf_get_auditoria_picking(id_picking: int) -> pd.DataFrame:
    def _op():
        with get_engine().connect() as conn:
            return pd.read_sql(
                text(
                    """
                    SELECT
                        ph.nro_picking,
                        p.sku,
                        p.nombre_producto,
                        u.codigo_unidad,
                        ub.codigo_ubicacion,
                        pd.lote,
                        CAST(SUM(pd.cantidad_atendida) AS DECIMAL(18,2)) AS cantidad_atendida,
                        COUNT(*) AS tareas
                    FROM dbo.picking_detalle pd
                    INNER JOIN dbo.picking_header ph ON ph.id_picking = pd.id_picking
                    INNER JOIN dbo.productos p ON p.id_producto = pd.id_producto
                    INNER JOIN dbo.unidades_medida u ON u.id_unidad = p.id_unidad
                    LEFT JOIN dbo.ubicaciones ub ON ub.id_ubicacion = pd.id_ubicacion_origen
                    WHERE pd.id_picking = :id_picking
                      AND pd.estado = 'COMPLETADO'
                    GROUP BY
                        ph.nro_picking,
                        p.sku,
                        p.nombre_producto,
                        u.codigo_unidad,
                        ub.codigo_ubicacion,
                        pd.lote
                    ORDER BY ub.codigo_ubicacion, p.sku
                    """
                ),
                conn,
                params={"id_picking": int(id_picking)},
            )

    return run_db_with_retry(_op)


@st.cache_data(ttl=30, show_spinner=False)
def rf_get_stock_por_ubicacion(codigo_ubicacion: str) -> pd.DataFrame:
    codigo_ubicacion = str(codigo_ubicacion or "").strip()

    def _op():
        with get_engine().connect() as conn:
            return pd.read_sql(
                text(
                    """
                    SELECT
                        su.id_stock_ubicacion,
                        ub.id_ubicacion,
                        ub.codigo_ubicacion,
                        p.id_producto,
                        p.sku,
                        p.ean_serie,
                        p.nombre_producto,
                        p.requiere_lote,
                        u.codigo_unidad,
                        su.lote,
                        CAST(su.cantidad_actual AS DECIMAL(18,2)) AS cantidad_actual,
                        CAST(ISNULL(su.cantidad_en_picking, 0) AS DECIMAL(18,2)) AS cantidad_en_picking,
                        CAST(su.cantidad_actual - ISNULL(su.cantidad_en_picking, 0) AS DECIMAL(18,2)) AS cantidad_disponible
                    FROM dbo.stock_ubicacion su
                    INNER JOIN dbo.productos p ON p.id_producto = su.id_producto
                    INNER JOIN dbo.unidades_medida u ON u.id_unidad = p.id_unidad
                    INNER JOIN dbo.ubicaciones ub ON ub.id_ubicacion = su.id_ubicacion
                    WHERE ub.codigo_ubicacion = :codigo_ubicacion
                      AND ub.activo = 1
                      AND p.activo = 1
                      AND (su.cantidad_actual - ISNULL(su.cantidad_en_picking, 0)) > 0
                    ORDER BY p.sku, su.lote
                    """
                ),
                conn,
                params={"codigo_ubicacion": codigo_ubicacion},
            )

    return run_db_with_retry(_op)


def rf_find_product_by_code(code: str) -> dict | None:
    code_norm = str(code or "").strip().upper()
    if not code_norm:
        return None

    df = rf_get_productos_lookup()
    if df.empty:
        return None

    sku_mask = df["sku"].astype(str).str.upper() == code_norm
    ean_mask = df["ean_serie"].fillna("").astype(str).str.upper() == code_norm
    matches = df[sku_mask | ean_mask]

    if matches.empty:
        return None

    return matches.iloc[0].to_dict()


def rf_clear_master_cache() -> None:
    rf_get_proveedores.clear()
    rf_get_productos_lookup.clear()
    rf_get_stage_recepcion.clear()
    rf_get_ubicaciones_activas.clear()
    rf_get_stock_consulta.clear()
    rf_get_pickings_pendientes.clear()
    rf_get_tareas_picking.clear()
    rf_get_auditoria_picking.clear()
    rf_get_stock_por_ubicacion.clear()

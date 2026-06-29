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


@st.cache_data(ttl=120, show_spinner=False)
def rf_get_stock_consulta(codigo: str = "") -> pd.DataFrame:
    codigo = str(codigo or "").strip()

    def _op():
        with get_engine().connect() as conn:
            return pd.read_sql(
                text(
                    """
                    SELECT TOP 200
                        p.sku,
                        p.ean_serie,
                        p.nombre_producto,
                        u.codigo_unidad,
                        ub.codigo_ubicacion,
                        su.lote,
                        su.cantidad_actual,
                        ISNULL(su.cantidad_en_picking, 0) AS cantidad_en_picking,
                        su.cantidad_actual - ISNULL(su.cantidad_en_picking, 0) AS cantidad_disponible
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
                    ORDER BY p.sku, ub.codigo_ubicacion
                    """
                ),
                conn,
                params={"codigo": codigo},
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
    rf_get_stock_consulta.clear()

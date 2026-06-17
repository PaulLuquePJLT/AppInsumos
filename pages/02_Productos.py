import streamlit as st

from src.queries import get_productos_activos, get_categorias, get_unidades, insert_producto

st.title("🧾 Productos")

if "msg_producto" in st.session_state:
    st.success(st.session_state.pop("msg_producto"))

categorias = get_categorias()
unidades = get_unidades()

with st.expander("Agregar producto", expanded=True):
    if categorias.empty or unidades.empty:
        st.warning(
            "Antes de registrar productos debes tener categorías y unidades de medida cargadas."
        )
    else:
        with st.form("form_producto"):
            sku = st.text_input("SKU").strip().upper()
            nombre_producto = st.text_input("Nombre del producto").strip()
            descripcion = st.text_area("Descripción").strip()
            categoria = st.selectbox("Categoría", categorias["nombre_categoria"].tolist())
            unidad = st.selectbox("Unidad de medida", unidades["nombre_unidad"].tolist())
            stock_minimo = st.number_input("Stock mínimo", min_value=0.0, step=1.0)
            stock_maximo = st.number_input("Stock máximo", min_value=0.0, step=1.0)
            requiere_lote = st.checkbox("Requiere lote", value=False)
            submitted = st.form_submit_button("Guardar producto")

        if submitted:
            if not sku or not nombre_producto:
                st.error("Completa SKU y nombre del producto.")
            elif stock_maximo > 0 and stock_maximo < stock_minimo:
                st.error("El stock máximo no puede ser menor que el stock mínimo.")
            else:
                id_categoria = int(
                    categorias.loc[
                        categorias["nombre_categoria"] == categoria,
                        "id_categoria",
                    ].iloc[0]
                )
                id_unidad = int(
                    unidades.loc[
                        unidades["nombre_unidad"] == unidad,
                        "id_unidad",
                    ].iloc[0]
                )

                try:
                    insert_producto(
                        sku=sku,
                        nombre_producto=nombre_producto,
                        descripcion=descripcion,
                        id_categoria=id_categoria,
                        id_unidad=id_unidad,
                        stock_minimo=stock_minimo,
                        stock_maximo=stock_maximo,
                        requiere_lote=int(requiere_lote),
                    )
                    st.session_state["msg_producto"] = "Producto agregado correctamente."
                    st.rerun()
                except Exception as exc:
                    error_text = str(exc)
                    if "UNIQUE" in error_text.upper() or "DUPLICATE" in error_text.upper():
                        st.error("Ya existe un producto con ese SKU.")
                    else:
                        st.error("No se pudo guardar el producto.")
                        st.exception(exc)

st.subheader("Productos activos")
productos = get_productos_activos()
st.dataframe(productos, use_container_width=True, hide_index=True)

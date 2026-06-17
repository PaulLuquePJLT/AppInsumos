import streamlit as st
from src.queries import get_productos_activos, get_categorias, get_unidades, insert_producto

st.title('🧾 Productos')

categorias = get_categorias()
unidades = get_unidades()

with st.expander('Agregar producto'):
    form = st.form('form_producto')
    sku = form.text_input('SKU')
    nombre = form.text_input('Nombre del producto')
    descripcion = form.text_area('Descripción')
    categoria = form.selectbox('Categoría', categorias['nombre_categoria'].tolist() if not categorias.empty else [])
    unidad = form.selectbox('Unidad de medida', unidades['nombre_unidad'].tolist() if not unidades.empty else [])
    stock_minimo = form.number_input('Stock mínimo', min_value=0.0, step=1.0)
    stock_maximo = form.number_input('Stock máximo', min_value=0.0, step=1.0)
    requiere_lote = form.checkbox('Requiere lote', value=False)
    submitted = form.form_submit_button('Guardar producto')

    if submitted:
        if not sku or not nombre or categorias.empty or unidades.empty:
            st.error('Complete todos los campos y asegúrese de tener categorías y unidades disponibles.')
        else:
            id_categoria = int(categorias.loc[categorias['nombre_categoria'] == categoria, 'id_categoria'].iloc[0])
            id_unidad = int(unidades.loc[unidades['nombre_unidad'] == unidad, 'id_unidad'].iloc[0])
            insert_producto(sku, nombre, descripcion, id_categoria, id_unidad, stock_minimo, stock_maximo, int(requiere_lote))
            st.success('Producto agregado correctamente.')

st.subheader('Productos activos')
productos = get_productos_activos()
st.dataframe(productos)

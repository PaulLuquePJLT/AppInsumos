import streamlit as st

from src.auth import create_user, deactivate_user, get_roles, get_users, update_user
from src.bulk_utils import clean_text
from src.session import is_admin


st.title("👤 Usuarios")

if not is_admin():
    st.error("No tienes permisos para administrar usuarios.")
    st.stop()

if "msg_usuario" in st.session_state:
    st.success(st.session_state.pop("msg_usuario"))

roles = get_roles()
usuarios = get_users()

if roles.empty:
    st.error("No hay roles activos. Ejecuta la migración de autenticación en Azure SQL.")
    st.stop()


def _role_id(nombre_rol: str) -> int:
    return int(
        roles.loc[
            roles["nombre_rol"] == nombre_rol,
            "id_rol",
        ].iloc[0]
    )


tab_crear, tab_editar, tab_listado = st.tabs([
    "Agregar",
    "Modificar / eliminar",
    "Listado",
])


with tab_crear:
    with st.form("form_crear_usuario"):
        usuario_login = st.text_input("Usuario").strip().lower()
        nombres = st.text_input("Nombres").strip()
        apellidos = st.text_input("Apellidos").strip()
        email = st.text_input("Correo").strip().lower()
        rol = st.selectbox("Rol", roles["nombre_rol"].tolist())
        password = st.text_input("Contraseña inicial", type="password")
        confirm_password = st.text_input("Confirmar contraseña", type="password")
        submitted = st.form_submit_button("Guardar usuario")

    if submitted:
        if not usuario_login or not nombres or not email:
            st.error("Usuario, nombres y correo son obligatorios.")
        elif len(password) < 8:
            st.error("La contraseña debe tener al menos 8 caracteres.")
        elif password != confirm_password:
            st.error("Las contraseñas no coinciden.")
        else:
            try:
                create_user(
                    usuario_login=usuario_login,
                    password=password,
                    nombres=nombres,
                    apellidos=apellidos,
                    email=email,
                    id_rol=_role_id(rol),
                    activo=1,
                )
                st.session_state["msg_usuario"] = "Usuario creado correctamente."
                st.rerun()
            except Exception as exc:
                st.error(
                    "No se pudo crear el usuario. "
                    "Revisa si el usuario o correo ya existen."
                )
                st.exception(exc)


with tab_editar:
    if usuarios.empty:
        st.info("No hay usuarios registrados.")
    else:
        labels = usuarios.apply(
            lambda r: (
                f"{r['usuario_login']} | {r['email']} | {r['rol']} | "
                f"{'Activo' if r['activo'] else 'Inactivo'}"
            ),
            axis=1,
        ).tolist()

        selected_label = st.selectbox("Selecciona usuario", labels)
        selected = usuarios.iloc[labels.index(selected_label)]

        role_options = roles["nombre_rol"].tolist()
        current_role = selected["rol"] if selected["rol"] in role_options else role_options[0]

        with st.form("form_editar_usuario"):
            usuario_login = st.text_input("Usuario", value=str(selected["usuario_login"]))
            nombres = st.text_input("Nombres", value=clean_text(selected["nombres"]))
            apellidos = st.text_input("Apellidos", value=clean_text(selected["apellidos"]))
            email = st.text_input("Correo", value=str(selected["email"]))

            rol = st.selectbox(
                "Rol",
                role_options,
                index=role_options.index(current_role),
            )

            activo = st.checkbox("Activo", value=bool(selected["activo"]))
            new_password = st.text_input("Nueva contraseña opcional", type="password")

            col1, col2 = st.columns(2)
            guardar = col1.form_submit_button("Guardar cambios")
            eliminar = col2.form_submit_button("Eliminar / desactivar")

        if guardar:
            if new_password and len(new_password) < 8:
                st.error("La nueva contraseña debe tener al menos 8 caracteres.")
            else:
                try:
                    update_user(
                        id_usuario=int(selected["id_usuario"]),
                        usuario_login=usuario_login,
                        nombres=nombres,
                        apellidos=apellidos,
                        email=email,
                        id_rol=_role_id(rol),
                        activo=int(activo),
                        new_password=new_password or None,
                    )
                    st.session_state["msg_usuario"] = "Usuario actualizado correctamente."
                    st.rerun()
                except Exception as exc:
                    st.error("No se pudo actualizar el usuario.")
                    st.exception(exc)

        if eliminar:
            try:
                deactivate_user(int(selected["id_usuario"]))
                st.session_state["msg_usuario"] = "Usuario desactivado correctamente."
                st.rerun()
            except Exception as exc:
                st.error("No se pudo desactivar el usuario.")
                st.exception(exc)


with tab_listado:
    st.dataframe(usuarios, use_container_width=True, hide_index=True)

import streamlit as st

st.title("Política de Privacidad")
st.caption("App WMS Block B")

st.markdown("""
## 1. Datos que recopila la aplicación

**App WMS Block B** puede recopilar y almacenar datos necesarios para operar el sistema, incluyendo usuario, nombres, apellidos, correo, rol, fecha de inicio de sesión, registros de movimientos, pedidos, pickings, ajustes, consultas operativas y datos asociados a acciones realizadas dentro de la aplicación.

## 2. Finalidad del tratamiento

Los datos se utilizan para autenticar usuarios, controlar accesos por rol, registrar trazabilidad operativa, mantener saldos de inventario, generar reportes, auditar movimientos y asegurar la continuidad de los procesos logísticos.

## 3. Datos operativos

La aplicación registra información relacionada con productos, ubicaciones, proveedores, cuentas logísticas, movimientos de stock, pedidos, picking, transferencias, salidas por ajuste y aprobaciones. Estos datos se almacenan para control interno, trazabilidad y análisis operativo.

## 4. Uso de la información

La información se utiliza únicamente para la operación del sistema y para fines internos autorizados. No debe ser usada para propósitos ajenos a la gestión logística sin autorización de la organización responsable.

## 5. Conservación de datos

Los datos pueden conservarse mientras sean necesarios para fines operativos, históricos, auditoría, cumplimiento interno o soporte de procesos. Los plazos de conservación pueden depender de las políticas internas de la organización.

## 6. Acceso y eliminación de datos

El usuario puede solicitar al administrador interno la revisión, corrección, desactivación o eliminación de sus datos personales cuando corresponda. Algunas transacciones operativas pueden mantenerse por trazabilidad, auditoría o integridad histórica del inventario.

## 7. Seguridad

La aplicación utiliza autenticación por usuario y contraseña, roles de acceso y controles internos para limitar las funciones disponibles según el perfil del usuario. La seguridad final depende también de la correcta administración de credenciales, permisos y configuraciones de infraestructura.

## 8. Servicios externos

La aplicación puede conectarse a servicios externos como Azure SQL, servicios SMTP para recuperación de contraseña y plataformas de hosting. Dichos servicios procesan datos únicamente para permitir el funcionamiento de la aplicación.

## 9. Contacto

Para consultas sobre privacidad, corrección o eliminación de datos, el usuario debe contactar al administrador interno de App WMS Block B o al área responsable de protección de datos de la organización.
""")

st.info("Este texto es una plantilla y debe ser revisado por el área legal, privacidad o cumplimiento de la organización antes de publicarse formalmente.")

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

import bcrypt
import pandas as pd
from sqlalchemy import text

from src.db import get_engine
from src.email_service import send_email
from src.time_utils import local_now


RESET_CODE_MINUTES = 15
MAX_RESET_ATTEMPTS = 5
LOGIN_LOCK_THRESHOLD = 3
UNKNOWN_LOGIN_MAX_ATTEMPTS = 5


class AuthenticationError(Exception):
    """Error base de autenticacion."""


class InvalidCredentialsError(AuthenticationError):
    def __init__(self, remaining_attempts: int):
        self.remaining_attempts = max(int(remaining_attempts), 0)
        super().__init__("Credenciales invalidas.")


class AccountLockedError(AuthenticationError):
    def __init__(self, message: str | None = None):
        super().__init__(
            message
            or "La cuenta fue bloqueada por intentos fallidos. Recupera tu contraseña para desbloquearla."
        )


def _hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def _is_bcrypt_hash(value: str | None) -> bool:
    if not value:
        return False

    return value.startswith(("$2a$", "$2b$", "$2y$"))


def _verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False

    if _is_bcrypt_hash(stored_hash):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        except ValueError:
            return False

    # Compatibilidad con el seed antiguo que guardaba 'changeme' en texto plano.
    return password == stored_hash


def _normalize_identifier(value: str) -> str:
    return str(value or "").strip().lower()


def _role_is_admin(role_name: str | None) -> bool:
    return str(role_name or "").strip().lower() in {
        "admin",
        "administrador",
    }


def _bool_value(value) -> bool:
    return bool(int(value or 0))


def get_roles() -> pd.DataFrame:
    query = text("""
        SELECT id_rol, nombre_rol, descripcion, activo
        FROM roles
        WHERE activo = 1
        ORDER BY CASE
            WHEN nombre_rol IN ('Administrador', 'ADMIN') THEN 1
            WHEN nombre_rol IN ('Usuario', 'OPERADOR') THEN 2
            WHEN nombre_rol IN ('Operario') THEN 3
            ELSE 4
        END,
        nombre_rol
    """)

    with get_engine().connect() as conn:
        return pd.read_sql(query, conn)


def get_users() -> pd.DataFrame:
    query = text("""
        SELECT
            u.id_usuario,
            u.usuario_login,
            u.nombres,
            u.apellidos,
            u.nombre,
            u.email,
            u.id_rol,
            r.nombre_rol AS rol,
            u.activo,
            ISNULL(u.failed_login_attempts, 0) AS failed_login_attempts,
            ISNULL(u.account_locked, 0) AS account_locked,
            u.account_locked_at,
            u.account_locked_reason,
            u.ultimo_login,
            u.fecha_creacion
        FROM usuarios u
        INNER JOIN roles r ON r.id_rol = u.id_rol
        ORDER BY u.activo DESC, u.account_locked DESC, u.usuario_login
    """)

    with get_engine().connect() as conn:
        return pd.read_sql(query, conn)


def find_user(identifier: str, include_inactive: bool = False) -> dict | None:
    identifier = _normalize_identifier(identifier)

    query = text("""
        SELECT TOP 1
            u.id_usuario,
            u.usuario_login,
            u.nombres,
            u.apellidos,
            u.nombre,
            u.email,
            u.password_hash,
            u.id_rol,
            r.nombre_rol AS rol,
            u.activo,
            u.reset_code_hash,
            u.reset_code_expires_at,
            u.reset_code_attempts,
            ISNULL(u.failed_login_attempts, 0) AS failed_login_attempts,
            u.last_failed_login,
            ISNULL(u.account_locked, 0) AS account_locked,
            u.account_locked_at,
            u.account_locked_reason
        FROM usuarios u
        INNER JOIN roles r ON r.id_rol = u.id_rol
        WHERE (:include_inactive = 1 OR u.activo = 1)
          AND (
                LOWER(u.usuario_login) = :identifier
                OR LOWER(u.email) = :identifier
              )
    """)

    with get_engine().connect() as conn:
        row = conn.execute(
            query,
            {
                "identifier": identifier,
                "include_inactive": 1 if include_inactive else 0,
            },
        ).mappings().first()

    return dict(row) if row else None


def _record_failed_login(id_usuario: int) -> tuple[int, bool]:
    with get_engine().begin() as conn:
        conn.execute(
            text("""
                UPDATE usuarios
                SET failed_login_attempts = ISNULL(failed_login_attempts, 0) + 1,
                    last_failed_login = dbo.fn_now_bogota_lima(),
                    account_locked = CASE
                        WHEN ISNULL(failed_login_attempts, 0) + 1 >= :threshold THEN 1
                        ELSE ISNULL(account_locked, 0)
                    END,
                    account_locked_at = CASE
                        WHEN ISNULL(failed_login_attempts, 0) + 1 >= :threshold
                             AND ISNULL(account_locked, 0) = 0
                        THEN dbo.fn_now_bogota_lima()
                        ELSE account_locked_at
                    END,
                    account_locked_reason = CASE
                        WHEN ISNULL(failed_login_attempts, 0) + 1 >= :threshold
                        THEN 'Bloqueo automatico por intentos fallidos de login'
                        ELSE account_locked_reason
                    END,
                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_usuario = :id_usuario
            """),
            {"id_usuario": int(id_usuario), "threshold": LOGIN_LOCK_THRESHOLD},
        )
        row = conn.execute(
            text("""
                SELECT
                    ISNULL(failed_login_attempts, 0) AS failed_login_attempts,
                    ISNULL(account_locked, 0) AS account_locked
                FROM usuarios
                WHERE id_usuario = :id_usuario
            """),
            {"id_usuario": int(id_usuario)},
        ).mappings().one()

    return int(row["failed_login_attempts"]), bool(row["account_locked"])


def _reset_login_failures(id_usuario: int) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text("""
                UPDATE usuarios
                SET failed_login_attempts = 0,
                    last_failed_login = NULL,
                    account_locked = 0,
                    account_locked_at = NULL,
                    account_locked_reason = NULL,
                    account_unlocked_at = dbo.fn_now_bogota_lima(),
                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_usuario = :id_usuario
            """),
            {"id_usuario": int(id_usuario)},
        )


def authenticate_user(identifier: str, password: str) -> dict | None:
    identifier = _normalize_identifier(identifier)

    if not identifier or not str(password or ""):
        return None

    user = find_user(identifier)

    if not user:
        return None

    if _bool_value(user.get("account_locked")):
        raise AccountLockedError()

    if not _verify_password(password, user.get("password_hash")):
        failed_attempts, is_locked = _record_failed_login(int(user["id_usuario"]))
        remaining = max(LOGIN_LOCK_THRESHOLD - failed_attempts, 0)
        if is_locked:
            raise AccountLockedError()
        raise InvalidCredentialsError(remaining_attempts=remaining)

    # Si venía del seed antiguo en texto plano, lo rehasheamos en el primer login exitoso.
    if not _is_bcrypt_hash(user.get("password_hash")):
        update_user_password(int(user["id_usuario"]), password)
    else:
        _reset_login_failures(int(user["id_usuario"]))

    with get_engine().begin() as conn:
        conn.execute(
            text("""
                UPDATE usuarios
                SET ultimo_login = dbo.fn_now_bogota_lima(),
                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_usuario = :id_usuario
            """),
            {"id_usuario": int(user["id_usuario"])},
        )

    return {
        "id_usuario": int(user["id_usuario"]),
        "usuario_login": user.get("usuario_login"),
        "nombres": user.get("nombres") or user.get("nombre") or "",
        "apellidos": user.get("apellidos") or "",
        "email": user.get("email"),
        "id_rol": int(user["id_rol"]),
        "rol": user.get("rol"),
        "is_admin": _role_is_admin(user.get("rol")),
    }


def create_user(
    usuario_login: str,
    password: str,
    nombres: str,
    apellidos: str,
    email: str,
    id_rol: int,
    activo: int = 1,
) -> None:
    nombre_completo = f"{nombres.strip()} {apellidos.strip()}".strip()

    with get_engine().begin() as conn:
        conn.execute(
            text("""
                INSERT INTO usuarios
                    (
                        usuario_login,
                        nombres,
                        apellidos,
                        nombre,
                        email,
                        password_hash,
                        id_rol,
                        activo,
                        failed_login_attempts,
                        account_locked
                    )
                VALUES
                    (
                        :usuario_login,
                        :nombres,
                        :apellidos,
                        :nombre,
                        :email,
                        :password_hash,
                        :id_rol,
                        :activo,
                        0,
                        0
                    )
            """),
            {
                "usuario_login": _normalize_identifier(usuario_login),
                "nombres": nombres.strip(),
                "apellidos": apellidos.strip(),
                "nombre": nombre_completo,
                "email": _normalize_identifier(email),
                "password_hash": _hash_password(password),
                "id_rol": int(id_rol),
                "activo": int(activo),
            },
        )


def update_user(
    id_usuario: int,
    usuario_login: str,
    nombres: str,
    apellidos: str,
    email: str,
    id_rol: int,
    activo: int,
    new_password: str | None = None,
) -> None:
    nombre_completo = f"{nombres.strip()} {apellidos.strip()}".strip()

    params = {
        "id_usuario": int(id_usuario),
        "usuario_login": _normalize_identifier(usuario_login),
        "nombres": nombres.strip(),
        "apellidos": apellidos.strip(),
        "nombre": nombre_completo,
        "email": _normalize_identifier(email),
        "id_rol": int(id_rol),
        "activo": int(activo),
    }

    password_sql = ""

    if new_password:
        params["password_hash"] = _hash_password(new_password)
        password_sql = ", password_hash = :password_hash"

    with get_engine().begin() as conn:
        conn.execute(
            text(f"""
                UPDATE usuarios
                SET usuario_login = :usuario_login,
                    nombres = :nombres,
                    apellidos = :apellidos,
                    nombre = :nombre,
                    email = :email,
                    id_rol = :id_rol,
                    activo = :activo,
                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                    {password_sql}
                WHERE id_usuario = :id_usuario
            """),
            params,
        )


def deactivate_user(id_usuario: int) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text("""
                UPDATE usuarios
                SET activo = 0,
                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_usuario = :id_usuario
            """),
            {"id_usuario": int(id_usuario)},
        )


def update_user_password(id_usuario: int, new_password: str) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text("""
                UPDATE usuarios
                SET password_hash = :password_hash,
                    reset_code_hash = NULL,
                    reset_code_expires_at = NULL,
                    reset_code_attempts = 0,
                    failed_login_attempts = 0,
                    last_failed_login = NULL,
                    account_locked = 0,
                    account_locked_at = NULL,
                    account_locked_reason = NULL,
                    account_unlocked_at = dbo.fn_now_bogota_lima(),
                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_usuario = :id_usuario
            """),
            {
                "id_usuario": int(id_usuario),
                "password_hash": _hash_password(new_password),
            },
        )


def request_password_reset(identifier: str) -> bool:
    user = find_user(identifier)

    # Respuesta genérica desde la UI. Aquí devolvemos False solo para no intentar enviar correo.
    if not user:
        return False

    code = f"{secrets.randbelow(1000000):06d}"
    expires_at = local_now().replace(tzinfo=None) + timedelta(minutes=RESET_CODE_MINUTES)

    with get_engine().begin() as conn:
        conn.execute(
            text("""
                UPDATE usuarios
                SET reset_code_hash = :reset_code_hash,
                    reset_code_expires_at = :reset_code_expires_at,
                    reset_code_attempts = 0,
                    fecha_actualizacion = dbo.fn_now_bogota_lima()
                WHERE id_usuario = :id_usuario
            """),
            {
                "id_usuario": int(user["id_usuario"]),
                "reset_code_hash": _hash_password(code),
                "reset_code_expires_at": expires_at,
            },
        )

    body = f"""Hola {user.get('nombres') or user.get('nombre') or ''},

Tu código para restablecer la contraseña del WMS es: {code}

Este código vencerá en {RESET_CODE_MINUTES} minutos.

Si no solicitaste este cambio, ignora este mensaje.
"""

    send_email(user["email"], "Código de recuperación de contraseña - WMS", body)

    return True


def reset_password_with_code(identifier: str, code: str, new_password: str) -> tuple[bool, str]:
    user = find_user(identifier)

    if not user:
        return False, "Usuario no encontrado o inactivo."

    attempts = int(user.get("reset_code_attempts") or 0)

    if attempts >= MAX_RESET_ATTEMPTS:
        return False, "Se superó el número máximo de intentos. Solicita un nuevo código."

    expires_at = user.get("reset_code_expires_at")

    if not user.get("reset_code_hash") or not expires_at:
        return False, "No hay un código vigente. Solicita un nuevo código."

    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)

    if local_now().replace(tzinfo=None) > expires_at:
        return False, "El código venció. Solicita un nuevo código."

    if not _verify_password(str(code).strip(), user.get("reset_code_hash")):
        with get_engine().begin() as conn:
            conn.execute(
                text("""
                    UPDATE usuarios
                    SET reset_code_attempts = ISNULL(reset_code_attempts, 0) + 1,
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                    WHERE id_usuario = :id_usuario
                """),
                {"id_usuario": int(user["id_usuario"])},
            )

        return False, "Código incorrecto."

    update_user_password(int(user["id_usuario"]), new_password)

    return True, "Contraseña actualizada correctamente. Ya puedes iniciar sesión."


def ensure_default_admin(
    default_password: str | None = None,
    force_password_reset: bool = False,
) -> None:
    """Crea el usuario admin inicial o rehashea el seed antiguo.

    No sobrescribe una contraseña bcrypt existente salvo que force_password_reset=True.
    """
    if not default_password:
        return

    with get_engine().begin() as conn:
        admin_role_id = conn.execute(
            text("""
                SELECT TOP 1 id_rol
                FROM roles
                WHERE nombre_rol IN ('Administrador', 'ADMIN')
                  AND activo = 1
                ORDER BY CASE WHEN nombre_rol = 'Administrador' THEN 1 ELSE 2 END
            """)
        ).scalar()

        if not admin_role_id:
            admin_role_id = conn.execute(
                text("""
                    INSERT INTO roles (nombre_rol, descripcion, activo)
                    OUTPUT INSERTED.id_rol
                    VALUES ('Administrador', 'Administrador del sistema', 1)
                """)
            ).scalar_one()

        admin = conn.execute(
            text("""
                SELECT TOP 1 id_usuario, password_hash
                FROM usuarios
                WHERE LOWER(usuario_login) = 'admin'
                   OR LOWER(email) = 'admin@wms.com'
                ORDER BY id_usuario
            """)
        ).mappings().first()

        if admin:
            params = {
                "id_usuario": int(admin["id_usuario"]),
                "id_rol": int(admin_role_id),
            }

            password_sql = ""

            if force_password_reset or not _is_bcrypt_hash(admin.get("password_hash")):
                params["password_hash"] = _hash_password(default_password)
                password_sql = ", password_hash = :password_hash"

            conn.execute(
                text(f"""
                    UPDATE usuarios
                    SET usuario_login = ISNULL(usuario_login, 'admin'),
                        nombres = ISNULL(nombres, 'Administrador'),
                        apellidos = ISNULL(apellidos, 'WMS'),
                        nombre = ISNULL(nombre, 'Administrador WMS'),
                        id_rol = :id_rol,
                        activo = 1,
                        fecha_actualizacion = dbo.fn_now_bogota_lima()
                        {password_sql}
                    WHERE id_usuario = :id_usuario
                """),
                params,
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO usuarios
                        (
                            usuario_login,
                            nombres,
                            apellidos,
                            nombre,
                            email,
                            password_hash,
                            id_rol,
                            activo,
                            failed_login_attempts,
                            account_locked
                        )
                    VALUES
                        ('admin', 'Administrador', 'WMS', 'Administrador WMS',
                         'admin@wms.com', :password_hash, :id_rol, 1, 0, 0)
                """),
                {
                    "id_rol": int(admin_role_id),
                    "password_hash": _hash_password(default_password),
                },
            )

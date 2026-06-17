from pathlib import Path

root = Path(r'd:/luquep/01. Apps/01. Apps Webs/08. Planificación/AppSupplies/mini_wms_insumos')
files = {
    'database/schema.sql': '''SET NOCOUNT ON;

CREATE TABLE roles (
    id_rol INT IDENTITY(1,1) PRIMARY KEY,
    nombre_rol NVARCHAR(50) NOT NULL UNIQUE,
    descripcion NVARCHAR(200),
    activo BIT NOT NULL DEFAULT 1,
    fecha_creacion DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);
GO

CREATE TABLE usuarios (
    id_usuario INT IDENTITY(1,1) PRIMARY KEY,
    nombre NVARCHAR(100) NOT NULL,
    email NVARCHAR(150) NOT NULL UNIQUE,
    password_hash NVARCHAR(255) NOT NULL,
    id_rol INT NOT NULL,
    activo BIT NOT NULL DEFAULT 1,
    fecha_creacion DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT FK_usuarios_roles FOREIGN KEY (id_rol) REFERENCES roles(id_rol)
);
GO

CREATE TABLE cuentas_logisticas (
    id_cuenta INT IDENTITY(1,1) PRIMARY KEY,
    codigo_cuenta NVARCHAR(50) NOT NULL UNIQUE,
    nombre_cuenta NVARCHAR(150) NOT NULL,
    responsable NVARCHAR(100),
    centro_costo NVARCHAR(50),
    activo BIT NOT NULL DEFAULT 1,
    fecha_creacion DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);
GO

CREATE TABLE categorias_producto (
    id_categoria INT IDENTITY(1,1) PRIMARY KEY,
    nombre_categoria NVARCHAR(100) NOT NULL UNIQUE,
    descripcion NVARCHAR(250),
    activo BIT NOT NULL DEFAULT 1
);
GO

CREATE TABLE unidades_medida (
    id_unidad INT IDENTITY(1,1) PRIMARY KEY,
    codigo_unidad NVARCHAR(20) NOT NULL UNIQUE,
    nombre_unidad NVARCHAR(50) NOT NULL
);
GO

CREATE TABLE productos (
    id_producto INT IDENTITY(1,1) PRIMARY KEY,
    sku NVARCHAR(50) NOT NULL UNIQUE,
    nombre_producto NVARCHAR(150) NOT NULL,
    descripcion NVARCHAR(300),
    id_categoria INT NOT NULL,
    id_unidad INT NOT NULL,
    stock_minimo DECIMAL(18,2) NOT NULL DEFAULT 0,
    stock_maximo DECIMAL(18,2),
    requiere_lote BIT NOT NULL DEFAULT 0,
    activo BIT NOT NULL DEFAULT 1,
    fecha_creacion DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT FK_productos_categoria FOREIGN KEY (id_categoria) REFERENCES categorias_producto(id_categoria),
    CONSTRAINT FK_productos_unidad FOREIGN KEY (id_unidad) REFERENCES unidades_medida(id_unidad)
);
GO

CREATE TABLE zonas_almacen (
    id_zona INT IDENTITY(1,1) PRIMARY KEY,
    codigo_zona NVARCHAR(50) NOT NULL UNIQUE,
    nombre_zona NVARCHAR(100) NOT NULL,
    descripcion NVARCHAR(250),
    activo BIT NOT NULL DEFAULT 1
);
GO

CREATE TABLE ubicaciones (
    id_ubicacion INT IDENTITY(1,1) PRIMARY KEY,
    codigo_ubicacion NVARCHAR(80) NOT NULL UNIQUE,
    id_zona INT NOT NULL,
    tipo_ubicacion NVARCHAR(50) NOT NULL,
    pasillo NVARCHAR(20),
    rack NVARCHAR(20),
    nivel NVARCHAR(20),
    posicion NVARCHAR(20),
    capacidad_maxima DECIMAL(18,2),
    activo BIT NOT NULL DEFAULT 1,
    CONSTRAINT FK_ubicaciones_zonas FOREIGN KEY (id_zona) REFERENCES zonas_almacen(id_zona)
);
GO

CREATE TABLE movimientos (
    id_movimiento INT IDENTITY(1,1) PRIMARY KEY,
    tipo_movimiento NVARCHAR(30) NOT NULL,
    fecha_movimiento DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    id_cuenta INT NULL,
    id_proveedor INT NULL,
    referencia NVARCHAR(100),
    observacion NVARCHAR(300),
    id_usuario INT NOT NULL,
    estado NVARCHAR(30) NOT NULL DEFAULT 'CONFIRMADO',
    CONSTRAINT FK_movimientos_cuenta FOREIGN KEY (id_cuenta) REFERENCES cuentas_logisticas(id_cuenta),
    CONSTRAINT FK_movimientos_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario),
    CONSTRAINT CK_movimientos_tipo CHECK (tipo_movimiento IN (
        'ENTRADA','SALIDA_CUENTA','TRANSFERENCIA','AJUSTE_POSITIVO','AJUSTE_NEGATIVO','DEVOLUCION_CUENTA'
    ))
);
GO

CREATE TABLE movimiento_detalle (
    id_detalle INT IDENTITY(1,1) PRIMARY KEY,
    id_movimiento INT NOT NULL,
    id_producto INT NOT NULL,
    id_ubicacion_origen INT NULL,
    id_ubicacion_destino INT NULL,
    cantidad DECIMAL(18,2) NOT NULL,
    costo_unitario DECIMAL(18,4),
    lote NVARCHAR(80),
    fecha_vencimiento DATE,
    observacion NVARCHAR(250),
    CONSTRAINT FK_detalle_movimiento FOREIGN KEY (id_movimiento) REFERENCES movimientos(id_movimiento),
    CONSTRAINT FK_detalle_producto FOREIGN KEY (id_producto) REFERENCES productos(id_producto),
    CONSTRAINT FK_detalle_ubicacion_origen FOREIGN KEY (id_ubicacion_origen) REFERENCES ubicaciones(id_ubicacion),
    CONSTRAINT FK_detalle_ubicacion_destino FOREIGN KEY (id_ubicacion_destino) REFERENCES ubicaciones(id_ubicacion),
    CONSTRAINT CK_detalle_cantidad CHECK (cantidad > 0)
);
GO

CREATE TABLE stock_ubicacion (
    id_stock_ubicacion INT IDENTITY(1,1) PRIMARY KEY,
    id_producto INT NOT NULL,
    id_ubicacion INT NOT NULL,
    lote NVARCHAR(80),
    cantidad_actual DECIMAL(18,2) NOT NULL DEFAULT 0,
    fecha_actualizacion DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT FK_stock_producto FOREIGN KEY (id_producto) REFERENCES productos(id_producto),
    CONSTRAINT FK_stock_ubicacion FOREIGN KEY (id_ubicacion) REFERENCES ubicaciones(id_ubicacion),
    CONSTRAINT UQ_stock_producto_ubicacion_lote UNIQUE (id_producto, id_ubicacion, lote)
);
GO

CREATE TABLE stock_cuenta (
    id_stock_cuenta INT IDENTITY(1,1) PRIMARY KEY,
    id_cuenta INT NOT NULL,
    id_producto INT NOT NULL,
    cantidad_entregada DECIMAL(18,2) NOT NULL DEFAULT 0,
    cantidad_devuelta DECIMAL(18,2) NOT NULL DEFAULT 0,
    cantidad_neta AS (cantidad_entregada - cantidad_devuelta),
    fecha_actualizacion DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT FK_stock_cuenta_cuenta FOREIGN KEY (id_cuenta) REFERENCES cuentas_logisticas(id_cuenta),
    CONSTRAINT FK_stock_cuenta_producto FOREIGN KEY (id_producto) REFERENCES productos(id_producto),
    CONSTRAINT UQ_stock_cuenta_producto UNIQUE (id_cuenta, id_producto)
);
GO
''',
    'database/procedures.sql': '''SET NOCOUNT ON;

CREATE OR ALTER PROCEDURE sp_registrar_entrada
    @id_producto INT,
    @id_ubicacion_destino INT,
    @cantidad DECIMAL(18,2),
    @id_usuario INT,
    @referencia NVARCHAR(100) = NULL,
    @observacion NVARCHAR(300) = NULL,
    @lote NVARCHAR(80) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;
        DECLARE @id_movimiento INT;

        INSERT INTO movimientos (tipo_movimiento, referencia, observacion, id_usuario)
        VALUES ('ENTRADA', @referencia, @observacion, @id_usuario);
        SET @id_movimiento = SCOPE_IDENTITY();

        INSERT INTO movimiento_detalle (id_movimiento, id_producto, id_ubicacion_destino, cantidad, lote)
        VALUES (@id_movimiento, @id_producto, @id_ubicacion_destino, @cantidad, @lote);

        IF EXISTS (SELECT 1 FROM stock_ubicacion
                   WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_destino
                   AND ISNULL(lote,'') = ISNULL(@lote,''))
            UPDATE stock_ubicacion
            SET cantidad_actual = cantidad_actual + @cantidad,
                fecha_actualizacion = SYSDATETIME()
            WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_destino
              AND ISNULL(lote,'') = ISNULL(@lote,'');
        ELSE
            INSERT INTO stock_ubicacion (id_producto, id_ubicacion, lote, cantidad_actual)
            VALUES (@id_producto, @id_ubicacion_destino, @lote, @cantidad);

        COMMIT TRANSACTION;
        SELECT @id_movimiento AS id_movimiento;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE sp_registrar_salida_cuenta
    @id_producto INT,
    @id_ubicacion_origen INT,
    @id_cuenta INT,
    @cantidad DECIMAL(18,2),
    @id_usuario INT,
    @referencia NVARCHAR(100) = NULL,
    @observacion NVARCHAR(300) = NULL,
    @lote NVARCHAR(80) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;
        DECLARE @stock_actual DECIMAL(18,2);
        DECLARE @id_movimiento INT;

        SELECT @stock_actual = cantidad_actual
        FROM stock_ubicacion
        WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_origen
          AND ISNULL(lote,'') = ISNULL(@lote,'');

        IF @stock_actual IS NULL OR @stock_actual < @cantidad
            THROW 50001, 'Stock insuficiente en la ubicación seleccionada.', 1;

        INSERT INTO movimientos (tipo_movimiento, id_cuenta, referencia, observacion, id_usuario)
        VALUES ('SALIDA_CUENTA', @id_cuenta, @referencia, @observacion, @id_usuario);
        SET @id_movimiento = SCOPE_IDENTITY();

        INSERT INTO movimiento_detalle (id_movimiento, id_producto, id_ubicacion_origen, cantidad, lote)
        VALUES (@id_movimiento, @id_producto, @id_ubicacion_origen, @cantidad, @lote);

        UPDATE stock_ubicacion
        SET cantidad_actual = cantidad_actual - @cantidad,
            fecha_actualizacion = SYSDATETIME()
        WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_origen
          AND ISNULL(lote,'') = ISNULL(@lote,'');

        IF EXISTS (SELECT 1 FROM stock_cuenta WHERE id_cuenta=@id_cuenta AND id_producto=@id_producto)
            UPDATE stock_cuenta
            SET cantidad_entregada = cantidad_entregada + @cantidad,
                fecha_actualizacion = SYSDATETIME()
            WHERE id_cuenta=@id_cuenta AND id_producto=@id_producto;
        ELSE
            INSERT INTO stock_cuenta (id_cuenta, id_producto, cantidad_entregada, cantidad_devuelta)
            VALUES (@id_cuenta, @id_producto, @cantidad, 0);

        COMMIT TRANSACTION;
        SELECT @id_movimiento AS id_movimiento;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE sp_registrar_transferencia
    @id_producto INT,
    @id_ubicacion_origen INT,
    @id_ubicacion_destino INT,
    @cantidad DECIMAL(18,2),
    @id_usuario INT,
    @referencia NVARCHAR(100) = NULL,
    @observacion NVARCHAR(300) = NULL,
    @lote NVARCHAR(80) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @id_ubicacion_origen = @id_ubicacion_destino
            THROW 50002, 'La ubicación origen y destino no pueden ser iguales.', 1;

        BEGIN TRANSACTION;
        DECLARE @stock_actual DECIMAL(18,2);
        DECLARE @id_movimiento INT;

        SELECT @stock_actual = cantidad_actual
        FROM stock_ubicacion
        WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_origen
          AND ISNULL(lote,'') = ISNULL(@lote,'');

        IF @stock_actual IS NULL OR @stock_actual < @cantidad
            THROW 50003, 'Stock insuficiente en la ubicación origen.', 1;

        INSERT INTO movimientos (tipo_movimiento, referencia, observacion, id_usuario)
        VALUES ('TRANSFERENCIA', @referencia, @observacion, @id_usuario);
        SET @id_movimiento = SCOPE_IDENTITY();

        INSERT INTO movimiento_detalle (id_movimiento, id_producto, id_ubicacion_origen, id_ubicacion_destino, cantidad, lote)
        VALUES (@id_movimiento, @id_producto, @id_ubicacion_origen, @id_ubicacion_destino, @cantidad, @lote);

        UPDATE stock_ubicacion
        SET cantidad_actual = cantidad_actual - @cantidad,
            fecha_actualizacion = SYSDATETIME()
        WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_origen
          AND ISNULL(lote,'') = ISNULL(@lote,'');

        IF EXISTS (SELECT 1 FROM stock_ubicacion
                   WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_destino
                     AND ISNULL(lote,'') = ISNULL(@lote,''))
            UPDATE stock_ubicacion
            SET cantidad_actual = cantidad_actual + @cantidad,
                fecha_actualizacion = SYSDATETIME()
            WHERE id_producto=@id_producto AND id_ubicacion=@id_ubicacion_destino
              AND ISNULL(lote,'') = ISNULL(@lote,'');
        ELSE
            INSERT INTO stock_ubicacion (id_producto, id_ubicacion, lote, cantidad_actual)
            VALUES (@id_producto, @id_ubicacion_destino, @lote, @cantidad);

        COMMIT TRANSACTION;
        SELECT @id_movimiento AS id_movimiento;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO
''',
    'database/views.sql': '''SET NOCOUNT ON;

CREATE OR ALTER VIEW vw_stock_general AS
SELECT
    p.id_producto,
    p.sku,
    p.nombre_producto,
    u.codigo_unidad,
    u.nombre_unidad,
    p.stock_minimo,
    p.stock_maximo,
    SUM(ISNULL(su.cantidad_actual, 0)) AS cantidad_total
FROM productos p
LEFT JOIN unidades_medida u ON u.id_unidad = p.id_unidad
LEFT JOIN stock_ubicacion su ON su.id_producto = p.id_producto
GROUP BY p.id_producto, p.sku, p.nombre_producto, u.codigo_unidad, u.nombre_unidad, p.stock_minimo, p.stock_maximo;
GO

CREATE OR ALTER VIEW vw_stock_por_ubicacion AS
SELECT
    p.id_producto,
    p.sku,
    p.nombre_producto,
    u.codigo_unidad,
    u.nombre_unidad,
    z.codigo_zona,
    z.nombre_zona,
    ub.codigo_ubicacion,
    ub.tipo_ubicacion,
    su.lote,
    su.cantidad_actual,
    su.fecha_actualizacion
FROM stock_ubicacion su
INNER JOIN productos p ON p.id_producto = su.id_producto
INNER JOIN unidades_medida u ON u.id_unidad = p.id_unidad
INNER JOIN ubicaciones ub ON ub.id_ubicacion = su.id_ubicacion
INNER JOIN zonas_almacen z ON z.id_zona = ub.id_zona;
GO

CREATE OR ALTER VIEW vw_stock_por_cuenta AS
SELECT
    c.id_cuenta,
    c.codigo_cuenta,
    c.nombre_cuenta,
    p.id_producto,
    p.sku,
    p.nombre_producto,
    u.codigo_unidad,
    u.nombre_unidad,
    sc.cantidad_entregada,
    sc.cantidad_devuelta,
    sc.cantidad_neta,
    sc.fecha_actualizacion
FROM stock_cuenta sc
INNER JOIN cuentas_logisticas c ON c.id_cuenta = sc.id_cuenta
INNER JOIN productos p ON p.id_producto = sc.id_producto
INNER JOIN unidades_medida u ON u.id_unidad = p.id_unidad;
GO

CREATE OR ALTER VIEW vw_movimientos AS
SELECT
    m.id_movimiento,
    m.tipo_movimiento,
    m.fecha_movimiento,
    ISNULL(c.codigo_cuenta, '') AS codigo_cuenta,
    ISNULL(c.nombre_cuenta, '') AS nombre_cuenta,
    p.sku,
    p.nombre_producto,
    ub_origen.codigo_ubicacion AS ubicacion_origen,
    ub_destino.codigo_ubicacion AS ubicacion_destino,
    md.cantidad,
    md.lote,
    m.referencia,
    m.observacion,
    m.id_usuario,
    m.estado
FROM movimientos m
LEFT JOIN movimiento_detalle md ON md.id_movimiento = m.id_movimiento
LEFT JOIN productos p ON p.id_producto = md.id_producto
LEFT JOIN ubicaciones ub_origen ON ub_origen.id_ubicacion = md.id_ubicacion_origen
LEFT JOIN ubicaciones ub_destino ON ub_destino.id_ubicacion = md.id_ubicacion_destino
LEFT JOIN cuentas_logisticas c ON c.id_cuenta = m.id_cuenta;
GO
''',
    'database/seed.sql': '''SET NOCOUNT ON;

INSERT INTO roles (nombre_rol, descripcion)
VALUES ('ADMIN', 'Administrador del sistema'),
       ('OPERADOR', 'Operador de almacén');
GO

INSERT INTO usuarios (nombre, email, password_hash, id_rol)
VALUES ('Administrador', 'admin@wms.com', 'changeme', 1);
GO

INSERT INTO categorias_producto (nombre_categoria, descripcion)
VALUES ('Papel y etiquetas', 'Insumos de papel, etiquetas y documentación'),
       ('Material de embalaje', 'Cintas, films, cajas y protección'),
       ('Oficina', 'Útiles de oficina y consumibles generales');
GO

INSERT INTO unidades_medida (codigo_unidad, nombre_unidad)
VALUES ('UND', 'Unidad'),
       ('MT', 'Metro'),
       ('PK', 'Paquete');
GO

INSERT INTO cuentas_logisticas (codigo_cuenta, nombre_cuenta, responsable, centro_costo)
VALUES ('CT001', 'Cuenta Logística A', 'Nicolás', 'CC1001'),
       ('CT002', 'Cuenta Logística B', 'María', 'CC1002');
GO

INSERT INTO zonas_almacen (codigo_zona, nombre_zona, descripcion)
VALUES ('Z01', 'Armario 1', 'Armario principal'),
       ('Z02', 'Rack 2', 'Rack selectivo en zona seca');
GO

INSERT INTO ubicaciones (codigo_ubicacion, id_zona, tipo_ubicacion, pasillo, rack, nivel, posicion, capacidad_maxima)
VALUES ('U-ARM-01', 1, 'Armario', 'A', '1', 'B', '01', 100),
       ('U-RCK-10', 2, 'Rack', 'B', '2', 'C', '10', 200);
GO

INSERT INTO productos (sku, nombre_producto, descripcion, id_categoria, id_unidad, stock_minimo, stock_maximo, requiere_lote)
VALUES ('SKU-001', 'Papel filme 30cm', 'Rollo de film para embalaje', 1, 2, 5, 50, 0),
       ('SKU-002', 'Cinta adhesiva 48mm', 'Cinta para embalaje', 2, 1, 10, 100, 0),
       ('SKU-003', 'Bolsa plástica 30x40', 'Bolsa para embalaje de insumos', 2, 1, 5, 80, 0);
GO

INSERT INTO stock_ubicacion (id_producto, id_ubicacion, lote, cantidad_actual)
VALUES (1, 1, NULL, 20),
       (2, 1, NULL, 35),
       (3, 2, NULL, 18);
GO
''',
    'src/queries.py': '''import pandas as pd
from sqlalchemy import text
from src.db import get_engine

def read_dataframe(query, params=None):
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params or {})

def execute_statement(statement, params=None):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(statement), params or {})

def get_stock_general():
    return read_dataframe('SELECT * FROM vw_stock_general ORDER BY nombre_producto')

def get_stock_por_ubicacion():
    return read_dataframe('SELECT * FROM vw_stock_por_ubicacion ORDER BY nombre_producto, codigo_ubicacion')

def get_stock_por_cuenta():
    return read_dataframe('SELECT * FROM vw_stock_por_cuenta ORDER BY nombre_cuenta, nombre_producto')

def get_productos_activos():
    return read_dataframe('''
        SELECT id_producto, sku, nombre_producto
        FROM productos
        WHERE activo = 1
        ORDER BY nombre_producto
    ''')

def get_ubicaciones():
    return read_dataframe('''
        SELECT id_ubicacion, codigo_ubicacion, tipo_ubicacion, id_zona
        FROM ubicaciones
        WHERE activo = 1
        ORDER BY codigo_ubicacion
    ''')

def get_cuentas():
    return read_dataframe('''
        SELECT id_cuenta, codigo_cuenta, nombre_cuenta
        FROM cuentas_logisticas
        WHERE activo = 1
        ORDER BY nombre_cuenta
    ''')

def get_zonas():
    return read_dataframe('''
        SELECT id_zona, codigo_zona, nombre_zona, activo
        FROM zonas_almacen
        ORDER BY codigo_zona
    ''')

def get_categorias():
    return read_dataframe('''
        SELECT id_categoria, nombre_categoria
        FROM categorias_producto
        WHERE activo = 1
        ORDER BY nombre_categoria
    ''')

def get_unidades():
    return read_dataframe('''
        SELECT id_unidad, codigo_unidad, nombre_unidad
        FROM unidades_medida
        ORDER BY nombre_unidad
    ''')

def get_movimientos():
    return read_dataframe('SELECT * FROM vw_movimientos ORDER BY fecha_movimiento DESC')

def insert_producto(sku, nombre_producto, descripcion, id_categoria, id_unidad, stock_minimo, stock_maximo, requiere_lote):
    query = text('''
        INSERT INTO productos (sku, nombre_producto, descripcion, id_categoria, id_unidad, stock_minimo, stock_maximo, requiere_lote)
        VALUES (:sku, :nombre_producto, :descripcion, :id_categoria, :id_unidad, :stock_minimo, :stock_maximo, :requiere_lote)
    ''')
    params = {
        'sku': sku,
        'nombre_producto': nombre_producto,
        'descripcion': descripcion,
        'id_categoria': id_categoria,
        'id_unidad': id_unidad,
        'stock_minimo': stock_minimo,
        'stock_maximo': stock_maximo,
        'requiere_lote': requiere_lote,
    }
    execute_statement(query, params)

def insert_zona(codigo_zona, nombre_zona, descripcion):
    query = text('''
        INSERT INTO zonas_almacen (codigo_zona, nombre_zona, descripcion)
        VALUES (:codigo_zona, :nombre_zona, :descripcion)
    ''')
    execute_statement(query, {'codigo_zona': codigo_zona, 'nombre_zona': nombre_zona, 'descripcion': descripcion})

def insert_ubicacion(codigo_ubicacion, id_zona, tipo_ubicacion, pasillo, rack, nivel, posicion, capacidad_maxima):
    query = text('''
        INSERT INTO ubicaciones (codigo_ubicacion, id_zona, tipo_ubicacion, pasillo, rack, nivel, posicion, capacidad_maxima)
        VALUES (:codigo_ubicacion, :id_zona, :tipo_ubicacion, :pasillo, :rack, :nivel, :posicion, :capacidad_maxima)
    ''')
    execute_statement(query, {
        'codigo_ubicacion': codigo_ubicacion,
        'id_zona': id_zona,
        'tipo_ubicacion': tipo_ubicacion,
        'pasillo': pasillo,
        'rack': rack,
        'nivel': nivel,
        'posicion': posicion,
        'capacidad_maxima': capacidad_maxima,
    })

def insert_cuenta(codigo_cuenta, nombre_cuenta, responsable, centro_costo):
    query = text('''
        INSERT INTO cuentas_logisticas (codigo_cuenta, nombre_cuenta, responsable, centro_costo)
        VALUES (:codigo_cuenta, :nombre_cuenta, :responsable, :centro_costo)
    ''')
    execute_statement(query, {
        'codigo_cuenta': codigo_cuenta,
        'nombre_cuenta': nombre_cuenta,
        'responsable': responsable,
        'centro_costo': centro_costo,
    })
''',
    'src/movimientos.py': '''from sqlalchemy import text
from src.db import get_engine

def registrar_entrada(id_producto, id_ubicacion_destino, cantidad, id_usuario, referencia=None, observacion=None, lote=None):
    query = text('''
        EXEC sp_registrar_entrada
            @id_producto = :id_producto,
            @id_ubicacion_destino = :id_ubicacion_destino,
            @cantidad = :cantidad,
            @id_usuario = :id_usuario,
            @referencia = :referencia,
            @observacion = :observacion,
            @lote = :lote
    ''')
    params = locals()
    with get_engine().begin() as conn:
        conn.execute(query, params)

def registrar_salida_cuenta(id_producto, id_ubicacion_origen, id_cuenta, cantidad, id_usuario, referencia=None, observacion=None, lote=None):
    query = text('''
        EXEC sp_registrar_salida_cuenta
            @id_producto = :id_producto,
            @id_ubicacion_origen = :id_ubicacion_origen,
            @id_cuenta = :id_cuenta,
            @cantidad = :cantidad,
            @id_usuario = :id_usuario,
            @referencia = :referencia,
            @observacion = :observacion,
            @lote = :lote
    ''')
    params = locals()
    with get_engine().begin() as conn:
        conn.execute(query, params)

def registrar_transferencia(id_producto, id_ubicacion_origen, id_ubicacion_destino, cantidad, id_usuario, referencia=None, observacion=None, lote=None):
    query = text('''
        EXEC sp_registrar_transferencia
            @id_producto = :id_producto,
            @id_ubicacion_origen = :id_ubicacion_origen,
            @id_ubicacion_destino = :id_ubicacion_destino,
            @cantidad = :cantidad,
            @id_usuario = :id_usuario,
            @referencia = :referencia,
            @observacion = :observacion,
            @lote = :lote
    ''')
    params = locals()
    with get_engine().begin() as conn:
        conn.execute(query, params)
''',
    'src/utils.py': '''from sqlalchemy import text
from src.db import get_engine

def execute_non_query(sql, params=None):
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})
''',
    'pages/01_Dashboard.py': '''import streamlit as st
from src.queries import get_stock_general, get_productos_activos, get_ubicaciones, get_cuentas

st.title('📊 Dashboard')

productos = get_productos_activos()
ubicaciones = get_ubicaciones()
cuentas = get_cuentas()
stock_general = get_stock_general()

col1, col2, col3, col4 = st.columns(4)
col1.metric('Productos', len(productos))
col2.metric('Ubicaciones', len(ubicaciones))
col3.metric('Cuentas logísticas', len(cuentas))
col4.metric('Productos en stock', len(stock_general[stock_general['cantidad_total'] > 0]))

low_stock = stock_general[stock_general['cantidad_total'] <= stock_general['stock_minimo']]
if not low_stock.empty:
    st.warning(f'Se encontraron {len(low_stock)} productos con stock igual o inferior al mínimo.')
    st.dataframe(low_stock[['sku', 'nombre_producto', 'cantidad_total', 'stock_minimo']].reset_index(drop=True))
else:
    st.success('No hay productos en stock bajo mínimo.')
''',
    'pages/02_Productos.py': '''import streamlit as st
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
''',
    'pages/03_Ubicaciones.py': '''import streamlit as st
from src.queries import get_zonas, get_ubicaciones, insert_zona, insert_ubicacion

st.title('📍 Ubicaciones')

zonas = get_zonas()

with st.expander('Agregar zona de almacén'):
    with st.form('form_zona'):
        codigo_zona = st.text_input('Código de zona')
        nombre_zona = st.text_input('Nombre de zona')
        descripcion = st.text_area('Descripción')
        submitted_zona = st.form_submit_button('Guardar zona')
        if submitted_zona:
            if not codigo_zona or not nombre_zona:
                st.error('Complete código y nombre de zona.')
            else:
                insert_zona(codigo_zona, nombre_zona, descripcion)
                st.success('Zona agregada correctamente.')

with st.expander('Agregar ubicación'):
    with st.form('form_ubicacion'):
        codigo_ubicacion = st.text_input('Código de ubicación')
        zona = st.selectbox('Zona', zonas['codigo_zona'].tolist() if not zonas.empty else [])
        tipo_ubicacion = st.selectbox('Tipo de ubicación', ['Armario', 'Rack', 'Estante', 'Otro'])
        pasillo = st.text_input('Pasillo')
        rack = st.text_input('Rack')
        nivel = st.text_input('Nivel')
        posicion = st.text_input('Posición')
        capacidad_maxima = st.number_input('Capacidad máxima', min_value=0.0, step=1.0)
        submitted_ubicacion = st.form_submit_button('Guardar ubicación')
        if submitted_ubicacion:
            if not codigo_ubicacion or zonas.empty:
                st.error('Complete el código y seleccione una zona.')
            else:
                id_zona = int(zonas.loc[zonas['codigo_zona'] == zona, 'id_zona'].iloc[0])
                insert_ubicacion(codigo_ubicacion, id_zona, tipo_ubicacion, pasillo, rack, nivel, posicion, capacidad_maxima)
                st.success('Ubicación agregada correctamente.')

st.subheader('Zonas de almacén')
st.dataframe(zonas)

st.subheader('Ubicaciones activas')
ubicaciones = get_ubicaciones()
st.dataframe(ubicaciones)
''',
    'pages/05_Salida_Cuenta.py': '''import streamlit as st
from src.queries import get_productos_activos, get_ubicaciones, get_cuentas
from src.movimientos import registrar_salida_cuenta

st.title('➖ Salida a cuenta logística')

productos = get_productos_activos()
ubicaciones = get_ubicaciones()
cuentas = get_cuentas()

if productos.empty or ubicaciones.empty or cuentas.empty:
    st.warning('Asegúrese de tener productos, ubicaciones y cuentas cargadas antes de registrar salidas.')

with st.form('form_salida'):
    producto_label = st.selectbox('Producto', productos['nombre_producto'].tolist())
    ubicacion_label = st.selectbox('Ubicación origen', ubicaciones['codigo_ubicacion'].tolist())
    cuenta_label = st.selectbox('Cuenta logística', cuentas['nombre_cuenta'].tolist())
    cantidad = st.number_input('Cantidad', min_value=0.01, step=1.0)
    lote = st.text_input('Lote', value='')
    referencia = st.text_input('Referencia')
    observacion = st.text_area('Observación')
    submitted = st.form_submit_button('Registrar salida')

    if submitted:
        id_producto = int(productos.loc[productos['nombre_producto'] == producto_label, 'id_producto'].iloc[0])
        id_ubicacion_origen = int(ubicaciones.loc[ubicaciones['codigo_ubicacion'] == ubicacion_label, 'id_ubicacion'].iloc[0])
        id_cuenta = int(cuentas.loc[cuentas['nombre_cuenta'] == cuenta_label, 'id_cuenta'].iloc[0])
        try:
            registrar_salida_cuenta(id_producto, id_ubicacion_origen, id_cuenta, cantidad, 1, referencia, observacion, lote or None)
            st.success('Salida registrada correctamente.')
        except Exception as exc:
            st.error(str(exc))
''',
    'pages/06_Transferencias.py': '''import streamlit as st
from src.queries import get_productos_activos, get_ubicaciones
from src.movimientos import registrar_transferencia

st.title('🔁 Transferencias')

productos = get_productos_activos()
ubicaciones = get_ubicaciones()

if productos.empty or ubicaciones.empty:
    st.warning('Asegúrese de tener productos y ubicaciones para registrar transferencias.')

with st.form('form_transferencia'):
    producto_label = st.selectbox('Producto', productos['nombre_producto'].tolist())
    origen_label = st.selectbox('Ubicación origen', ubicaciones['codigo_ubicacion'].tolist())
    destino_label = st.selectbox('Ubicación destino', ubicaciones['codigo_ubicacion'].tolist())
    cantidad = st.number_input('Cantidad', min_value=0.01, step=1.0)
    lote = st.text_input('Lote', value='')
    referencia = st.text_input('Referencia')
    observacion = st.text_area('Observación')
    submitted = st.form_submit_button('Registrar transferencia')

    if submitted:
        if origen_label == destino_label:
            st.error('La ubicación origen y destino no pueden ser iguales.')
        else:
            id_producto = int(productos.loc[productos['nombre_producto'] == producto_label, 'id_producto'].iloc[0])
            id_ubicacion_origen = int(ubicaciones.loc[ubicaciones['codigo_ubicacion'] == origen_label, 'id_ubicacion'].iloc[0])
            id_ubicacion_destino = int(ubicaciones.loc[ubicaciones['codigo_ubicacion'] == destino_label, 'id_ubicacion'].iloc[0])
            try:
                registrar_transferencia(id_producto, id_ubicacion_origen, id_ubicacion_destino, cantidad, 1, referencia, observacion, lote or None)
                st.success('Transferencia registrada correctamente.')
            except Exception as exc:
                st.error(str(exc))
''',
    'pages/07_Stock.py': '''import streamlit as st
from src.queries import get_stock_general, get_stock_por_ubicacion, get_stock_por_cuenta

st.title('📦 Stock')

stock_general = get_stock_general()
stock_ubicacion = get_stock_por_ubicacion()
stock_cuenta = get_stock_por_cuenta()

tabs = st.tabs(['Stock general', 'Por ubicación', 'Por cuenta', 'Stock bajo mínimo'])

with tabs[0]:
    st.dataframe(stock_general)

with tabs[1]:
    st.dataframe(stock_ubicacion)

with tabs[2]:
    st.dataframe(stock_cuenta)

with tabs[3]:
    low_stock = stock_general[stock_general['cantidad_total'] <= stock_general['stock_minimo']]
    if low_stock.empty:
        st.success('No hay productos en stock bajo mínimo.')
    else:
        st.dataframe(low_stock[['sku', 'nombre_producto', 'cantidad_total', 'stock_minimo']].reset_index(drop=True))
''',
    'pages/08_Movimientos.py': '''import streamlit as st
from src.queries import get_movimientos

st.title('📜 Movimientos')
movimientos = get_movimientos()
st.dataframe(movimientos)
''',
    'pages/09_Stock_Cuentas.py': '''import streamlit as st
from src.queries import get_stock_por_cuenta

st.title('💼 Stock por cuenta logística')
stock_cuenta = get_stock_por_cuenta()
st.dataframe(stock_cuenta)
''',
}

for relative, content in files.items():
    path = root / relative
    path.write_text(content, encoding='utf-8')
print(f'wrote {len(files)} files')

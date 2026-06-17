SET NOCOUNT ON;

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

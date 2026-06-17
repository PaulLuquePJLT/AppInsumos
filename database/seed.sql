SET NOCOUNT ON;

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

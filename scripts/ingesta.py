import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def cargar_csv(nombre_archivo):
    return pd.read_csv(RAW_DIR / nombre_archivo)


def cargar_json(nombre_archivo):
    return pd.read_json(RAW_DIR / nombre_archivo)


def cargar_xml_logistica(nombre_archivo):
    tree = ET.parse(RAW_DIR / nombre_archivo)
    root = tree.getroot()

    datos = []
    for pedido in root.findall("pedido"):
        datos.append({
            "id_pedido": pedido.find("id").text,
            "id_cliente": int(pedido.find("cliente").text),
            "estado": pedido.find("estado").text
        })

    return pd.DataFrame(datos)


def cargar_logs(nombre_archivo):
    ruta = RAW_DIR / nombre_archivo
    datos = []

    with open(ruta, "r", encoding="utf-8") as archivo:
        for linea in archivo:
            partes = linea.strip().split()
            if len(partes) >= 3:
                datos.append({
                    "fecha": partes[0],
                    "hora": partes[1],
                    "evento": partes[2],
                    "detalle": " ".join(partes[3:]) if len(partes) > 3 else ""
                })

    return pd.DataFrame(datos)


def limpiar_datos(df):
    return df.drop_duplicates().dropna()


def main():
    print("Iniciando simulación de ingesta de datos...")

    ventas_pos = limpiar_datos(cargar_csv("ventas_pos.csv"))
    clientes = limpiar_datos(cargar_csv("clientes_crm.csv"))
    productos = limpiar_datos(cargar_csv("productos_erp.csv"))
    ventas_online = limpiar_datos(cargar_csv("ventas_online.csv"))
    eventos_app = limpiar_datos(cargar_json("eventos_app.json"))
    logistica = limpiar_datos(cargar_xml_logistica("logistica.xml"))
    callcenter = limpiar_datos(cargar_csv("callcenter.csv"))
    proveedores = limpiar_datos(cargar_csv("proveedores.csv"))
    multimedia = limpiar_datos(cargar_csv("multimedia.csv"))
    redes_sociales = limpiar_datos(cargar_json("redes_sociales.json"))
    logs_sistema = limpiar_datos(cargar_logs("logs_sistema.txt"))

    print("Archivos CSV, JSON, XML y TXT cargados correctamente.")

    ventas_pos["total"] = ventas_pos["cantidad"] * ventas_pos["precio_unitario"]
    ventas_pos["canal"] = "tienda_fisica"

    ventas_pos_unificada = ventas_pos.merge(clientes, on="id_cliente", how="left")
    ventas_pos_unificada = ventas_pos_unificada.merge(productos, on="id_producto", how="left")

    ventas_online_unificada = ventas_online.merge(clientes, on="id_cliente", how="left")

    ventas_pos_unificada["tipo_venta"] = "POS"
    ventas_online_unificada["tipo_venta"] = "ONLINE"

    ventas_pos_final = ventas_pos_unificada[[
        "id_venta", "fecha", "id_cliente", "nombre", "apellido",
        "segmento", "ciudad", "id_producto", "nombre_producto",
        "categoria", "cantidad", "total", "canal", "tipo_venta"
    ]].rename(columns={"id_venta": "id_transaccion"})

    ventas_online_final = ventas_online_unificada[[
        "id_orden", "fecha", "id_cliente", "nombre", "apellido",
        "segmento", "ciudad", "total", "canal", "tipo_venta"
    ]].rename(columns={"id_orden": "id_transaccion"})

    ventas_unificadas = pd.concat(
        [ventas_pos_final, ventas_online_final],
        ignore_index=True,
        sort=False
    )

    ventas_unificadas.to_csv(
        PROCESSED_DIR / "ventas_unificadas.csv",
        index=False,
        encoding="utf-8-sig"
    )


    # PARTE 3: PROCESAMIENTO ETL / ELT

    # Total de ventas por cliente
    ventas_por_cliente = ventas_unificadas.groupby(
        ["id_cliente", "nombre", "apellido", "segmento", "ciudad"],
        as_index=False
    )["total"].sum()

    ventas_por_cliente = ventas_por_cliente.rename(
        columns={"total": "total_compras"}
    )

    ventas_por_cliente = ventas_por_cliente.sort_values(
        by="total_compras",
        ascending=False
    )

    ventas_por_cliente.to_csv(
        PROCESSED_DIR / "ventas_por_cliente.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # Total de ventas por canal
    ventas_por_canal = ventas_unificadas.groupby(
        "canal",
        as_index=False
    )["total"].sum()

    ventas_por_canal = ventas_por_canal.rename(
        columns={"total": "total_ventas"}
    )

    ventas_por_canal = ventas_por_canal.sort_values(
        by="total_ventas",
        ascending=False
    )

    ventas_por_canal.to_csv(
        PROCESSED_DIR / "ventas_por_canal.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # Clientes frecuentes según cantidad de compras
    clientes_frecuentes = ventas_unificadas.groupby(
        ["id_cliente", "nombre", "apellido"],
        as_index=False
    ).size()

    clientes_frecuentes = clientes_frecuentes.rename(
        columns={"size": "cantidad_compras"}
    )

    clientes_frecuentes = clientes_frecuentes.sort_values(
        by="cantidad_compras",
        ascending=False
    )

    clientes_frecuentes.to_csv(
        PROCESSED_DIR / "clientes_frecuentes.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # Productos más vendidos
    productos_mas_vendidos = ventas_unificadas.dropna(
        subset=["id_producto", "nombre_producto"]
    ).groupby(
        ["id_producto", "nombre_producto", "categoria"],
        as_index=False
    ).agg({
        "cantidad": "sum",
        "total": "sum"
    })

    productos_mas_vendidos = productos_mas_vendidos.rename(
        columns={
            "cantidad": "cantidad_total_vendida",
            "total": "total_ventas"
        }
    )

    productos_mas_vendidos = productos_mas_vendidos.sort_values(
        by="cantidad_total_vendida",
        ascending=False
    )

    productos_mas_vendidos.to_csv(
        PROCESSED_DIR / "productos_mas_vendidos.csv",
        index=False,
        encoding="utf-8-sig"
    )
    # ==============================
    # PARTE 4: MODELO DATA WAREHOUSE
    # MODELO ESTRELLA
    # ==============================

    dim_cliente = clientes[[
        "id_cliente", "nombre", "apellido", "email", "segmento", "ciudad"
    ]].drop_duplicates()

    dim_producto = productos[[
        "id_producto", "nombre_producto", "categoria", "precio_base", "proveedor"
    ]].drop_duplicates()

    dim_tiempo = ventas_unificadas[["fecha"]].drop_duplicates()
    dim_tiempo["fecha"] = pd.to_datetime(dim_tiempo["fecha"])
    dim_tiempo["id_tiempo"] = dim_tiempo["fecha"].dt.strftime("%Y%m%d").astype(int)
    dim_tiempo["dia"] = dim_tiempo["fecha"].dt.day
    dim_tiempo["mes"] = dim_tiempo["fecha"].dt.month
    dim_tiempo["anio"] = dim_tiempo["fecha"].dt.year

    dim_tiempo = dim_tiempo[[
        "id_tiempo", "fecha", "dia", "mes", "anio"
    ]]

    dim_canal = ventas_unificadas[["canal"]].drop_duplicates().reset_index(drop=True)
    dim_canal["id_canal"] = dim_canal.index + 1
    dim_canal["descripcion"] = dim_canal["canal"].replace({
        "tienda_fisica": "Venta realizada en tienda física",
        "web": "Venta realizada mediante sitio web",
        "app": "Venta realizada mediante aplicación móvil"
    })

    dim_canal = dim_canal[[
        "id_canal", "canal", "descripcion"
    ]]

    fact_ventas = ventas_unificadas.copy()
    fact_ventas["fecha"] = pd.to_datetime(fact_ventas["fecha"])
    fact_ventas["id_tiempo"] = fact_ventas["fecha"].dt.strftime("%Y%m%d").astype(int)

    fact_ventas = fact_ventas.merge(
        dim_canal[["id_canal", "canal"]],
        on="canal",
        how="left"
    )

    fact_ventas = fact_ventas[[
        "id_transaccion",
        "id_cliente",
        "id_producto",
        "id_tiempo",
        "id_canal",
        "cantidad",
        "total",
        "tipo_venta"
    ]]

    fact_ventas.to_csv(PROCESSED_DIR / "fact_ventas.csv", index=False, encoding="utf-8-sig")
    dim_cliente.to_csv(PROCESSED_DIR / "dim_cliente.csv", index=False, encoding="utf-8-sig")
    dim_producto.to_csv(PROCESSED_DIR / "dim_producto.csv", index=False, encoding="utf-8-sig")
    dim_tiempo.to_csv(PROCESSED_DIR / "dim_tiempo.csv", index=False, encoding="utf-8-sig")
    dim_canal.to_csv(PROCESSED_DIR / "dim_canal.csv", index=False, encoding="utf-8-sig")

    print("Modelo estrella del Data Warehouse generado correctamente.")
    print("- fact_ventas.csv")
    print("- dim_cliente.csv")
    print("- dim_producto.csv")
    print("- dim_tiempo.csv")
    print("- dim_canal.csv")
    
    eventos_app.to_csv(PROCESSED_DIR / "eventos_app_limpio.csv", index=False, encoding="utf-8-sig")
    logistica.to_csv(PROCESSED_DIR / "logistica_limpia.csv", index=False, encoding="utf-8-sig")
    callcenter.to_csv(PROCESSED_DIR / "callcenter_limpio.csv", index=False, encoding="utf-8-sig")
    proveedores.to_csv(PROCESSED_DIR / "proveedores_limpio.csv", index=False, encoding="utf-8-sig")
    multimedia.to_csv(PROCESSED_DIR / "multimedia_limpia.csv", index=False, encoding="utf-8-sig")
    redes_sociales.to_csv(PROCESSED_DIR / "redes_sociales_limpias.csv", index=False, encoding="utf-8-sig")
    logs_sistema.to_csv(PROCESSED_DIR / "logs_sistema_limpio.csv", index=False, encoding="utf-8-sig")

    print("Limpieza y unificación básica completadas.")
    print("Archivo principal generado: data/processed/ventas_unificadas.csv")
    print("Archivos complementarios generados en data/processed/")
    print("\nVista previa de ventas unificadas:")
    print(ventas_unificadas.head())

    # Parte 3 ETL ELT
    print("Procesamiento ETL / ELT completado.")
    print("Archivos analíticos generados:")
    print("- ventas_por_cliente.csv")
    print("- ventas_por_canal.csv")
    print("- clientes_frecuentes.csv")
    print("- productos_mas_vendidos.csv")

if __name__ == "__main__":
    main()
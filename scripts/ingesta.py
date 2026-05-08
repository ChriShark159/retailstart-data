import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def cargar_csv(nombre_archivo):
    ruta = RAW_DIR / nombre_archivo
    return pd.read_csv(ruta)


def cargar_json(nombre_archivo):
    ruta = RAW_DIR / nombre_archivo
    return pd.read_json(ruta)


def cargar_xml_logistica(nombre_archivo):
    ruta = RAW_DIR / nombre_archivo
    tree = ET.parse(ruta)
    root = tree.getroot()

    datos = []

    for pedido in root.findall("pedido"):
        datos.append({
            "id_pedido": pedido.find("id").text,
            "id_cliente": pedido.find("cliente").text,
            "estado": pedido.find("estado").text
        })

    return pd.DataFrame(datos)


def limpiar_datos(df):
    df = df.drop_duplicates()
    df = df.dropna()
    return df


def main():
    ventas_pos = cargar_csv("ventas_pos.csv")
    clientes = cargar_csv("clientes_crm.csv")
    productos = cargar_csv("productos_erp.csv")
    ventas_online = cargar_csv("ventas_online.csv")
    eventos_app = cargar_json("eventos_app.json")
    logistica = cargar_xml_logistica("logistica.xml")

    ventas_pos = limpiar_datos(ventas_pos)
    clientes = limpiar_datos(clientes)
    productos = limpiar_datos(productos)
    ventas_online = limpiar_datos(ventas_online)
    eventos_app = limpiar_datos(eventos_app)
    logistica = limpiar_datos(logistica)

    ventas_pos["total"] = ventas_pos["cantidad"] * ventas_pos["precio_unitario"]
    ventas_pos["canal"] = "tienda_fisica"

    ventas_pos_unificada = ventas_pos.merge(
        clientes,
        on="id_cliente",
        how="left"
    )

    ventas_pos_unificada = ventas_pos_unificada.merge(
        productos,
        on="id_producto",
        how="left"
    )

    ventas_online_unificada = ventas_online.merge(
        clientes,
        on="id_cliente",
        how="left"
    )

    ventas_pos_unificada["tipo_venta"] = "POS"
    ventas_online_unificada["tipo_venta"] = "ONLINE"

    ventas_pos_final = ventas_pos_unificada[[
        "id_venta",
        "fecha",
        "id_cliente",
        "nombre",
        "apellido",
        "segmento",
        "ciudad",
        "id_producto",
        "nombre_producto",
        "categoria",
        "cantidad",
        "total",
        "canal",
        "tipo_venta"
    ]]

    ventas_online_final = ventas_online_unificada[[
        "id_orden",
        "fecha",
        "id_cliente",
        "nombre",
        "apellido",
        "segmento",
        "ciudad",
        "total",
        "canal",
        "tipo_venta"
    ]]

    ventas_pos_final = ventas_pos_final.rename(columns={"id_venta": "id_transaccion"})
    ventas_online_final = ventas_online_final.rename(columns={"id_orden": "id_transaccion"})

    ventas_unificadas = pd.concat(
        [ventas_pos_final, ventas_online_final],
        ignore_index=True,
        sort=False
    )

    salida = PROCESSED_DIR / "ventas_unificadas.csv"
    ventas_unificadas.to_csv(salida, index=False, encoding="utf-8-sig")

    print("Ingesta finalizada correctamente.")
    print(f"Archivo generado: {salida}")
    print("\nVista previa:")
    print(ventas_unificadas.head())


if __name__ == "__main__":
    main()
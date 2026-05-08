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


if __name__ == "__main__":
    main()
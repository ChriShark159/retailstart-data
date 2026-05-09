import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def formato_pesos(valor):
    return f"${valor:,.0f}".replace(",", ".")


def agregar_etiquetas_barras(ax):
    for barra in ax.patches:
        alto = barra.get_height()
        ax.annotate(
            formato_pesos(alto) if alto >= 10000 else f"{int(alto)}",
            (barra.get_x() + barra.get_width() / 2, alto),
            ha="center",
            va="bottom",
            fontsize=9
        )


def main():
    ventas_pos = pd.read_csv(RAW_DIR / "ventas_pos.csv")
    clientes = pd.read_csv(RAW_DIR / "clientes_crm.csv")
    productos = pd.read_csv(RAW_DIR / "productos_erp.csv")
    ventas_online = pd.read_csv(RAW_DIR / "ventas_online.csv")

    ventas_pos = ventas_pos.drop_duplicates().dropna()
    clientes = clientes.drop_duplicates().dropna()
    productos = productos.drop_duplicates().dropna()
    ventas_online = ventas_online.drop_duplicates().dropna()

    ventas_pos["total"] = ventas_pos["cantidad"] * ventas_pos["precio_unitario"]
    ventas_pos["canal"] = "tienda_fisica"

    ventas_pos_detalle = ventas_pos.merge(clientes, on="id_cliente", how="left")
    ventas_pos_detalle = ventas_pos_detalle.merge(productos, on="id_producto", how="left")

    ventas_online_detalle = ventas_online.merge(clientes, on="id_cliente", how="left")

    ventas_pos_clientes = ventas_pos_detalle[[
        "id_cliente", "nombre", "apellido", "segmento", "ciudad", "total", "canal"
    ]]

    ventas_online_clientes = ventas_online_detalle[[
        "id_cliente", "nombre", "apellido", "segmento", "ciudad", "total", "canal"
    ]]

    ventas_clientes_total = pd.concat(
        [ventas_pos_clientes, ventas_online_clientes],
        ignore_index=True
    )

    mejores_clientes = ventas_clientes_total.groupby(
        ["id_cliente", "nombre", "apellido", "segmento", "ciudad"],
        as_index=False
    )["total"].sum()

    mejores_clientes = mejores_clientes.rename(columns={"total": "total_compras"})
    mejores_clientes = mejores_clientes.sort_values(by="total_compras", ascending=False)

    ventas_por_canal = ventas_clientes_total.groupby(
        "canal",
        as_index=False
    )["total"].sum()

    ventas_por_canal = ventas_por_canal.rename(columns={"total": "total_ventas"})
    ventas_por_canal = ventas_por_canal.sort_values(by="total_ventas", ascending=False)

    productos_mas_vendidos = ventas_pos_detalle.groupby(
        ["id_producto", "nombre_producto", "categoria"],
        as_index=False
    ).agg({
        "cantidad": "sum",
        "total": "sum"
    })

    productos_mas_vendidos = productos_mas_vendidos.rename(columns={
        "cantidad": "cantidad_vendida",
        "total": "total_ventas"
    })

    productos_mas_vendidos = productos_mas_vendidos.sort_values(
        by=["cantidad_vendida", "total_ventas"],
        ascending=False
    )

    plt.figure(figsize=(12, 6))
    ax = plt.gca()
    ax.bar(
        mejores_clientes["nombre"] + " " + mejores_clientes["apellido"],
        mejores_clientes["total_compras"]
    )
    ax.set_title("Mejores clientes según total de compras")
    ax.set_xlabel("Cliente")
    ax.set_ylabel("Total de compras")
    ax.ticklabel_format(style="plain", axis="y")
    plt.xticks(rotation=30, ha="right")
    agregar_etiquetas_barras(ax)
    plt.tight_layout()
    plt.savefig(PROCESSED_DIR / "grafico_mejores_clientes.png")
    plt.close()

    plt.figure(figsize=(8, 5))
    ax = plt.gca()
    ax.bar(
        ventas_por_canal["canal"],
        ventas_por_canal["total_ventas"]
    )
    ax.set_title("Ventas totales por canal")
    ax.set_xlabel("Canal")
    ax.set_ylabel("Total de ventas")
    ax.ticklabel_format(style="plain", axis="y")
    agregar_etiquetas_barras(ax)
    plt.tight_layout()
    plt.savefig(PROCESSED_DIR / "grafico_ventas_por_canal.png")
    plt.close()

    plt.figure(figsize=(12, 6))
    ax = plt.gca()
    ax.bar(
        productos_mas_vendidos["nombre_producto"],
        productos_mas_vendidos["cantidad_vendida"]
    )
    ax.set_title("Productos con mayor cantidad de ventas")
    ax.set_xlabel("Producto")
    ax.set_ylabel("Cantidad vendida")
    plt.xticks(rotation=30, ha="right")

    for barra in ax.patches:
        alto = barra.get_height()
        ax.annotate(
            f"{int(alto)}",
            (barra.get_x() + barra.get_width() / 2, alto),
            ha="center",
            va="bottom",
            fontsize=9
        )

    plt.tight_layout()
    plt.savefig(PROCESSED_DIR / "grafico_productos_mas_vendidos.png")
    plt.close()

    mejor_cliente = mejores_clientes.iloc[0]
    mejor_canal = ventas_por_canal.iloc[0]
    mejor_producto = productos_mas_vendidos.iloc[0]

    print("Análisis y visualización completados correctamente.")
    print()
    print("Pregunta 1: ¿Quiénes son los mejores clientes?")
    print(mejores_clientes[["nombre", "apellido", "segmento", "ciudad", "total_compras"]])
    print()
    print("Mejor cliente:")
    print(
        f"{mejor_cliente['nombre']} {mejor_cliente['apellido']} "
        f"con {formato_pesos(mejor_cliente['total_compras'])} en compras."
    )
    print()
    print("Pregunta 2: ¿Qué canal vende más?")
    print(ventas_por_canal)
    print()
    print(
        f"El canal que vende más es {mejor_canal['canal']} "
        f"con {formato_pesos(mejor_canal['total_ventas'])}."
    )
    print()
    print("Pregunta 3: ¿Qué producto tiene más ventas?")
    print(productos_mas_vendidos[["nombre_producto", "categoria", "cantidad_vendida", "total_ventas"]])
    print()
    print(
        f"El producto con más ventas es {mejor_producto['nombre_producto']} "
        f"con {int(mejor_producto['cantidad_vendida'])} unidades vendidas."
    )
    print()
    print("Archivos generados en data/processed:")
    print("- grafico_mejores_clientes.png")
    print("- grafico_ventas_por_canal.png")
    print("- grafico_productos_mas_vendidos.png")

if __name__ == "__main__":
    main()
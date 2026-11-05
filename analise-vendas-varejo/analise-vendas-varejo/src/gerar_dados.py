"""Gera um dataset sintético (mas realista) de vendas de uma rede de varejo.

Uso:
    python src/gerar_dados.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_PEDIDOS = 12_000
N_CLIENTES = 1_500
SAIDA = Path(__file__).resolve().parents[1] / "data" / "vendas.csv"

CATALOGO = {
    # produto: (categoria, preço, custo)
    "Notebook": ("Eletrônicos", 3200, 2400),
    "Smartphone": ("Eletrônicos", 2100, 1500),
    "Fone Bluetooth": ("Eletrônicos", 250, 120),
    "Smart TV": ("Eletrônicos", 2800, 2100),
    "Camiseta": ("Moda", 60, 22),
    "Calça Jeans": ("Moda", 150, 65),
    "Tênis": ("Moda", 320, 150),
    "Jaqueta": ("Moda", 280, 120),
    "Cafeteira": ("Casa", 220, 120),
    "Aspirador": ("Casa", 480, 300),
    "Jogo de Panelas": ("Casa", 350, 190),
    "Luminária": ("Casa", 90, 40),
    "Whey Protein": ("Esporte", 140, 80),
    "Bicicleta": ("Esporte", 1500, 1000),
    "Halteres": ("Esporte", 120, 60),
    "Livro": ("Livros", 55, 28),
    "Box de Livros": ("Livros", 190, 100),
}
REGIOES = {"Sudeste": 0.42, "Nordeste": 0.25, "Sul": 0.18, "Centro-Oeste": 0.09, "Norte": 0.06}
CANAIS = {"Online": 0.45, "Loja Física": 0.35, "App": 0.20}
# Sazonalidade por mês (Black Friday/Natal em alta, janeiro/fevereiro em baixa)
SAZONALIDADE = {1: 0.8, 2: 0.75, 3: 0.9, 4: 0.9, 5: 1.1, 6: 1.0,
                7: 0.95, 8: 0.95, 9: 1.0, 10: 1.05, 11: 1.6, 12: 1.5}


def gerar() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)

    datas = pd.date_range("2023-01-01", "2024-12-31", freq="D")
    pesos = np.array([SAZONALIDADE[d.month] * (1 + 0.0004 * i) for i, d in enumerate(datas)])
    pesos /= pesos.sum()  # leve tendência de crescimento ao longo do tempo
    data_pedido = rng.choice(datas, size=N_PEDIDOS, p=pesos)

    produtos = rng.choice(list(CATALOGO), size=N_PEDIDOS)
    df = pd.DataFrame({
        "id_pedido": np.arange(1, N_PEDIDOS + 1),
        "data_pedido": data_pedido,
        "id_cliente": rng.integers(1, N_CLIENTES + 1, N_PEDIDOS),
        "produto": produtos,
        "regiao": rng.choice(list(REGIOES), N_PEDIDOS, p=list(REGIOES.values())),
        "canal": rng.choice(list(CANAIS), N_PEDIDOS, p=list(CANAIS.values())),
        "quantidade": rng.choice([1, 2, 3, 4], N_PEDIDOS, p=[0.7, 0.2, 0.07, 0.03]),
    })
    df["categoria"] = df["produto"].map(lambda p: CATALOGO[p][0])
    df["preco_unitario"] = df["produto"].map(lambda p: CATALOGO[p][1])
    df["custo_unitario"] = df["produto"].map(lambda p: CATALOGO[p][2])

    # Descontos mais frequentes em novembro (Black Friday) e no canal online
    prob_desc = np.where(df["data_pedido"].dt.month == 11, 0.8, 0.3)
    prob_desc = np.where(df["canal"] == "Online", prob_desc + 0.1, prob_desc)
    tem_desc = rng.random(N_PEDIDOS) < prob_desc
    df["desconto"] = np.where(tem_desc, rng.choice([0.05, 0.10, 0.15, 0.20, 0.30], N_PEDIDOS), 0.0)

    df["receita"] = (df["preco_unitario"] * df["quantidade"] * (1 - df["desconto"])).round(2)
    df["lucro"] = (df["receita"] - df["custo_unitario"] * df["quantidade"]).round(2)

    # Sujeira proposital para demonstrar limpeza de dados
    idx_nulos = rng.choice(N_PEDIDOS, 60, replace=False)
    df.loc[idx_nulos, "regiao"] = None
    idx_dup = rng.choice(N_PEDIDOS, 40, replace=False)
    df = pd.concat([df, df.iloc[idx_dup]], ignore_index=True)

    return df.sort_values("data_pedido").reset_index(drop=True)


if __name__ == "__main__":
    dados = gerar()
    SAIDA.parent.mkdir(exist_ok=True)
    dados.to_csv(SAIDA, index=False)
    print(f"Dataset gerado: {SAIDA} ({len(dados):,} linhas)")

"""Análise exploratória de vendas de varejo.

Etapas: limpeza -> métricas -> gráficos -> segmentação RFM -> insights.

Uso:
    python src/gerar_dados.py
    python src/analise.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "data" / "vendas.csv"
FIGURAS = RAIZ / "reports" / "figures"
FIGURAS.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams.update({"figure.dpi": 110, "axes.titleweight": "bold"})


def brl(x: float) -> str:
    return f"R$ {x:,.0f}".replace(",", ".")


# ---------------------------------------------------------------- 1. Limpeza
def carregar_e_limpar() -> pd.DataFrame:
    df = pd.read_csv(DADOS, parse_dates=["data_pedido"])
    print(f"Linhas brutas: {len(df):,}")

    duplicadas = df.duplicated().sum()
    df = df.drop_duplicates()
    nulos = df["regiao"].isna().sum()
    df["regiao"] = df["regiao"].fillna("Não informado")
    print(f"Duplicatas removidas: {duplicadas} | Regiões nulas preenchidas: {nulos}")

    df["ano_mes"] = df["data_pedido"].dt.to_period("M").dt.to_timestamp()
    df["ano"] = df["data_pedido"].dt.year
    df["mes"] = df["data_pedido"].dt.month
    df["margem"] = df["lucro"] / df["receita"]
    return df


# ---------------------------------------------------------------- 2. Gráficos
def grafico_receita_mensal(df):
    mensal = df.groupby("ano_mes")["receita"].sum()
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(mensal.index, mensal.values / 1e3, marker="o", lw=2)
    ax.fill_between(mensal.index, mensal.values / 1e3, alpha=0.15)
    ax.set(title="Receita mensal", xlabel="", ylabel="Receita (R$ mil)")
    fig.tight_layout()
    fig.savefig(FIGURAS / "01_receita_mensal.png")
    plt.close(fig)


def grafico_categorias(df):
    cat = df.groupby("categoria").agg(receita=("receita", "sum"), lucro=("lucro", "sum"))
    cat["margem"] = cat["lucro"] / cat["receita"] * 100
    cat = cat.sort_values("receita", ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    sns.barplot(x=cat["receita"] / 1e6, y=cat.index, ax=axes[0], color="#4C72B0")
    axes[0].set(title="Receita por categoria", xlabel="R$ milhões", ylabel="")
    sns.barplot(x=cat["margem"], y=cat.index, ax=axes[1], color="#55A868")
    axes[1].set(title="Margem de lucro por categoria", xlabel="Margem (%)", ylabel="")
    fig.tight_layout()
    fig.savefig(FIGURAS / "02_categorias.png")
    plt.close(fig)
    return cat


def grafico_regiao_canal(df):
    pivot = df.pivot_table(index="regiao", columns="canal", values="receita", aggfunc="sum")
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index] / 1e6
    ax = pivot.plot(kind="bar", stacked=True, figsize=(9, 5), width=0.75)
    ax.set(title="Receita por região e canal", xlabel="", ylabel="R$ milhões")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(FIGURAS / "03_regiao_canal.png")
    plt.close()


def grafico_desconto_margem(df):
    d = df.groupby(df["desconto"] * 100).agg(margem=("margem", "mean"), pedidos=("id_pedido", "count"))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.barplot(x=d.index.astype(int), y=d["margem"] * 100, ax=ax, color="#C44E52")
    ax.set(title="Margem média por faixa de desconto", xlabel="Desconto (%)", ylabel="Margem média (%)")
    fig.tight_layout()
    fig.savefig(FIGURAS / "04_desconto_margem.png")
    plt.close(fig)


def grafico_sazonalidade(df):
    s = df.pivot_table(index="mes", columns="ano", values="receita", aggfunc="sum") / 1e3
    fig, ax = plt.subplots(figsize=(10, 4.5))
    s.plot(kind="bar", ax=ax, width=0.8)
    ax.set(title="Sazonalidade: receita por mês (ano a ano)", xlabel="Mês", ylabel="R$ mil")
    plt.xticks(rotation=0)
    fig.tight_layout()
    fig.savefig(FIGURAS / "05_sazonalidade.png")
    plt.close(fig)


# ---------------------------------------------------------------- 3. RFM
def segmentacao_rfm(df) -> pd.DataFrame:
    ref = df["data_pedido"].max() + pd.Timedelta(days=1)
    rfm = df.groupby("id_cliente").agg(
        recencia=("data_pedido", lambda x: (ref - x.max()).days),
        frequencia=("id_pedido", "nunique"),
        valor=("receita", "sum"),
    )
    rfm["R"] = pd.qcut(rfm["recencia"].rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
    rfm["F"] = pd.qcut(rfm["frequencia"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["M"] = pd.qcut(rfm["valor"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
    rfm["score"] = rfm["R"] + rfm["F"] + rfm["M"]

    def segmento(s):
        if s >= 10:
            return "Campeões"
        if s >= 8:
            return "Leais"
        if s >= 6:
            return "Potenciais"
        return "Em risco"

    rfm["segmento"] = rfm["score"].apply(segmento)

    resumo = rfm.groupby("segmento").agg(clientes=("valor", "size"), receita=("valor", "sum"))
    resumo = resumo.reindex(["Campeões", "Leais", "Potenciais", "Em risco"])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].bar(resumo.index, resumo["clientes"], color="#4C72B0")
    axes[0].set(title="Clientes por segmento", ylabel="Clientes")
    axes[1].bar(resumo.index, resumo["receita"] / 1e6, color="#55A868")
    axes[1].set(title="Receita por segmento", ylabel="R$ milhões")
    fig.tight_layout()
    fig.savefig(FIGURAS / "06_rfm.png")
    plt.close(fig)
    return rfm


# ---------------------------------------------------------------- 4. Insights
def insights(df, cat, rfm):
    receita, lucro = df["receita"].sum(), df["lucro"].sum()
    anual = df.groupby("ano")["receita"].sum()
    crescimento = (anual.iloc[-1] / anual.iloc[0] - 1) * 100
    top_prod = df.groupby("produto")["lucro"].sum().nlargest(3)
    nov_dez = df[df["mes"].isin([11, 12])]["receita"].sum() / receita * 100
    com_desc = df[df["desconto"] > 0]["margem"].mean() * 100
    sem_desc = df[df["desconto"] == 0]["margem"].mean() * 100
    campeoes = rfm[rfm["segmento"] == "Campeões"]
    pct_clientes = len(campeoes) / len(rfm) * 100
    pct_receita = campeoes["valor"].sum() / rfm["valor"].sum() * 100

    linhas = [
        "# Principais insights\n",
        f"- **Receita total:** {brl(receita)} | **Lucro:** {brl(lucro)} | **Margem:** {lucro / receita:.1%}",
        f"- **Ticket médio:** {brl(df['receita'].mean())} por pedido",
        f"- **Crescimento 2024 vs 2023:** {crescimento:+.1f}%",
        f"- **Novembro + dezembro** concentram {nov_dez:.1f}% da receita (sazonalidade forte)",
        f"- **Categoria mais lucrativa em valor absoluto:** {cat['lucro'].idxmax()}; "
        f"**maior margem:** {cat['margem'].idxmax()} ({cat['margem'].max():.1f}%)",
        f"- **Top 3 produtos por lucro:** " + ", ".join(f"{p} ({brl(v)})" for p, v in top_prod.items()),
        f"- **Margem com desconto:** {com_desc:.1f}% vs **sem desconto:** {sem_desc:.1f}%",
        f"- **Clientes 'Campeões'** são {pct_clientes:.1f}% da base e geram {pct_receita:.1f}% da receita",
    ]
    texto = "\n".join(linhas)
    (RAIZ / "reports" / "insights.md").write_text(texto + "\n", encoding="utf-8")
    print("\n" + texto)


def main():
    df = carregar_e_limpar()
    grafico_receita_mensal(df)
    cat = grafico_categorias(df)
    grafico_regiao_canal(df)
    grafico_desconto_margem(df)
    grafico_sazonalidade(df)
    rfm = segmentacao_rfm(df)
    insights(df, cat, rfm)
    print(f"\nGráficos salvos em: {FIGURAS}")


if __name__ == "__main__":
    main()

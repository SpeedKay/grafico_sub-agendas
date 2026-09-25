import requests
import zipfile
import io
import pandas as pd
import csv
import matplotlib.pyplot as plt

URL = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/sctie/pesquisa_saude/csv/pesquisa_saude_csv.zip"

resp = requests.get(URL)
resp.raise_for_status()
z = zipfile.ZipFile(io.BytesIO(resp.content))
print(z.namelist())

nome_csv = z.namelist()[0]
with z.open(nome_csv) as f:
    df = pd.read_csv(
        f,
        sep="|",
        encoding="latin1",
        engine="python",
        quoting=csv.QUOTE_NONE,
        on_bad_lines="skip",
    )

colunas_uteis = [
    "codigo_pesquisa", "uf_pesquisa", "ano_publicacao_edital",
    "subagenda_pesquisa", "modalidade_fomento", "natureza_pesquisa",
    "valor_sem_bolsa", "valor_bolsa", "valor_decit", "valor_parceiro",
    "nome_instituicao_vinculada_ao_coordenador",
]
df = df[colunas_uteis]

df["valor_total"] = df[["valor_sem_bolsa", "valor_bolsa", "valor_decit", "valor_parceiro"]].apply(
    pd.to_numeric, errors="coerce"
).sum(axis=1)

df["ano_publicacao_edital"] = pd.to_numeric(df["ano_publicacao_edital"], errors="coerce")
antes = len(df)
df = df.dropna(subset=["ano_publicacao_edital"])
df["ano_publicacao_edital"] = df["ano_publicacao_edital"].astype(int)
df = df[(df["ano_publicacao_edital"] >= 1990) & (df["ano_publicacao_edital"] <= 2026)]
print(f"{antes - len(df)} linhas descartadas por ano inválido")

invalidos = ["Não informado", "Objetivo Estratégico 02", "Objetivo Estratégico 12"]
df = df[~df["subagenda_pesquisa"].isin(invalidos)]

print("Período:", df["ano_publicacao_edital"].min(), "a", df["ano_publicacao_edital"].max())
print(df["subagenda_pesquisa"].nunique(), "sub-agendas após limpeza")
print(sorted(df["subagenda_pesquisa"].dropna().unique()))

top5_total = df["subagenda_pesquisa"].value_counts().head(5).sum()
total = len(df)
print(f"Top 5 sub-agendas concentram {top5_total/total:.1%} dos projetos (n={total})")

evolucao = (
    df.groupby(["ano_publicacao_edital", "subagenda_pesquisa"])
    .agg(qtd_projetos=("codigo_pesquisa", "count"), valor_total=("valor_total", "sum"))
    .reset_index()
)

pivot = evolucao.pivot_table(
    index="ano_publicacao_edital", columns="subagenda_pesquisa",
    values="qtd_projetos", aggfunc="sum", fill_value=0
).sort_index()

top8 = df["subagenda_pesquisa"].value_counts().head(8).index
pivot_top = pivot[top8].copy()
pivot_top["Outras"] = pivot.drop(columns=top8, errors="ignore").sum(axis=1)

pivot_top.plot(kind="area", stacked=True, figsize=(12, 6), colormap="tab20")
plt.title("Evolução das sub-agendas de pesquisa em saúde no Brasil")
plt.xlabel("Ano de publicação do edital")
plt.ylabel("Nº de projetos")
plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
plt.tight_layout()
plt.savefig("evolucao_subagendas.png", dpi=150)
plt.show()
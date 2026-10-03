import os
from datetime import date

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="App Financeiro", page_icon="💰", layout="centered")

# ==========================================
# CONSTANTES
# ==========================================
ARQUIVO_GASTOS = "meus_gastos.csv"
ARQUIVO_RECEITAS = "minhas_receitas.csv"

COLS_GASTOS = ["Data", "Categoria", "Descrição", "Forma de Pagamento", "Valor"]
COLS_RECEITAS = ["Data", "Tipo", "Origem", "Valor"]

CATEGORIAS = ["Alimentação", "Moradia", "Transporte", "Lazer", "Saúde",
              "Educação", "Assinaturas", "Fatura do Cartão", "Outros"]
FORMAS_PAGAMENTO = ["Cartão de Crédito", "Cartão de Débito", "PIX",
                    "Dinheiro", "Vale Refeição", "Pagamento de Fatura"]
TIPOS_RECEITA = ["Conta Corrente", "Vale Refeição"]

FMT_CSV = "%d/%m/%Y"

CARTEIRAS = {
    "Conservador": [("🛡️ Reserva de Emergência / Renda Fixa", 0.80), ("🏢 Fundos Imobiliários", 0.20)],
    "Moderado": [("🛡️ Tesouro IPCA+", 0.50), ("🏢 Fundos Imobiliários", 0.30), ("📈 Ações/ETFs", 0.20)],
    "Arrojado": [("📈 Ações e ETFs Globais", 0.40), ("🏢 FIIs e Fiagros", 0.30),
                 ("🛡️ Renda Fixa", 0.20), ("₿ Criptomoedas", 0.10)],
}


# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def carregar(arquivo, colunas):
    """Lê o CSV, migra formatos antigos e devolve Data como datetime."""
    if not os.path.exists(arquivo):
        return pd.DataFrame(columns=colunas).astype({"Data": "datetime64[ns]"})

    df = pd.read_csv(arquivo)

    # Migrações de arquivos antigos
    if "Tipo" in colunas and "Tipo" not in df.columns:
        df["Tipo"] = "Conta Corrente"
    if "Forma de Pagamento" in colunas and "Forma de Pagamento" not in df.columns:
        df["Forma de Pagamento"] = "Dinheiro"
    if "Tipo" in df.columns:
        # Normaliza textos longos como "Conta Corrente (Dinheiro, Pix, Salário)"
        df["Tipo"] = df["Tipo"].apply(
            lambda t: "Vale Refeição" if "Vale" in str(t) else "Conta Corrente"
        )

    df = df[colunas].copy()
    df["Data"] = pd.to_datetime(df["Data"], format=FMT_CSV, errors="coerce")
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0)
    return df.dropna(subset=["Data"]).reset_index(drop=True)


def salvar(df, arquivo):
    saida = df.copy()
    saida["Data"] = pd.to_datetime(saida["Data"]).dt.strftime(FMT_CSV)
    saida.to_csv(arquivo, index=False)


def adicionar(df, linha, colunas, arquivo):
    novo = pd.DataFrame([linha], columns=colunas)
    novo["Data"] = pd.to_datetime(novo["Data"])
    salvar(pd.concat([df, novo], ignore_index=True), arquivo)


def calcular_saldos(rec, gas):
    """Retorna (saldo_conta, saldo_vr, fatura_aberta)."""
    forma = gas["Forma de Pagamento"]
    ent_vr = rec.loc[rec["Tipo"] == "Vale Refeição", "Valor"].sum()
    ent_cc = rec.loc[rec["Tipo"] != "Vale Refeição", "Valor"].sum()

    sai_vr = gas.loc[forma == "Vale Refeição", "Valor"].sum()
    credito = gas.loc[forma == "Cartão de Crédito", "Valor"].sum()
    pago_fatura = gas.loc[forma == "Pagamento de Fatura", "Valor"].sum()
    # Crédito só sai da conta quando a fatura é paga
    sai_conta = gas.loc[~forma.isin(["Vale Refeição", "Cartão de Crédito"]), "Valor"].sum()

    return ent_cc - sai_conta, ent_vr - sai_vr, credito - pago_fatura


def filtrar_mes(df, mes):
    if mes == "Todos" or df.empty:
        return df
    return df[df["Data"].dt.strftime("%m/%Y") == mes]


# ==========================================
# APIs GRATUITAS (sem chave) - todas com cache e tolerância a falhas
# ==========================================
def _get_json(url):
    try:
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        return r.json()
    except Exception as erro:
        # AGORA ELE IMPRIME O ERRO NA TELA PRETA (TERMINAL)
        print(f"⚠️ Erro de conexão com a API: {erro}")
        return None  # o app continua funcionando se a API estiver fora do ar


@st.cache_data(ttl=3600)
def buscar_selic():
    """Banco Central (SGS 432): meta Selic, % ao ano."""
    dados = _get_json("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json")
    return float(dados[0]["valor"]) if dados else None


@st.cache_data(ttl=3600)
def buscar_ipca_12m():
    """Banco Central (SGS 433): IPCA mensal, encadeado nos últimos 12 meses."""
    dados = _get_json("https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/12?formato=json")
    if not dados or len(dados) < 12:
        return None
    acumulado = 1.0
    for item in dados:
        acumulado *= 1 + float(item["valor"]) / 100
    return (acumulado - 1) * 100


@st.cache_data(ttl=300)
def buscar_cotacoes():
    """AwesomeAPI: dólar, euro e bitcoin em reais."""
    # LINK DA API ATUALIZADO AQUI
    dados = _get_json("https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL,BTC-BRL")
    if not dados:
        return None
    try:
        return {
            nome: (float(dados[chave]["bid"]), float(dados[chave]["pctChange"]))
            for nome, chave in [("💵 Dólar", "USDBRL"), ("💶 Euro", "EURBRL"), ("₿ Bitcoin", "BTCBRL")]
        }
    except (KeyError, ValueError):
        return None


@st.cache_data(ttl=86400)
def buscar_feriados(ano):
    """BrasilAPI: feriados nacionais do ano."""
    dados = _get_json(f"https://brasilapi.com.br/api/feriados/v1/{ano}")
    return dados or []


def proximo_feriado():
    hoje = date.today()
    futuros = []
    for ano in (hoje.year, hoje.year + 1):
        for f in buscar_feriados(ano):
            try:
                d = pd.to_datetime(f["date"]).date()
            except Exception:
                continue
            if d >= hoje:
                futuros.append((d, f["name"]))
    return min(futuros) if futuros else None


# ==========================================
# DADOS
# ==========================================
df_gastos = carregar(ARQUIVO_GASTOS, COLS_GASTOS)
df_receitas = carregar(ARQUIVO_RECEITAS, COLS_RECEITAS)
saldo_conta, saldo_vr, fatura_aberta = calcular_saldos(df_receitas, df_gastos)

st.title("Meu Assessor 💰")

if "msg" in st.session_state:
    st.toast(st.session_state.pop("msg"))

aba_resumo, aba_gastos, aba_receitas, aba_editar, aba_assessor = st.tabs(
    ["📊 Resumo", "💸 Gastos", "💵 Receitas", "✏️ Editar", "🧠 Assessor"]
)

# ==========================================
# ABA 1: RESUMO
# ==========================================
with aba_resumo:
    st.header("Painel Financeiro")

    c1, c2, c3 = st.columns(3)
    c1.metric("💳 Saldo em Conta", formatar_moeda(saldo_conta))
    c2.metric("🍽️ Saldo VR", formatar_moeda(saldo_vr))
    c3.metric("🧾 Fatura em aberto", formatar_moeda(fatura_aberta))

    if saldo_vr < 0:
        st.warning("Seus gastos com Vale Refeição superam o saldo do VR. Confira os lançamentos.")

    with st.expander("🌎 Mercado hoje"):
        cotacoes = buscar_cotacoes()
        if cotacoes:
            cols = st.columns(len(cotacoes))
            for col, (nome, (preco, var)) in zip(cols, cotacoes.items()):
                col.metric(nome, formatar_moeda(preco), f"{var:+.2f}%")
        else:
            st.caption("Cotações indisponíveis no momento.")

        selic, ipca = buscar_selic(), buscar_ipca_12m()
        c1, c2 = st.columns(2)
        c1.metric("Selic (meta)", f"{selic:.2f}% a.a.".replace(".", ",") if selic else "—")
        c2.metric("IPCA 12 meses", f"{ipca:.2f}%".replace(".", ",") if ipca else "—")

        feriado = proximo_feriado()
        if feriado:
            d, nome = feriado
            st.caption(f"📅 Próximo feriado: {nome} ({d.strftime(FMT_CSV)}). "
                       "Atenção a vencimentos de boletos, que podem cair em dia não útil.")
        st.caption("Fontes: Banco Central, AwesomeAPI e BrasilAPI.")

    st.divider()

    meses = sorted(df_gastos["Data"].dt.to_period("M").unique(), reverse=True)
    opcoes_mes = ["Todos"] + [p.strftime("%m/%Y") for p in meses]
    mes = st.selectbox("Período", opcoes_mes)

    gastos_mes = filtrar_mes(df_gastos, mes)
    # Pagamento de fatura não é gasto novo (já foi contado no crédito)
    gastos_reais = gastos_mes[gastos_mes["Forma de Pagamento"] != "Pagamento de Fatura"]

    if gastos_reais.empty:
        st.info("Nenhum gasto registrado neste período.")
    else:
        st.metric("Total gasto no período", formatar_moeda(gastos_reais["Valor"].sum()))

        mostrar = gastos_mes.sort_values("Data", ascending=False).copy()
        mostrar["Data"] = mostrar["Data"].dt.strftime(FMT_CSV)
        mostrar["Valor"] = mostrar["Valor"].apply(formatar_moeda)
        st.dataframe(mostrar, use_container_width=True, hide_index=True)

        st.write("**Gastos por Categoria**")
        st.bar_chart(gastos_reais.groupby("Categoria")["Valor"].sum())

        if mes == "Todos":
            st.write("**Evolução mensal**")
            por_mes = gastos_reais.groupby(gastos_reais["Data"].dt.to_period("M").astype(str))["Valor"].sum()
            st.line_chart(por_mes)

    st.download_button(
        "⬇️ Exportar gastos (CSV)",
        df_gastos.assign(Data=df_gastos["Data"].dt.strftime(FMT_CSV)).to_csv(index=False).encode("utf-8"),
        file_name="gastos.csv",
        mime="text/csv",
    )

# ==========================================
# ABA 2: GASTOS
# ==========================================
with aba_gastos:
    st.header("Lançar Gasto")

    with st.form("form_gasto", clear_on_submit=True):
        data = st.date_input("Data da Compra", date.today(), format="DD/MM/YYYY")
        categoria = st.selectbox("Categoria", CATEGORIAS)
        descricao = st.text_input("Descrição (Ex: Supermercado)")
        forma = st.selectbox("Forma de Pagamento", FORMAS_PAGAMENTO)
        valor = st.number_input("Valor", min_value=0.01, step=1.0, format="%.2f")
        parcelas = st.number_input("Parcelas (só crédito)", min_value=1, max_value=48, value=1, step=1)
        enviar = st.form_submit_button("Salvar Gasto")

    if enviar:
        if not descricao.strip():
            st.error("Informe uma descrição.")
        elif forma == "Vale Refeição" and valor > saldo_vr:
            st.error(f"Saldo do VR insuficiente ({formatar_moeda(saldo_vr)}).")
        else:
            n = int(parcelas) if forma == "Cartão de Crédito" else 1
            valor_parcela = round(valor / n, 2)
            for i in range(n):
                data_parcela = (pd.Timestamp(data) + pd.DateOffset(months=i))
                desc = descricao.strip() + (f" ({i + 1}/{n})" if n > 1 else "")
                adicionar(df_gastos if i == 0 else carregar(ARQUIVO_GASTOS, COLS_GASTOS),
                          [data_parcela, categoria, desc, forma, valor_parcela],
                          COLS_GASTOS, ARQUIVO_GASTOS)
            st.session_state["msg"] = "Gasto salvo com sucesso! ✅"
            st.rerun()

# ==========================================
# ABA 3: RECEITAS
# ==========================================
with aba_receitas:
    st.header("Entrada de Dinheiro / Benefício")

    with st.form("form_receita", clear_on_submit=True):
        tipo = st.selectbox("Onde esse valor entrou?", TIPOS_RECEITA)
        data = st.date_input("Data do Recebimento", date.today(), format="DD/MM/YYYY")
        origem = st.text_input("Descrição (Ex: Salário, Recarga do VR)")
        valor = st.number_input("Valor", min_value=0.01, step=1.0, format="%.2f")
        enviar = st.form_submit_button("Salvar Entrada")

    if enviar:
        if not origem.strip():
            st.error("Informe uma descrição.")
        else:
            adicionar(df_receitas, [data, tipo, origem.strip(), valor], COLS_RECEITAS, ARQUIVO_RECEITAS)
            st.session_state["msg"] = "Entrada salva com sucesso! ✅"
            st.rerun()

# ==========================================
# ABA 4: EDITAR
# ==========================================
with aba_editar:
    st.header("Editar ou Excluir Registros")
    st.caption("Altere células direto na tabela. Para excluir, selecione a linha e aperte Delete. Depois clique em Salvar.")

    alvo = st.radio("O que deseja editar?", ["Gastos", "Receitas"], horizontal=True)

    if alvo == "Gastos":
        df_base, arquivo, colunas = df_gastos, ARQUIVO_GASTOS, COLS_GASTOS
        config = {
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY", required=True),
            "Categoria": st.column_config.SelectboxColumn("Categoria", options=CATEGORIAS, required=True),
            "Forma de Pagamento": st.column_config.SelectboxColumn("Forma de Pagamento", options=FORMAS_PAGAMENTO, required=True),
            "Valor": st.column_config.NumberColumn("Valor", min_value=0.01, format="R$ %.2f", required=True),
        }
    else:
        df_base, arquivo, colunas = df_receitas, ARQUIVO_RECEITAS, COLS_RECEITAS
        config = {
            "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY", required=True),
            "Tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS_RECEITA, required=True),
            "Valor": st.column_config.NumberColumn("Valor", min_value=0.01, format="R$ %.2f", required=True),
        }

    editado = st.data_editor(
        df_base, column_config=config, num_rows="dynamic",
        use_container_width=True, hide_index=True, key=f"editor_{alvo}",
    )

    if st.button("💾 Salvar alterações"):
        editado = editado.dropna(subset=["Data", "Valor"]).reset_index(drop=True)
        salvar(editado, arquivo)
        st.session_state["msg"] = "Alterações salvas! ✅"
        st.rerun()

# ==========================================
# ABA 5: ASSESSOR
# ==========================================
with aba_assessor:
    st.header("Assessor Inteligente")
    st.write("Analiso **apenas o dinheiro da conta** (o VR não pode ser investido) e desconto a fatura do cartão em aberto.")

    colchao = st.number_input("Contas a pagar nos próximos dias (colchão)", min_value=0.0, step=100.0, format="%.2f")
    disponivel = saldo_conta - fatura_aberta - colchao

    st.write(f"**Saldo em conta:** {formatar_moeda(saldo_conta)}")
    st.write(f"**Fatura em aberto:** {formatar_moeda(fatura_aberta)}")
    st.write(f"**Disponível para investir:** {formatar_moeda(max(disponivel, 0))}")

    if df_receitas.empty:
        st.info("Registre algum salário/dinheiro na Conta Corrente primeiro!")
    elif disponivel <= 0:
        st.error("⚠️ Não há sobra livre depois de fatura e contas a pagar. Ajuste o orçamento antes de investir.")
    else:
        perfil = st.radio("Seu perfil de investidor:", list(CARTEIRAS), horizontal=True)
        st.subheader("Sugestão de Carteira")
        for nome, pct in CARTEIRAS[perfil]:
            st.write(f"{nome}: **{formatar_moeda(disponivel * pct)}** ({pct:.0%})")

        selic, ipca = buscar_selic(), buscar_ipca_12m()
        if selic:
            mensal_bruto = (1 + selic / 100) ** (1 / 12) - 1
            st.info(
                f"Com a Selic em {selic:.2f}% a.a. (referência para renda fixa pós-fixada), "
                f"{formatar_moeda(disponivel)} renderiam cerca de "
                f"**{formatar_moeda(disponivel * mensal_bruto)} por mês**, valor bruto, antes do IR."
            )
            if ipca is not None:
                juro_real = ((1 + selic / 100) / (1 + ipca / 100) - 1) * 100
                st.caption(f"IPCA em 12 meses: {ipca:.2f}%. Juro real aproximado: {juro_real:.2f}% a.a. "
                           "Dinheiro parado na conta perde para a inflação.")

        media_gastos = df_gastos[df_gastos["Forma de Pagamento"] != "Pagamento de Fatura"]
        if not media_gastos.empty:
            por_mes = media_gastos.groupby(media_gastos["Data"].dt.to_period("M"))["Valor"].sum().mean()
            st.caption(f"Referência: 6 meses de gastos ≈ {formatar_moeda(por_mes * 6)} para a reserva de emergência.")

        st.caption("⚠️ Sugestão genérica e educativa, não é recomendação de investimento. "
                   "Consulte um profissional certificado antes de investir.")

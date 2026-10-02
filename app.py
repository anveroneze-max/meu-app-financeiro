import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Define os arquivos onde os dados serão salvos
ARQUIVO_GASTOS = 'meus_gastos.csv'
ARQUIVO_RECEITAS = 'minhas_receitas.csv'

# Função para criar os arquivos ou atualizar os antigos
def inicializar_dados():
    # Cria arquivo de receitas se não existir
    if not os.path.exists(ARQUIVO_RECEITAS):
        pd.DataFrame(columns=['Data', 'Origem', 'Valor']).to_csv(ARQUIVO_RECEITAS, index=False)
        
    # Cria ou atualiza o arquivo de gastos
    if not os.path.exists(ARQUIVO_GASTOS):
        pd.DataFrame(columns=['Data', 'Categoria', 'Descrição', 'Forma de Pagamento', 'Valor']).to_csv(ARQUIVO_GASTOS, index=False)
    else:
        # Se o arquivo antigo existir, adiciona a coluna nova para não dar erro
        df = pd.read_csv(ARQUIVO_GASTOS)
        if 'Forma de Pagamento' not in df.columns:
            df['Forma de Pagamento'] = 'Não informada (Antigo)'
            df.to_csv(ARQUIVO_GASTOS, index=False)

inicializar_dados()

# Carrega os dados atualizados
df_gastos = pd.read_csv(ARQUIVO_GASTOS)
df_receitas = pd.read_csv(ARQUIVO_RECEITAS)

# Título do aplicativo
st.title("Meu Assessor Financeiro 💰")

# Menu de navegação lateral atualizado
menu = st.sidebar.selectbox("Navegação", [
    "Resumo e Saldo", 
    "Adicionar Gasto", 
    "Adicionar Receita", 
    "Gerenciar Registros", 
    "Assessor de Investimentos"
])

if menu == "Adicionar Gasto":
    st.header("💸 Lançar Novo Gasto")
    
    with st.form("form_gasto", clear_on_submit=True):
        data = st.date_input("Data da Compra", datetime.today())
        categoria = st.selectbox("Categoria", ["Alimentação", "Moradia", "Transporte", "Lazer", "Saúde", "Educação", "Assinaturas", "Outros"])
        descricao = st.text_input("Descrição (Ex: Supermercado, Conta de Luz)")
        forma_pagamento = st.selectbox("Forma de Pagamento", ["Cartão de Crédito", "Cartão de Débito", "PIX", "Dinheiro", "Vale Refeição"])
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        submit = st.form_submit_button("Salvar Gasto")

        if submit:
            novo_gasto = pd.DataFrame([[data, categoria, descricao, forma_pagamento, valor]], 
                                      columns=['Data', 'Categoria', 'Descrição', 'Forma de Pagamento', 'Valor'])
            df_gastos = pd.concat([df_gastos, novo_gasto], ignore_index=True)
            df_gastos.to_csv(ARQUIVO_GASTOS, index=False)
            st.success(f"Gasto de R$ {valor:.2f} com '{descricao}' salvo com sucesso!")

elif menu == "Adicionar Receita":
    st.header("💵 Registrar Entrada de Dinheiro")
    
    with st.form("form_receita", clear_on_submit=True):
        data = st.date_input("Data do Recebimento", datetime.today())
        origem = st.text_input("Origem (Ex: Salário, Pix do amigo, Rendimentos)")
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        submit = st.form_submit_button("Salvar Receita")

        if submit:
            nova_receita = pd.DataFrame([[data, origem, valor]], columns=['Data', 'Origem', 'Valor'])
            df_receitas = pd.concat([df_receitas, nova_receita], ignore_index=True)
            df_receitas.to_csv(ARQUIVO_RECEITAS, index=False)
            st.success(f"Receita de R$ {valor:.2f} salva com sucesso!")

elif menu == "Resumo e Saldo":
    st.header("📊 Meu Painel Financeiro")
    
    # Cálculos
    total_receitas = df_receitas['Valor'].sum() if not df_receitas.empty else 0.0
    total_gastos = df_gastos['Valor'].sum() if not df_gastos.empty else 0.0
    saldo = total_receitas - total_gastos
    
    # Exibe os cartões de resumo
    col1, col2, col3 = st.columns(3)
    col1.metric("Entradas", f"R$ {total_receitas:.2f}")
    col2.metric("Saídas", f"R$ {total_gastos:.2f}")
    col3.metric("Saldo Atual", f"R$ {saldo:.2f}")

    if not df_gastos.empty:
        st.subheader("Histórico de Gastos")
        st.dataframe(df_gastos, use_container_width=True)
        
        # Gráficos em duas colunas
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Gastos por Categoria**")
            st.bar_chart(df_gastos.groupby('Categoria')['Valor'].sum())
        with c2:
            st.write("**Gastos por Forma de Pagamento**")
            st.bar_chart(df_gastos.groupby('Forma de Pagamento')['Valor'].sum())
    else:
        st.info("Nenhum gasto registrado.")

elif menu == "Gerenciar Registros":
    st.header("🗑️ Excluir Registros")
    st.write("Selecione um lançamento digitado errado para excluí-lo.")
    
    tipo = st.radio("O que você deseja excluir?", ["Gastos", "Receitas"])
    
    if tipo == "Gastos":
        if not df_gastos.empty:
            # Cria uma lista legível para o usuário escolher
            opcoes = [f"ID {i} | {row['Data']} | {row['Descrição']} | R$ {row['Valor']}" for i, row in df_gastos.iterrows()]
            escolha = st.selectbox("Selecione o gasto:", opcoes)
            
            if st.button("Excluir Gasto Selecionado"):
                # Pega o ID (índice) do item selecionado e apaga
                idx = int(escolha.split(" | ")[0].replace("ID ", ""))
                df_gastos = df_gastos.drop(idx)
                df_gastos.to_csv(ARQUIVO_GASTOS, index=False)
                st.success("Gasto excluído com sucesso!")
                st.rerun() # Atualiza a tela
        else:
            st.info("Não há gastos para excluir.")
            
    elif tipo == "Receitas":
        if not df_receitas.empty:
            opcoes = [f"ID {i} | {row['Data']} | {row['Origem']} | R$ {row['Valor']}" for i, row in df_receitas.iterrows()]
            escolha = st.selectbox("Selecione a receita:", opcoes)
            
            if st.button("Excluir Receita Selecionada"):
                idx = int(escolha.split(" | ")[0].replace("ID ", ""))
                df_receitas = df_receitas.drop(idx)
                df_receitas.to_csv(ARQUIVO_RECEITAS, index=False)
                st.success("Receita excluída com sucesso!")
                st.rerun() # Atualiza a tela
        else:
            st.info("Não há receitas para excluir.")

elif menu == "Assessor de Investimentos":
    st.header("🧠 Assessor Inteligente")
    
    total_receitas = df_receitas['Valor'].sum() if not df_receitas.empty else 0.0
    total_gastos = df_gastos['Valor'].sum() if not df_gastos.empty else 0.0
    sobra = total_receitas - total_gastos
    
    st.write("Eu analiso seu saldo atual e crio um plano de investimentos focado no que sobrou da sua conta.")
    st.write(f"**Saldo Atual Disponível:** R$ {sobra:.2f}")

    if total_receitas > 0:
        if sobra <= 0:
            st.error("⚠️ Atenção! Você gastou tudo ou mais do que ganhou. O foco agora deve ser organizar o orçamento e cortar despesas antes de investir.")
        else:
            st.success(f"Excelente! Você tem **R$ {sobra:.2f}** livres para investir.")

            perfil = st.radio("Qual é o seu perfil de investidor atual?", 
                              ["Conservador (Não quero perder dinheiro, foco na Reserva de Emergência)", 
                               "Moderado (Aceito um pouco de risco para ganhar mais a longo prazo)", 
                               "Arrojado (Já tenho reserva e quero investir em ações/cripto focando no longo prazo)"])

            st.subheader("Recomendação do Assessor:")
            
            if "Conservador" in perfil:
                st.write(f"🛡️ **Reserva de Emergência / Renda Fixa:** R$ {sobra * 0.80:.2f} (80%)")
                st.write(f"🏢 **Fundos Imobiliários (FIIs - geram renda mensal):** R$ {sobra * 0.20:.2f} (20%)")
            
            elif "Moderado" in perfil:
                st.write(f"🛡️ **Renda Fixa Atrelada à Inflação (Tesouro IPCA+):** R$ {sobra * 0.50:.2f} (50%)")
                st.write(f"🏢 **Fundos Imobiliários (FIIs):** R$ {sobra * 0.30:.2f} (30%)")
                st.write(f"📈 **Ações Brasileiras ou ETFs (Ex: BOVA11):** R$ {sobra * 0.20:.2f} (20%)")
            
            else:
                st.write(f"📈 **Ações e ETFs Globais (Ex: IVVB11 / WRLD11):** R$ {sobra * 0.40:.2f} (40%)")
                st.write(f"🏢 **Fundos Imobiliários e Fiagros:** R$ {sobra * 0.30:.2f} (30%)")
                st.write(f"🛡️ **Renda Fixa (Caixa para oportunidades):** R$ {sobra * 0.20:.2f} (20%)")
                st.write(f"₿ **Criptomoedas (Bitcoin/Ethereum):** R$ {sobra * 0.10:.2f} (10%)")
    else:
        st.info("Registre alguma receita primeiro para que eu possa avaliar seu saldo!")

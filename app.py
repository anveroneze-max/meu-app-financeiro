import streamlit as st
import pandas as pd
import os
import time  # <-- Biblioteca nova para dar um tempinho antes de atualizar
from datetime import datetime

st.set_page_config(page_title="App Financeiro", page_icon="💰", layout="centered")

# Define os arquivos onde os dados serão salvos
ARQUIVO_GASTOS = 'meus_gastos.csv'
ARQUIVO_RECEITAS = 'minhas_receitas.csv'

# Função para criar os arquivos ou atualizar os antigos
def inicializar_dados():
    if not os.path.exists(ARQUIVO_RECEITAS):
        pd.DataFrame(columns=['Data', 'Tipo', 'Origem', 'Valor']).to_csv(ARQUIVO_RECEITAS, index=False)
    else:
        df_rec = pd.read_csv(ARQUIVO_RECEITAS)
        if 'Tipo' not in df_rec.columns:
            df_rec['Tipo'] = 'Conta Corrente'
            df_rec.to_csv(ARQUIVO_RECEITAS, index=False)
            
    if not os.path.exists(ARQUIVO_GASTOS):
        pd.DataFrame(columns=['Data', 'Categoria', 'Descrição', 'Forma de Pagamento', 'Valor']).to_csv(ARQUIVO_GASTOS, index=False)
    else:
        df = pd.read_csv(ARQUIVO_GASTOS)
        if 'Forma de Pagamento' not in df.columns:
            df['Forma de Pagamento'] = 'Não informada (Antigo)'
            df.to_csv(ARQUIVO_GASTOS, index=False)

inicializar_dados()

# Carrega os dados logo ao abrir o app
df_gastos = pd.read_csv(ARQUIVO_GASTOS)
df_receitas = pd.read_csv(ARQUIVO_RECEITAS)

st.title("Meu Assessor 💰")

aba_resumo, aba_gastos, aba_receitas, aba_gerenciar, aba_assessor = st.tabs([
    "📊 Resumo", 
    "💸 Gastos", 
    "💵 Receitas", 
    "🗑️ Editar", 
    "🧠 Assessor"
])

# ==========================================
# CONTEÚDO DA ABA 1: RESUMO 
# ==========================================
with aba_resumo:
    st.header("Painel Financeiro")
    
    entradas_vr = df_receitas[df_receitas['Tipo'] == 'Vale Refeição']['Valor'].sum() if not df_receitas.empty else 0.0
    saidas_vr = df_gastos[df_gastos['Forma de Pagamento'] == 'Vale Refeição']['Valor'].sum() if not df_gastos.empty else 0.0
    saldo_vr = entradas_vr - saidas_vr
    
    entradas_conta = df_receitas[df_receitas['Tipo'] != 'Vale Refeição']['Valor'].sum() if not df_receitas.empty else 0.0
    saidas_conta = df_gastos[df_gastos['Forma de Pagamento'] != 'Vale Refeição']['Valor'].sum() if not df_gastos.empty else 0.0
    saldo_conta = entradas_conta - saidas_conta
    
    col1, col2 = st.columns(2)
    col1.metric("💳 Saldo em Conta", f"R$ {saldo_conta:.2f}")
    col2.metric("🍽️ Saldo VR", f"R$ {saldo_vr:.2f}")
    
    st.divider()

    if not df_gastos.empty:
        st.subheader("Histórico de Gastos")
        st.dataframe(df_gastos, use_container_width=True)
        
        st.write("**Gastos por Categoria**")
        st.bar_chart(df_gastos.groupby('Categoria')['Valor'].sum())
    else:
        st.info("Nenhum gasto registrado.")

# ==========================================
# CONTEÚDO DA ABA 2: GASTOS (CORRIGIDA)
# ==========================================
with aba_gastos:
    st.header("Lançar Gasto")
    
    with st.form("form_gasto", clear_on_submit=True):
        data = st.date_input("Data da Compra", datetime.today())
        categoria = st.selectbox("Categoria", ["Alimentação", "Moradia", "Transporte", "Lazer", "Saúde", "Educação", "Assinaturas", "Outros"])
        descricao = st.text_input("Descrição (Ex: Supermercado)")
        forma_pagamento = st.selectbox("Forma de Pagamento", ["Cartão de Crédito", "Cartão de Débito", "PIX", "Dinheiro", "Vale Refeição"])
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        submit = st.form_submit_button("Salvar Gasto")

        if submit:
            novo_gasto = pd.DataFrame([[data, categoria, descricao, forma_pagamento, valor]], 
                                      columns=['Data', 'Categoria', 'Descrição', 'Forma de Pagamento', 'Valor'])
            df_gastos = pd.concat([df_gastos, novo_gasto], ignore_index=True)
            df_gastos.to_csv(ARQUIVO_GASTOS, index=False)
            
            st.success(f"Gasto salvo com sucesso!")
            time.sleep(1) # Aguarda 1 segundo para você ler a mensagem
            st.rerun()    # Atualiza o app automaticamente!

# ==========================================
# CONTEÚDO DA ABA 3: RECEITAS (CORRIGIDA)
# ==========================================
with aba_receitas:
    st.header("Entrada de Dinheiro / Benefício")
    
    with st.form("form_receita", clear_on_submit=True):
        tipo_entrada = st.selectbox("Onde esse valor entrou?", ["Conta Corrente (Dinheiro, Pix, Salário)", "Vale Refeição"])
        data = st.date_input("Data do Recebimento", datetime.today())
        origem = st.text_input("Descrição (Ex: Salário, Recarga do VR)")
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        submit = st.form_submit_button("Salvar Entrada")

        if submit:
            nova_receita = pd.DataFrame([[data, tipo_entrada, origem, valor]], columns=['Data', 'Tipo', 'Origem', 'Valor'])
            df_receitas = pd.concat([df_receitas, nova_receita], ignore_index=True)
            df_receitas.to_csv(ARQUIVO_RECEITAS, index=False)
            
            st.success(f"Entrada salva com sucesso!")
            time.sleep(1) # Aguarda 1 segundo
            st.rerun()    # Atualiza o app automaticamente!

# ==========================================
# CONTEÚDO DA ABA 4: GERENCIAR
# ==========================================
with aba_gerenciar:
    st.header("Excluir Registros")
    
    tipo_del = st.radio("O que você deseja excluir?", ["Gastos", "Receitas"])
    
    if tipo_del == "Gastos":
        if not df_gastos.empty:
            opcoes = [f"ID {i} | {row['Data']} | {row['Descrição']} | R$ {row['Valor']}" for i, row in df_gastos.iterrows()]
            escolha = st.selectbox("Selecione o gasto:", opcoes)
            
            if st.button("Excluir Gasto Selecionado"):
                idx = int(escolha.split(" | ")[0].replace("ID ", ""))
                df_gastos = df_gastos.drop(idx)
                df_gastos.to_csv(ARQUIVO_GASTOS, index=False)
                st.success("Gasto Excluído!")
                time.sleep(1)
                st.rerun()
        else:
            st.info("Não há gastos para excluir.")
            
    elif tipo_del == "Receitas":
        if not df_receitas.empty:
            opcoes = [f"ID {i} | {row['Data']} | {row.get('Tipo', 'Conta')} - {row['Origem']} | R$ {row['Valor']}" for i, row in df_receitas.iterrows()]
            escolha = st.selectbox("Selecione a receita:", opcoes)
            
            if st.button("Excluir Receita Selecionada"):
                idx = int(escolha.split(" | ")[0].replace("ID ", ""))
                df_receitas = df_receitas.drop(idx)
                df_receitas.to_csv(ARQUIVO_RECEITAS, index=False)
                st.success("Receita Excluída!")
                time.sleep(1)
                st.rerun()
        else:
            st.info("Não há receitas para excluir.")

# ==========================================
# CONTEÚDO DA ABA 5: ASSESSOR
# ==========================================
with aba_assessor:
    st.header("Assessor Inteligente")
    
    entradas_conta = df_receitas[df_receitas['Tipo'] != 'Vale Refeição']['Valor'].sum() if not df_receitas.empty else 0.0
    saidas_conta = df_gastos[df_gastos['Forma de Pagamento'] != 'Vale Refeição']['Valor'].sum() if not df_gastos.empty else 0.0
    sobra_real = entradas_conta - saidas_conta
    
    st.write("Eu analiso **apenas o seu saldo em dinheiro (fora o VR)** para recomendar investimentos, afinal, o Vale Refeição não pode ser investido.")
    st.write(f"**Saldo em Conta (Dinheiro Disponível):** R$ {sobra_real:.2f}")

    if entradas_conta > 0:
        if sobra_real <= 0:
            st.error("⚠️ Você gastou todo o seu dinheiro da conta ou está no negativo. Ajuste o orçamento antes de investir.")
        else:
            st.success(f"Você tem **R$ {sobra_real:.2f}** livres na conta para investir.")
            perfil = st.radio("Seu perfil de investidor:", 
                              ["Conservador", "Moderado", "Arrojado"])
            st.subheader("Recomendação de Carteira:")
            
            if "Conservador" in perfil:
                st.write(f"🛡️ **Reserva de Emergência:** R$ {sobra_real * 0.80:.2f} (80%)")
                st.write(f"🏢 **Fundos Imobiliários:** R$ {sobra_real * 0.20:.2f} (20%)")
            elif "Moderado" in perfil:
                st.write(f"🛡️ **Tesouro IPCA+:** R$ {sobra_real * 0.50:.2f} (50%)")
                st.write(f"🏢 **Fundos Imobiliários:** R$ {sobra_real * 0.30:.2f} (30%)")
                st.write(f"📈 **Ações/ETFs:** R$ {sobra_real * 0.20:.2f} (20%)")
            else:
                st.write(f"📈 **Ações e ETFs Globais:** R$ {sobra_real * 0.40:.2f} (40%)")
                st.write(f"🏢 **Fundos Imobiliários e Fiagros:** R$ {sobra_real * 0.30:.2f} (30%)")
                st.write(f"🛡️ **Renda Fixa:** R$ {sobra_real * 0.20:.2f} (20%)")
                st.write(f"₿ **Criptomoedas:** R$ {sobra_real * 0.10:.2f} (10%)")
    else:
        st.info("Registre algum salário/dinheiro na Conta Corrente primeiro!")

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Define o nome do arquivo onde os dados serão salvos localmente
ARQUIVO_DADOS = 'meus_gastos.csv'

# Cria o arquivo vazio caso seja a primeira vez abrindo o app
if not os.path.exists(ARQUIVO_DADOS):
    df = pd.DataFrame(columns=['Data', 'Categoria', 'Descrição', 'Valor'])
    df.to_csv(ARQUIVO_DADOS, index=False)

# Título do aplicativo
st.title("Meu Assessor Financeiro 💰")

# Menu de navegação lateral
menu = st.sidebar.selectbox("Navegação", ["Adicionar Gasto", "Resumo do Mês", "Assessor de Investimentos"])

if menu == "Adicionar Gasto":
    st.header("Lançar Novo Gasto")
    
    # Formulário para você digitar os gastos manuais
    with st.form("form_gasto", clear_on_submit=True):
        data = st.date_input("Data da Compra", datetime.today())
        categoria = st.selectbox("Categoria", ["Alimentação", "Moradia", "Transporte", "Lazer", "Saúde", "Educação", "Assinaturas", "Outros"])
        descricao = st.text_input("Descrição (Ex: Supermercado, Conta de Luz)")
        valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
        submit = st.form_submit_button("Salvar Gasto")

        if submit:
            # Salva o novo gasto no arquivo CSV
            novo_gasto = pd.DataFrame([[data, categoria, descricao, valor]], columns=['Data', 'Categoria', 'Descrição', 'Valor'])
            df = pd.read_csv(ARQUIVO_DADOS)
            df = pd.concat([df, novo_gasto], ignore_index=True)
            df.to_csv(ARQUIVO_DADOS, index=False)
            st.success(f"Gasto de R$ {valor:.2f} com '{descricao}' salvo com sucesso!")

elif menu == "Resumo do Mês":
    st.header("Meus Gastos")
    df = pd.read_csv(ARQUIVO_DADOS)
    
    if not df.empty:
        # Mostra a tabela com todos os gastos
        st.dataframe(df, use_container_width=True)
        
        # Calcula o total
        total = df['Valor'].sum()
        st.metric("Total Gasto Registrado", f"R$ {total:.2f}")

        # Gráfico de barras por categoria
        st.subheader("Gastos por Categoria")
        gastos_cat = df.groupby('Categoria')['Valor'].sum()
        st.bar_chart(gastos_cat)
    else:
        st.info("Você ainda não cadastrou nenhum gasto.")

elif menu == "Assessor de Investimentos":
    st.header("🧠 Assessor Inteligente")
    st.write("Vou analisar seus gastos e sugerir como investir o que sobrou.")
    
    renda = st.number_input("Qual foi sua Renda Total este mês? (R$)", min_value=0.0, format="%.2f")
    
    df = pd.read_csv(ARQUIVO_DADOS)
    total_gasto = df['Valor'].sum() if not df.empty else 0.0

    st.write(f"**Total Gasto:** R$ {total_gasto:.2f}")
    sobra = renda - total_gasto

    if renda > 0:
        if sobra <= 0:
            st.error("⚠️ Atenção! Seus gastos ultrapassaram ou igualaram sua renda. O foco agora deve ser organizar o orçamento e cortar despesas antes de investir.")
        else:
            st.success(f"Excelente! Sobraram **R$ {sobra:.2f}** para investir este mês.")

            perfil = st.radio("Qual é o seu perfil de risco atual?", 
                              ["Conservador (Não quero perder dinheiro, foco na Reserva de Emergência)", 
                               "Moderado (Aceito um pouco de risco para ganhar mais a longo prazo)", 
                               "Arrojado (Já tenho reserva e quero investir em ações/cripto focando no longo prazo)"])

            st.subheader("Recomendação de Alocação:")
            st.write("Baseado no valor que sobrou, aqui está uma sugestão de divisão de aportes para este mês:")

            # Lógica simples de assessoria financeira
            if "Conservador" in perfil:
                st.write(f"🛡️ **Reserva de Emergência / Renda Fixa (Tesouro Selic ou CDB 100% CDI):** R$ {sobra * 0.80:.2f} (80%)")
                st.write(f"🏢 **Fundos Imobiliários (FIIs - Menos voláteis, geram renda mensal):** R$ {sobra * 0.20:.2f} (20%)")
            
            elif "Moderado" in perfil:
                st.write(f"🛡️ **Renda Fixa Atrelada à Inflação (Tesouro IPCA+):** R$ {sobra * 0.50:.2f} (50%)")
                st.write(f"🏢 **Fundos Imobiliários (FIIs):** R$ {sobra * 0.30:.2f} (30%)")
                st.write(f"📈 **Ações Brasileiras ou ETFs (Ex: BOVA11):** R$ {sobra * 0.20:.2f} (20%)")
            
            else:
                st.write(f"📈 **Ações e ETFs Globais (Ex: IVVB11 / WRLD11):** R$ {sobra * 0.40:.2f} (40%)")
                st.write(f"🏢 **Fundos Imobiliários e Fiagros:** R$ {sobra * 0.30:.2f} (30%)")
                st.write(f"🛡️ **Renda Fixa (Caixa para oportunidades):** R$ {sobra * 0.20:.2f} (20%)")
                st.write(f"₿ **Criptomoedas (Bitcoin/Ethereum):** R$ {sobra * 0.10:.2f} (10%)")
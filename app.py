
import streamlit as st
from openai import OpenAI
from datetime import datetime
from dateutil import parser

st.set_page_config(page_title="MVP IA - Precificação de Crédito", layout="centered")
st.title("IA para Precificação de Antecipação de Crédito")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

with st.form("formulario_operacao"):
    nome_cliente = st.text_input("Nome do cliente")
    valor = st.number_input("Valor da operação (R$)", min_value=0.0, format="%.2f")
    data_operacao = st.date_input("Data da operação", value=datetime.today(), format="DD/MM/YYYY")
    data_vencimento = st.date_input("Data de vencimento", format="DD/MM/YYYY")
    rating = st.slider("Rating do cliente (0 = risco alto, 100 = risco baixo)", 0, 100, 80)
    margem_desejada = st.number_input("Margem desejada (%)", min_value=0.0, value=1.0)
    custo_capital = st.number_input("Custo do capital (%)", min_value=0.0, value=1.5)
    taxa_concorrencia = st.number_input("Taxa da concorrência (%)", min_value=0.0, value=4.5)
    enviar = st.form_submit_button("Simular")

if enviar:
    prazo = (data_vencimento - data_operacao).days
    risco = (100 - rating) / 100  # risco de 0 (seguro) a 1 (muito arriscado)

    # Ajuste por valor da operação: quanto maior, menor o impacto (até -0.5%)
    ajuste_valor = max(0.5 - (valor / 100000), 0)

    # Novo cálculo da taxa ideal
    taxa_ideal = round(custo_capital + margem_desejada + (risco * 2.0) + ajuste_valor, 2)

    margem_estimada = round(taxa_ideal - custo_capital, 2)
    retorno_esperado = round((taxa_ideal - custo_capital) / 100 * valor, 2)

    # Comparação realista com a taxa da concorrência
    if taxa_ideal > taxa_concorrencia + 0.05:
        status = "Acima do mercado"
    elif taxa_ideal < taxa_concorrencia - 0.05:
        status = "Abaixo do mercado"
    else:
        status = "Na média do mercado"

    if rating >= 80:
        risco_class = "Baixo"
    elif rating >= 60:
        risco_class = "Moderado"
    else:
        risco_class = "Alto"

    st.subheader("Resultado da Simulação")
    st.write(f"**Prazo:** {prazo} dias")
    st.write(f"**Taxa ideal sugerida:** {taxa_ideal}%")
    st.write(f"**Margem estimada:** {margem_estimada}%")
    st.write(f"**Retorno esperado:** R$ {retorno_esperado}")
    st.write(f"**Comparação com concorrência:** {status}")
    st.write(f"**Classificação de risco:** {risco_class}")

    with st.spinner("Gerando explicação da IA..."):
        prompt = f"""
        Considere uma operação de antecipação de crédito no valor de R$ {valor:.2f}, com prazo de {prazo} dias.
        O rating do cliente é {rating}/100 ({risco_class} risco), o custo de capital da operação é {custo_capital}%,
        e a margem desejada é {margem_desejada}%.
        A taxa média praticada pelo mercado é de {taxa_concorrencia}%, e a taxa ideal sugerida foi de {taxa_ideal}%,
        com retorno estimado de R$ {retorno_esperado:.2f} e status competitivo: {status}.
        Gere uma explicação curta e profissional para justificar essa taxa sugerida, levando em conta risco x retorno.
        """

        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=250
        )

        explicacao = resposta.choices[0].message.content
        st.markdown("### Justificativa da IA")
        st.success(explicacao)

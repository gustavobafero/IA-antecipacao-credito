
import streamlit as st
from openai import OpenAI, RateLimitError
from datetime import datetime
import pandas as pd
import os
import matplotlib.pyplot as plt
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="IA Crédito + Risco de Inadimplência", layout="centered")
st.title("IA para Precificação de Antecipação de Crédito")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
storage_file = "simulacoes_credito.csv"

def gerar_pdf(data_dict, explicacao):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório de Precificação e Risco de Crédito", ln=True, align='C')
    pdf.ln(10)
    for chave, valor in data_dict.items():
        pdf.cell(200, 10, txt=f"{chave}: {valor}", ln=True)
    pdf.ln(10)
    pdf.multi_cell(200, 10, txt="Justificativa da IA: " + explicacao)
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

st.header("1. Informações da Operação")
form = st.form("formulario_operacao")
with form:
    nome_cliente = st.text_input("Nome do cliente")
    cnpj_cliente = st.text_input("CNPJ do cliente (opcional)")
    valor = st.number_input("Valor da operação (R$)", min_value=0.0, format="%.2f")
    data_operacao = st.date_input("Data da operação", value=datetime.today(), format="DD/MM/YYYY")
    data_vencimento = st.date_input("Data de vencimento", format="DD/MM/YYYY")
    rating = st.slider("Rating do cliente (0 = risco alto, 100 = risco baixo)", 0, 100, 80)
    margem_desejada = st.number_input("Margem desejada (%)", min_value=0.0, value=1.0)
    custo_capital = st.number_input("Custo do capital (%)", min_value=0.0, value=1.5)
    taxa_concorrencia = st.number_input("Taxa da concorrência (%)", min_value=0.0, value=4.5)

    st.markdown("---")
    st.subheader("2. Avaliação de Risco de Inadimplência (manual)")

    score_serasa = st.number_input("Score Serasa (0 a 1000)", min_value=0, max_value=1000, value=750)
    idade_empresa = st.number_input("Idade da empresa (anos)", min_value=0, value=5)
    protestos = st.selectbox("Possui protestos ou dívidas públicas?", ["Não", "Sim"])
    faturamento = st.number_input("Último faturamento declarado (R$)", min_value=0.0, format="%.2f")
    data_faturamento = st.date_input("Data do último faturamento")

    enviar = st.form_submit_button("Simular")

if enviar:
    prazo = (data_vencimento - data_operacao).days
    risco = (100 - rating) / 100
    ajuste_valor = max(0.5 - (valor / 100000), 0)
    taxa_ideal = round(custo_capital + margem_desejada + (risco * 2.0) + ajuste_valor, 2)
    margem_estimada = round(taxa_ideal - custo_capital, 2)
    retorno_esperado = round((taxa_ideal - custo_capital) / 100 * valor, 2)

    if taxa_ideal > taxa_concorrencia + 0.05:
        status = "Acima do mercado"
    elif taxa_ideal < taxa_concorrencia - 0.05:
        status = "Abaixo do mercado"
    else:
        status = "Na média do mercado"

    risco_score = 0 if score_serasa >= 800 else 1 if score_serasa < 600 else 0.5
    risco_idade = 0 if idade_empresa >= 5 else 0.5
    risco_protesto = 1 if protestos == "Sim" else 0
    risco_faturamento = 0 if faturamento >= 500000 else 0.5

    risco_total = (risco_score * 0.4 + risco_idade * 0.2 + risco_protesto * 0.25 + risco_faturamento * 0.15) * 100
    risco_total = round(risco_total, 2)

    cor_risco = "🟢 Baixo" if risco_total <= 30 else "🟡 Moderado" if risco_total <= 60 else "🔴 Alto"

    st.markdown("## Resultado da Simulação")
    st.write(f"**Prazo da operação:** {prazo} dias")
    st.write(f"**Taxa ideal sugerida:** {taxa_ideal}%")
    st.write(f"**Margem estimada:** {margem_estimada}%")
    st.write(f"**Retorno esperado:** R$ {retorno_esperado}")
    st.write(f"**Comparação com concorrência:** {status}")
    st.write(f"**Classificação de risco (IA):** {'Baixo' if rating >= 80 else 'Moderado' if rating >= 60 else 'Alto'}")
    st.write(f"**Risco de inadimplência (manual):** {cor_risco} ({risco_total}%)")

    dados_relatorio = {
        "Cliente": nome_cliente,
        "CNPJ": cnpj_cliente,
        "Valor da operação": f"R$ {valor:.2f}",
        "Prazo (dias)": prazo,
        "Taxa Ideal (%)": taxa_ideal,
        "Margem (%)": margem_estimada,
        "Retorno Esperado (R$)": retorno_esperado,
        "Status Concorrência": status,
        "Risco de inadimplência": f"{risco_total}% ({cor_risco})"
    }

    try:
        prompt = (
            f"Considere uma operação de antecipação de crédito no valor de R$ {valor:.2f}, com prazo de {prazo} dias. "
            f"O rating do cliente é {rating}/100, o custo de capital da operação é {custo_capital}%, "
            f"e a margem desejada é {margem_desejada}%. A taxa da concorrência é {taxa_concorrencia}%, "
            f"e a taxa ideal sugerida foi de {taxa_ideal}% (status: {status}). "
            f"A avaliação de risco de inadimplência resultou em {risco_total}% ({cor_risco}). "
            f"Gere uma explicação curta e profissional considerando risco x retorno."
        )

        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=250
        )
        explicacao = resposta.choices[0].message.content
        st.markdown("### Justificativa da IA")
        st.success(explicacao)

        fig, ax = plt.subplots()
        ax.scatter(risco_total, retorno_esperado, color="blue", s=100)
        ax.set_xlabel("Risco de Inadimplência (%)")
        ax.set_ylabel("Retorno Esperado (R$)")
        ax.set_title("Risco x Retorno")
        ax.grid(True)

        # Salva a imagem como PNG e exibe
        buffer = BytesIO()
        fig.savefig(buffer, format="png")
        buffer.seek(0)
        st.image(buffer, caption="Análise Gráfica: Risco x Retorno", use_column_width=True)

        # Geração do PDF
        pdf_bytes = gerar_pdf(dados_relatorio, explicacao)
        st.download_button("📄 Baixar relatório em PDF", data=pdf_bytes, file_name="relatorio_credito.pdf")

    except RateLimitError:
        st.warning("⚠️ A OpenAI está com excesso de requisições no momento. Aguarde alguns instantes e tente novamente.")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao chamar a IA: {e}")

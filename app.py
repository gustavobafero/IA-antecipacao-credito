import streamlit as st
from openai import OpenAI, RateLimitError
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from io import BytesIO
from fpdf import FPDF
import unicodedata
import tempfile

st.set_page_config(page_title="IA Crédito + Risco de Inadimplência", layout="centered")
st.title("IA para Precificação de Antecipação de Crédito")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def clean_text(text):
    return unicodedata.normalize('NFKD', text).encode('latin1', 'ignore').decode('latin1')

def gerar_pdf(data_dict, grafico_risco_bytes=None, grafico_fatores_bytes=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatorio de Precificacao e Risco de Credito", ln=True, align='C')
    pdf.ln(10)
    for chave, valor in data_dict.items():
        linha = f"{chave}: {valor}"
        pdf.cell(200, 10, txt=clean_text(linha), ln=True)
    pdf.ln(10)
    pdf.ln(5)

    if grafico_risco_bytes and grafico_fatores_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_risco:
            tmp_risco.write(grafico_risco_bytes.getvalue())
            tmp_risco_path = tmp_risco.name
        pdf.image(tmp_risco_path, w=180)
        pdf.ln(5)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_fatores:
            tmp_fatores.write(grafico_fatores_bytes.getvalue())
            tmp_fatores_path = tmp_fatores.name
        pdf.image(tmp_fatores_path, w=180)

    pdf_data = pdf.output(dest='S').encode('latin1')
    return BytesIO(pdf_data)

def gerar_justificativa_ia(prompt):
    st.info("🔍 Enviando solicitação à IA...")
    try:
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=300
        )
        st.success("✅ Justificativa recebida com sucesso!")
        return resposta.choices[0].message.content.strip()
    except RateLimitError as e:
        st.warning("⚠️ A IA está temporariamente indisponível (erro de cota). O relatório continuará sem justificativa da IA.")
        return "A OpenAI está com excesso de requisições no momento. Tente novamente mais tarde."
    except Exception as e:
        st.warning("⚠️ Erro inesperado ao consultar a IA. O relatório continuará sem justificativa da IA.")
        return "Não foi possível gerar a justificativa neste momento. Use a análise manual como apoio."

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
    data_faturamento = st.date_input("Data do último faturamento", format="DD/MM/YYYY")

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

                
    # Gráfico Risco x Retorno
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(risco_total, retorno_esperado, color="#1f77b4", s=150, edgecolors="black", linewidths=1.2, zorder=3)
    ax.set_xlabel("Risco de Inadimplência (%)", fontsize=12)
    ax.set_ylabel("Retorno Esperado (R$)", fontsize=12)
    ax.set_title("Risco x Retorno", fontsize=13, fontweight='bold')
    ax.grid(True, linestyle="--", alpha=0.6, zorder=0)
    ax.annotate(f"({risco_total:.1f}%, R$ {retorno_esperado:.2f})", (risco_total, retorno_esperado),
                textcoords="offset points", xytext=(10, 10), ha='left', fontsize=10,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.7))
    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    buffer.seek(0)
    st.pyplot(fig)

    # Gráfico de Análise de Risco
    st.markdown("### Análise de Risco de Inadimplência")
    fatores = ["Score Serasa", "Idade da Empresa", "Protestos", "Faturamento"]
    pesos = [risco_score * 0.4, risco_idade * 0.2, risco_protesto * 0.25, risco_faturamento * 0.15]
    pesos = [p * 100 for p in pesos]
    fig_risco, ax_risco = plt.subplots(figsize=(6, 4))
    bars = ax_risco.bar(fatores, pesos, color="#1f77b4", edgecolor="black", zorder=3)
    for bar in bars:
        height = bar.get_height()
        ax_risco.annotate(f'{height:.1f}%',
                          xy=(bar.get_x() + bar.get_width() / 2, height),
                          xytext=(0, 5),
                          textcoords="offset points",
                          ha='center', va='bottom',
                          fontsize=10,
                          bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.7))
    ax_risco.set_ylabel("Peso na Composição do Risco (%)", fontsize=12)
    ax_risco.set_title("Análise de Risco de Inadimplência", fontsize=13, fontweight='bold')
    fig_risco.subplots_adjust(top=0.85)
    ax_risco.yaxis.set_major_formatter(PercentFormatter())
    ax_risco.grid(True, linestyle="--", alpha=0.6, zorder=0)
    buffer_risco = BytesIO()
    fig_risco.savefig(buffer_risco, format="png", bbox_inches="tight")
    buffer_risco.seek(0)
    st.pyplot(fig_risco)

    dados_relatorio = {
        "Cliente": nome_cliente,
        "CNPJ": cnpj_cliente,
        "Valor da operação": f"R$ {valor:.2f}",
        "Prazo (dias)": prazo,
        "Taxa Ideal (%)": taxa_ideal,
        "Margem (%)": margem_estimada,
        "Retorno Esperado (R$)": retorno_esperado,
        "Status Concorrência": status,
        "Risco de inadimplência": f"{risco_total}% ({cor_risco})",
        "Data do último faturamento": data_faturamento.strftime('%d/%m/%Y')
    }

    pdf_bytes = gerar_pdf(dados_relatorio, buffer, buffer_risco)
    st.download_button("📄 Baixar relatório em PDF", data=pdf_bytes, file_name="relatorio_credito.pdf")

import streamlit as st
from openai import OpenAI, RateLimitError
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from io import BytesIO
from fpdf import FPDF
import unicodedata
import tempfile
import locale

# Configura localização para formatação brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')  # fallback


def formatar_moeda(valor):
    try:
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except:
        return f"R$ {valor:.2f}".replace(".", ",")


def calcular_preco_minimo(custo_base, risco_inadimplencia, margem_desejada_percentual):
    ajuste_risco = 1 + risco_inadimplencia
    margem = 1 + (margem_desejada_percentual / 100)
    return custo_base * ajuste_risco * margem

# Configuração da página
st.set_page_config(page_title="IA Crédito + Risco de Inadimplência", layout="centered")
st.title("IA para Precificação de Antecipação de Crédito")

# Cliente OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def clean_text(text):
    return unicodedata.normalize('NFKD', text).encode('latin1', 'ignore').decode('latin1')


def gerar_pdf(data_dict, grafico_risco_bytes=None, grafico_fatores_bytes=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório de Precificação e Risco de Crédito", ln=True, align='C')
    pdf.ln(10)
    for chave, valor in data_dict.items():
        pdf.cell(0, 8, txt=clean_text(f"{chave}: {valor}"), ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", style='I', size=11)
    pdf.multi_cell(0, 8, clean_text(
        "Como a IA chegou no preço mínimo? "
        "Ela considera o valor do empréstimo, protege-se do risco e adiciona uma margem de lucro. "
        "Assim, garante segurança e rentabilidade."))

    # Página de gráfico de risco x retorno
    pdf.add_page()
    if grafico_risco_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_risco:
            tmp_risco.write(grafico_risco_bytes.getvalue())
            tmp_risco_path = tmp_risco.name
        pdf.image(tmp_risco_path, w=180)
        pdf.ln(5)
    pdf.multi_cell(0, 8, clean_text(
        "Gráfico: retorno esperado vs. risco de inadimplência. Mais alto é melhor retorno; mais à direita é maior risco."))

    # Página de fatores de risco
    pdf.add_page()
    if grafico_fatores_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_fatores:
            tmp_fatores.write(grafico_fatores_bytes.getvalue())
            tmp_fatores_path = tmp_fatores.name
        pdf.image(tmp_fatores_path, w=180)
        pdf.ln(5)
    pdf.multi_cell(0, 8, clean_text(
        "Fatores de risco: peso de cada indicador no cálculo do risco de inadimplência."))

    return BytesIO(pdf.output(dest='S').encode('latin1'))

# Formulário de entrada
st.header("1. Informações da Operação")
with st.form("formulario_operacao"):
    st.subheader("1. Dados da Operação")
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
    st.subheader("2. Avaliação de Risco de Inadimplência (Manual)")
    score_serasa = st.number_input("Score Serasa (0 a 1000)", 0, 1000, 750)
    idade_empresa = st.number_input("Idade da empresa (anos)", 0, 100, 5)
    protestos = st.selectbox("Possui protestos ou dívidas públicas?", ["Não", "Sim"])
    faturamento = st.number_input("Último faturamento declarado (R$)", min_value=0.0, format="%.2f")
    data_faturamento = st.date_input("Data do último faturamento", format="DD/MM/YYYY")
    enviar = st.form_submit_button("Simular")

# Processamento e exibição
if enviar:
    # Cálculos gerais
    prazo = (data_vencimento - data_operacao).days
    risco = (100 - rating) / 100
    ajuste_valor = max(0.5 - (valor / 100000), 0)
    taxa_ideal = round(custo_capital + margem_desejada + (risco * 2.0) + ajuste_valor, 2)
    margem_estimada = round(taxa_ideal - custo_capital, 2)
    retorno_esperado = round(valor * (margem_estimada / 100), 2)
    preco_sugerido = calcular_preco_minimo(valor, risco, margem_desejada)

    # Exibição dos resultados
    st.markdown("## Resultado da Simulação")
    st.write(f"**Prazo da operação:** {prazo} dias")
    st.write(f"**Taxa ideal sugerida:** {taxa_ideal}%")
    st.write(f"**Margem estimada:** {margem_estimada}%")
    st.write(f"**Retorno esperado:** {formatar_moeda(retorno_esperado)}")
    st.write(
        f"**Comparação com concorrência:** "
        f"{'Acima do mercado' if taxa_ideal > taxa_concorrencia + 0.05 else 'Abaixo do mercado' if taxa_ideal < taxa_concorrencia - 0.05 else 'Na média do mercado'}"
    )
    st.markdown(f"### 💰 Preço sugerido pela IA: **{formatar_moeda(preco_sugerido)}**")
    st.markdown("---")

    # Avaliação manual Serasa separada
    st.subheader("Avaliação de Risco de Inadimplência (Manual)")
    risco_score = 0 if score_serasa >= 800 else 1 if score_serasa < 600 else 0.5
    risco_idade = 0 if idade_empresa >= 5 else 0.5
    risco_protesto = 1 if protestos == "Sim" else 0
    risco_faturamento = 0 if faturamento >= 500000 else 0.5
    risco_total = round((risco_score * 0.4 + risco_idade * 0.2 + risco_protesto * 0.25 + risco_faturamento * 0.15) * 100, 2)
    cor_risco = "🟢 Baixo" if risco_total <= 30 else "🟡 Moderado" if risco_total <= 60 else "🔴 Alto"
    st.write(f"**Risco de inadimplência (Manual):** {cor_risco} ({risco_total}%)")
    st.markdown("---")

    # Gráfico Risco x Retorno estilizado
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, retorno_esperado * 1.2)
    ax.scatter(risco_total, retorno_esperado, s=150, edgecolor="black", zorder=3)
    fig.suptitle("Análise de Risco x Retorno", fontsize=16, fontweight='bold', y=1.02)
    # Escapar o % para evitar MathText errors
    formula_text = f"{formatar_moeda(valor)} × {margem_estimada:.1f}\% = {formatar_moeda(retorno_esperado)} de retorno"
    fig.text(
        0.5, 0.95,
        formula_text,
        ha='center', fontsize=12
    )
    fig.tight_layout(rect=[0, 0, 1, 0.9])
    buf_risco = BytesIO()
    fig.savefig(buf_risco, format="png", dpi=300, bbox_inches="tight")
    buf_risco.seek(0)
    st.image(buf_risco)
    plt.close(fig)

    # Gráfico de Análise de Fatores de Risco
    st.subheader("Análise de Fatores de Risco")
    fatores = ["Score Serasa", "Idade da Empresa", "Protestos", "Faturamento"]
    pesos = [risco_score * 0.4, risco_idade * 0.2, risco_protesto * 0.25, risco_faturamento * 0.15]
    pesos = [p * 100 for p in pesos]
    fig_fat, ax_fat = plt.subplots(figsize=(6, 4))
    bars = ax_fat.bar(fatores, pesos, edgecolor="black", zorder=3)
    for bar in bars:
        height = bar.get_height()
        ax_fat.annotate(
            f"{height:.1f}%",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 5),
            textcoords="offset points",
            ha='center', va='bottom', fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.7)
        )
    ax_fat.set_ylabel("Peso na Composição do Risco (%)", fontsize=12)
    ax_fat.yaxis.set_major_formatter(PercentFormatter())
    ax_fat.grid(True, linestyle="--", alpha=0.6, zorder=0)
    buf_fat = BytesIO()
    fig_fat.savefig(buf_fat, format="png", dpi=300, bbox_inches="tight")
    buf_fat.seek(0)
    st.image(buf_fat)
    plt.close(fig_fat)

    # Geração e download do PDF
    dados_relatorio = {
        "Cliente": nome_cliente,
        "CNPJ": cnpj_cliente,
        "Valor da operação": formatar_moeda(valor),
        "Prazo (dias)": prazo,
        "Taxa Ideal (%)": taxa_ideal,
        "Margem (%)": margem_estimada,
        "Retorno Esperado (R$)": formatar_moeda(retorno_esperado),
        "Comparação com concorrência": ('Acima do mercado' if taxa_ideal > taxa_concorrencia + 0.05 else 'Abaixo do mercado' if taxa_ideal < taxa_concorrencia - 0.05 else 'Na média do mercado'),
        "Risco de inadimplência": f"{risco_total}% ({cor_risco})",
        "Preço mínimo sugerido pela IA": formatar_moeda(preco_sugerido),
        "Data do último faturamento": data_faturamento.strftime('%d/%m/%Y')
    }
    pdf_bytes = gerar_pdf(dados_relatorio, buf_risco, buf_fat)
    st.download_button("📄 Baixar relatório em PDF", data=pdf_bytes, file_name="relatorio_credito.pdf")

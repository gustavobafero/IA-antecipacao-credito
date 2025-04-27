import streamlit as st
from openai import OpenAI, RateLimitError
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter
from io import BytesIO
from fpdf import FPDF
import unicodedata
import tempfile
import locale

# Configuração de localização para formatação brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')  # fallback


def formatar_moeda(valor):
    """
    Formata valor numérico como moeda brasileira.
    """
    try:
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except:
        return f"R$ {valor:.2f}".replace(".", ",")


def calcular_preco_minimo(custo_base, risco_inadimplencia, margem_desejada_percentual):
    """
    Calcula o preço mínimo com base no custo, risco e margem desejada.
    """
    ajuste_risco = 1 + risco_inadimplencia
    margem = 1 + (margem_desejada_percentual / 100)
    return custo_base * ajuste_risco * margem

# Configuração da página Streamlit
st.set_page_config(page_title="IA Crédito + Risco de Inadimplência", layout="centered")
st.title("IA para Precificação de Antecipação de Crédito")
# Cliente OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def clean_text(text):
    """Normaliza texto para evitar problemas de codificação no PDF."""
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
        "Como a IA chegou no preço mínimo? Ela considera o valor do empréstimo, se protege do risco e adiciona uma margem de lucro, garantindo segurança e rentabilidade."
    ))
    # Gráfico Risco x Retorno
    pdf.add_page()
    if grafico_risco_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(grafico_risco_bytes.getvalue())
            path = tmp.name
        pdf.image(path, w=180)
        pdf.ln(5)
    pdf.multi_cell(0, 8, clean_text(
        "No gráfico:\n"
        "- Zona verde (0-30%): baixo risco, ótimo retorno.\n"
        "- Zona amarela (30-60%): risco intermediário, atenção.\n"
        "- Zona vermelha (60-100%): alto risco, cuidado.\n"
        "O ponto mostra sua simulação. Busque sempre estar na área verde!"
    ))
    # Gráfico de Fatores de Risco
    pdf.add_page()
    if grafico_fatores_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(grafico_fatores_bytes.getvalue())
            path = tmp.name
        pdf.image(path, w=180)
        pdf.ln(5)
    pdf.multi_cell(0, 8, clean_text(
        "Fatores de risco: mostra quais indicadores mais afetam a inadimplência."
    ))
    return BytesIO(pdf.output(dest='S').encode('latin1'))

# Formulário de entrada
st.header("1. Informações da Operação")
with st.form("formulario_operacao"):
    st.subheader("1. Dados da Operação")
    nome_cliente = st.text_input("Nome do cliente")
    cnpj_cliente = st.text_input("CNPJ do cliente (opcional)")
    valor = st.number_input("Valor da operação (R$)", 0.0, format="%.2f")
    data_operacao = st.date_input("Data da operação", datetime.today(), format="DD/MM/YYYY")
    data_vencimento = st.date_input("Data de vencimento", format="DD/MM/YYYY")
    rating = st.slider("Rating (0=risco alto,100=baixo)", 0, 100, 80)
    margem_desejada = st.number_input("Margem desejada (%)", 0.0, 1.0)
    custo_capital = st.number_input("Custo do capital (%)", 0.0, 1.5)
    taxa_concorrencia = st.number_input("Taxa da concorrência (%)", 0.0, 4.5)
    st.markdown("---")
    st.subheader("2. Avaliação de Risco de Inadimplência (Manual)")
    score_serasa = st.number_input("Score Serasa (0-1000)", 0, 1000, 750)
    idade_empresa = st.number_input("Idade da empresa (anos)", 0, 100, 5)
    protestos = st.selectbox("Possui protestos/dívidas públicas?", ["Não", "Sim"])
    faturamento = st.number_input("Último faturamento declarado (R$)", 0.0)
    data_faturamento = st.date_input("Data do último faturamento", format="DD/MM/YYYY")
    enviar = st.form_submit_button("Simular")

if enviar:
    prazo = (data_vencimento - data_operacao).days
    risco = (100 - rating) / 100
    taxa_ideal = round(custo_capital + margem_desejada + (risco * 2.0), 2)
    margem_est = round(taxa_ideal - custo_capital, 2)
    retorno = round(valor * (margem_est / 100), 2)
    preco_sugerido = calcular_preco_minimo(valor, risco, margem_desejada)
    risco_score = 0 if score_serasa >= 800 else 1 if score_serasa < 600 else 0.5
    risco_idade = 0 if idade_empresa >= 5 else 0.5
    risco_protesto = 1 if protestos == "Sim" else 0
    risco_fat = 0 if faturamento >= 500000 else 0.5
    risco_total = round((risco_score*0.4 + risco_idade*0.2 + risco_protesto*0.25 + risco_fat*0.15)*100, 2)

    st.markdown("## Resultado da Simulação")
    st.write(f"Prazo: {prazo} dias")
    st.write(f"Taxa ideal sugerida: {taxa_ideal}%")
    st.write(f"Retorno esperado: {formatar_moeda(retorno)}")
    st.write(f"Risco de inadimplência (Manual): {risco_total}%")
    st.markdown("---")

    # Gráfico Risco x Retorno
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.axvspan(0, 30, color='green', alpha=0.2)
    ax.axvspan(30, 60, color='yellow', alpha=0.2)
    ax.axvspan(60, 100, color='red', alpha=0.2)
    ax.scatter(risco_total, retorno, s=150, color='blue', edgecolor='navy', zorder=5)
    ax.annotate(f"{risco_total:.1f}% / {formatar_moeda(retorno)}", (risco_total, retorno), textcoords='offset points', xytext=(10,10), ha='left', color='blue')
    ax.set_xlim(0,100); ax.set_ylim(0, retorno*1.3)
    ax.set_xlabel('Risco de Inadimplência (%)'); ax.set_ylabel('Retorno Esperado (R$)')
    ax.set_title('Análise de Risco x Retorno')
    buf_risco = BytesIO(); fig.savefig(buf_risco, format='png', dpi=300, bbox_inches='tight'); buf_risco.seek(0)
    st.pyplot(fig); plt.close(fig)

    # Gráfico Fatores de Risco
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    fatores = ["Score Serasa", "Idade da Empresa", "Protestos", "Faturamento"]
    pesos = [risco_score*0.4, risco_idade*0.2, risco_protesto*0.25, risco_fat*0.15]
    pesos = [p*100 for p in pesos]
    bars = ax2.bar(fatores, pesos, edgecolor='black', zorder=3)
    for bar in bars:
        h = bar.get_height()
        ax2.annotate(f"{h:.1f}%", xy=(bar.get_x()+bar.get_width()/2, h), xytext=(0,5),
                     textcoords='offset points', ha='center', va='bottom')
    ax2.set_ylabel('Peso na Composição do Risco (%)')
    ax2.set_title('Análise de Fatores de Risco')
    buf_fat = BytesIO(); fig2.savefig(buf_fat, format='png', dpi=300, bbox_inches='tight'); buf_fat.seek(0)
    st.pyplot(fig2); plt.close(fig2)

    # Download PDF
    dados_relatorio = {
        'Cliente': nome_cliente,
        'CNPJ': cnpj_cliente,
        'Valor da operação': formatar_moeda(valor),
        'Prazo (dias)': prazo,
        'Taxa Ideal (%)': taxa_ideal,
        'Retorno Esperado (R$)': formatar_moeda(retorno),
        'Risco de inadimplência (%)': risco_total,
        'Preço IA': formatar_moeda(preco_sugerido)
    }
    pdf_bytes = gerar_pdf(dados_relatorio, buf_risco, buf_fat)
    st.download_button("📄 Baixar relatório em PDF", data=pdf_bytes, file_name="relatorio_credito.pdf")

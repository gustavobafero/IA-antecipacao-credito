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
import numpy as np

# Configuração de localização para formatação brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')


def formatar_moeda(valor):
    """Formata valor numérico como moeda brasileira."""
    try:
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except:
        return f"R$ {valor:.2f}".replace(".", ",")


def calcular_preco_minimo(custo_base, risco_inadimplencia, margem_desejada_percentual):
    """Calcula o preço mínimo com base no custo, risco e margem desejada."""
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


def gerar_pdf(data_dict, grafico_risco_bytes=None, grafico_fatores_bytes=None,
             grafico_frente_bytes=None, grafico_water_bytes=None):
    """Gera um PDF com relatório de precificação e riscos, incluindo gráficos."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório de Precificação e Risco de Crédito", ln=True, align='C')
    pdf.ln(10)
    for chave, valor in data_dict.items():
        pdf.cell(0, 8, txt=clean_text(f"{chave}: {valor}"), ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", style='I', size=11)
    texto_inf = (
        "Como a IA chegou no preço mínimo?\n"
        "- Ela considera o valor do empréstimo e protege-se do risco.\n"
        "- Adiciona uma margem de lucro para garantir rentabilidade.\n"
        "O resultado é um preço justo, seguro e vantajoso para todos."
    )
    pdf.multi_cell(0, 8, clean_text(texto_inf))

    def adicionar_imagem(bytes_img, legenda):
        if bytes_img:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(bytes_img.getvalue())
                path = tmp.name
            pdf.add_page()
            pdf.image(path, w=180)
            pdf.ln(5)
            pdf.multi_cell(0, 8, clean_text(legenda))

    # 1) Risco x Retorno
        # 1) Risco x Retorno
    legenda1 = (
        "No gráfico:
"
        "- Zona verde (0-30%): baixo risco, ótimo retorno.
"
        "- Zona amarela (30-60%): risco intermediário, atenção.
"
        "- Zona vermelha (60-100%): alto risco, cuidado.
"
        "O ponto mostra a sua simulação. Busque sempre estar na área verde!"
    ): baixo risco, ótimo retorno.\n"
        "- Zona amarela (30-60%): risco intermediário, atenção.\n"
        "- Zona vermelha (60-100%): alto risco, cuidado.\n"
        "O ponto mostra a sua simulação. Busque sempre estar na área verde!"
    )
    adicionar_imagem(grafico_risco_bytes, legenda1)

    # 2) Fatores de Risco
    legenda2 = "Fatores de risco: mostra quais indicadores mais afetam a inadimplência."
    adicionar_imagem(grafico_fatores_bytes, legenda2)

    # 3) Fronteira Eficiente
    legenda3 = "Fronteira eficiente: para cada nível de risco, mostra o retorno máximo esperado."
    adicionar_imagem(grafico_frente_bytes, legenda3)

    # 4) Waterfall de Contribuições
    legenda4 = "Waterfall: ilustra como cada fator contribuiu incrementalmente para o risco total."
    adicionar_imagem(grafico_water_bytes, legenda4)

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
    score_serasa = st.number_input("Score Serasa (0 a 1000)", min_value=0, max_value=1000, value=750)
    idade_empresa = st.number_input("Idade da empresa (anos)", min_value=0, value=5)
    protestos = st.selectbox("Possui protestos ou dívidas públicas?", ["Não", "Sim"])
    faturamento = st.number_input("Último faturamento declarado (R$)", min_value=0.0, format="%.2f")
    data_faturamento = st.date_input("Data do último faturamento", format="DD/MM/YYYY")
    enviar = st.form_submit_button("Simular")

if enviar:
    # Cálculos
    prazo = (data_vencimento - data_operacao).days
    risco = (100 - rating) / 100
    taxa_ideal = round(custo_capital + margem_desejada + (risco * 2.0), 2)
    margem_est = round(taxa_ideal - custo_capital, 2)
    retorno = round(valor * (margem_est / 100), 2)
    preco_sugerido = calcular_preco_minimo(valor, risco, margem_desejada)
    # Contribuições manuais
    r_score = 0 if score_serasa >= 800 else 1 if score_serasa < 600 else 0.5
    r_idade = 0 if idade_empresa >= 5 else 0.5
    r_protesto = 1 if protestos == "Sim" else 0
    r_fatur = 0 if faturamento >= 500000 else 0.5
    contrib = [r_score * 40, r_idade * 20, r_protesto * 25, r_fatur * 15]
    fatores = ["Serasa", "Idade", "Protestos", "Faturamento"]
    risco_total = round(sum(contrib), 2)

    st.markdown("## Resultado da Simulação")
    st.write(f"Prazo: {prazo} dias | Taxa: {taxa_ideal}% | Retorno: {formatar_moeda(retorno)}")
    st.markdown(f"**Preço IA: {formatar_moeda(preco_sugerido)}**")
    st.write(f"Risco Manual: {risco_total}%")
    st.markdown("---")

    # 1) Risco x Retorno
    fig_r = plt.figure(figsize=(6, 4))
    axr = fig_r.add_subplot(111)
    axr.axvspan(0, 30, color='green', alpha=0.2)
    axr.axvspan(30, 60, color='yellow', alpha=0.2)
    axr.axvspan(60, 100, color='red', alpha=0.2)
    axr.scatter(risco_total, retorno, s=150, color='blue', edgecolor='navy', zorder=5)
    axr.annotate(f"{risco_total:.1f}% / {formatar_moeda(retorno)}", (risco_total, retorno),
                 textcoords='offset points', xytext=(10, 10), ha='left', color='blue')
    axr.set_xlim(0, 100); axr.set_ylim(0, retorno * 1.3)
    axr.set_xlabel('Risco (%)'); axr.set_ylabel('Retorno (R$)')
    axr.set_title('1. Risco x Retorno')
    axr.xaxis.set_major_formatter(PercentFormatter())
    buf_risco = BytesIO(); fig_r.savefig(buf_risco, format='png', dpi=300, bbox_inches='tight'); buf_risco.seek(0)
    st.pyplot(fig_r); plt.close(fig_r)

    # 2) Fatores de Risco
    fig_f = plt.figure(figsize=(6, 4))
    axf = fig_f.add_subplot(111)
    axf.bar(fatores, contrib, color='skyblue', edgecolor='black')
    for i, h in enumerate(contrib): axf.text(i, h + 1, f"{h:.1f}%", ha='center')
    axf.set_ylabel('Contribuição (%)'); axf.set_title('2. Fatores de Risco')
    buf_fat = BytesIO(); fig_f.savefig(buf_fat, format='png', dpi=300, bbox_inches='tight'); buf_fat.seek(0)
    st.pyplot(fig_f); plt.close(fig_f)

    # 3) Fronteira Eficiente
    fig_fr = plt.figure(figsize=(6, 4))
    axfr = fig_fr.add_subplot(111)
    x = np.linspace(0, 100, 100)
    y = valor * (margem_est / 100) * (1 + x / 100)
    axfr.plot(x, y, label='Fronteira Eficiente')
    axfr.scatter(risco_total, retorno, color='blue', edgecolor='navy', zorder=5)
    axfr.set_xlabel('Risco (%)'); axfr.set_ylabel('Retorno (R$)')
    axfr.set_title('3. Fronteira Eficiente')
    axfr.legend()
    buf_frente = BytesIO(); fig_fr.savefig(buf_frente, format='png', dpi=300, bbox_inches='tight'); buf_frente.seek(0)
    st.pyplot(fig_fr); plt.close(fig_fr)

    # 4) Waterfall
    fig_w = plt.figure(figsize=(6, 4))
    axw = fig_w.add_subplot(111)
    cum = [0] + list(np.cumsum(contrib))
    for i, v in enumerate(contrib):
        axw.bar(fatores[i], v, bottom=cum[i], color='orange', edgecolor='black')
    axw.set_ylabel('Risco (%)'); axw.set_title('4. Waterfall de Contribuições')
    buf_water = BytesIO(); fig_w.savefig(buf_water, format='png', dpi=300, bbox_inches='tight'); buf_water.seek(0)
    st.pyplot(fig_w); plt.close(fig_w)

    # Gerar PDF com todos os gráficos
    dados = {
        'Cliente': nome_cliente,
        'CNPJ': cnpj_cliente,
        'Valor': formatar_moeda(valor),
        'Prazo': f"{prazo} dias",
        'Taxa Ideal (%)': f"{taxa_ideal}%",
        'Retorno Esperado': formatar_moeda(retorno),
        'Preço IA': formatar_moeda(preco_sugerido),
        'Risco Total (%)': f"{risco_total}%"
    }
    pdf_bytes = gerar_pdf(dados, buf_risco, buf_fat, buf_frente, buf_water)
    st.download_button('📄 Baixar PDF', data=pdf_bytes, file_name='relatorio_credito.pdf')

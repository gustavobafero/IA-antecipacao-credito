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
    """
    Normaliza texto para evitar problemas de codificação no PDF.
    """
    return unicodedata.normalize('NFKD', text).encode('latin1', 'ignore').decode('latin1')


def gerar_pdf(data_dict, grafico_risco_bytes=None, grafico_fatores_bytes=None,
             grafico_frente_bytes=None, grafico_water_bytes=None):
    """
    Gera um PDF com relatório de precificação e riscos, incluindo gráficos.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Relatório de Precificação e Risco de Crédito", ln=True, align='C')
    pdf.ln(10)

    # Insere dados
    for chave, valor in data_dict.items():
        pdf.cell(0, 8, txt=clean_text(f"{chave}: {valor}"), ln=True)
    pdf.ln(5)

    # Explicação infantil
    pdf.set_font("Arial", style='I', size=11)
    texto_inf = (
        "Como a IA chegou no preço mínimo?\n"
        "- Ela considera o valor do empréstimo e protege-se do risco.\n"
        "- Adiciona uma margem de lucro para garantir rentabilidade.\n"
        "O resultado é um preço justo, seguro e vantajoso para todos."
    )
    pdf.multi_cell(0, 8, clean_text(texto_inf))

    # Gráfico Risco x Retorno
    pdf.add_page()
    if grafico_risco_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(grafico_risco_bytes.getvalue()); path = tmp.name
        pdf.image(path, w=180); pdf.ln(5)
    texto_graf1 = (
        "No gráfico:\n"
        "- Zona verde (0-30%): baixo risco, ótimo retorno.\n"
        "- Zona amarela (30-60%): risco intermediário, atenção.\n"
        "- Zona vermelha (60-100%): alto risco, cuidado.\n"
        "O ponto mostra a sua simulação. Busque sempre estar na área verde!"
    )
    pdf.multi_cell(0, 8, clean_text(texto_graf1))

    # Graph 1: Fronteira de Risco x Retorno
    pdf.add_page()
    if grafico_frente_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(grafico_frente_bytes.getvalue()); path = tmp.name
        pdf.image(path, w=180); pdf.ln(5)
    pdf.multi_cell(0, 8, clean_text(
        "Fronteira eficiente: para cada nível de risco, mostra o retorno máximo esperado."
    ))

    # Graph 4: Waterfall de Fatores de Risco
    pdf.add_page()
    if grafico_water_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(grafico_water_bytes.getvalue()); path = tmp.name
        pdf.image(path, w=180); pdf.ln(5)
    pdf.multi_cell(0, 8, clean_text(
        "Waterfall: ilustra como cada fator contribuiu incrementalmente para o risco total."
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
    rating = st.slider("Rating (0 risco alto,100 baixo)", 0,100,80)
    margem_desejada = st.number_input("Margem desejada (%)", 0.0,1.0)
    custo_capital = st.number_input("Custo de capital (%)", 0.0,1.5)
    taxa_concorrencia = st.number_input("Taxa concorrência (%)",0.0,4.5)
    st.markdown("---")
    st.subheader("2. Avaliação de Risco (Manual)")
    score_serasa = st.number_input("Score Serasa (0-1000)",0,1000,750)
    idade_empresa = st.number_input("Idade empresa (anos)",0,100,5)
    protestos = st.selectbox("Protestos?",["Não","Sim"])
    faturamento = st.number_input("Faturamento (R$)",0.0)
    data_faturamento = st.date_input("Data faturamento",format="DD/MM/YYYY")
    enviar = st.form_submit_button("Simular")

if enviar:
    # Cálculos
    prazo=(data_vencimento-data_operacao).days
    risco=(100-rating)/100
    taxa_ideal=round(custo_capital+margem_desejada+(risco*2),2)
    margem_est=round(taxa_ideal-custo_capital,2)
    retorno=round(valor*(margem_est/100),2)
    preco_sugerido=calcular_preco_minimo(valor,risco,margem_desejada)
    # Manual
    r_score=0 if score_serasa>=800 else 1 if score_serasa<600 else 0.5
    r_idade=0 if idade_empresa>=5 else 0.5
    r_protesto=1 if protestos=="Sim" else 0
    r_fatur=0 if faturamento>=500000 else 0.5
    contribuicoes=[r_score*40, r_idade*20, r_protesto*25, r_fatur*15]
    fatores=["Serasa","Idade","Protestos","Faturamento"]
    risco_total=round(sum(contribuicoes),2)

    # Exibição resultados
    st.markdown("## Resultado")
    st.write(f"Prazo: {prazo} dias | Taxa: {taxa_ideal}% | Retorno: {formatar_moeda(retorno)}")
    st.markdown(f"**Preço IA: {formatar_moeda(preco_sugerido)}**")
    st.write(f"Risco Manual: {risco_total}%")
    st.markdown("---")

    # 1) Gráfico Risco x Retorno
    fig,ax=plt.subplots(6,1,figsize=(6,8))
    ax0=ax[0]
    ax0.axvspan(0,30,color='green',alpha=0.2)
    ax0.axvspan(30,60,color='yellow',alpha=0.2)
    ax0.axvspan(60,100,color='red',alpha=0.2)
    ax0.scatter(risco_total,retorno,s=150,color='blue',edgecolor='navy')
    ax0.annotate(f"{risco_total:.1f}% / {formatar_moeda(retorno)}",(risco_total,retorno),xytext=(10,10),textcoords='offset points',color='blue')
    ax0.set_xlim(0,100);ax0.set_ylim(0,retorno*1.3)
    ax0.set_xlabel('Risco (%)');ax0.set_ylabel('Retorno (R$)')
    ax0.set_title('1. Risco x Retorno')

    # 2) Gráfico Fatores
    ax1=ax[1]
    ax1.bar(fatores,contribuicoes,color='skyblue',edgecolor='black')
    for i,h in enumerate(contribuicoes): ax1.text(i,h+1,f"{h:.1f}%",ha='center')
    ax1.set_ylabel('Contribuição (%)'); ax1.set_title('2. Fatores de Risco')

    # 3) Fronteira Eficiente (Gráfico 1 sugerido)
    ax2=ax[2]
    x=np.linspace(0,100,100)
    y=valor*(margem_est/100)*(1+x/100)
    ax2.plot(x,y,label='Fronteira')
    ax2.scatter(risco_total,retorno,color='blue',edgecolor='navy')
    ax2.set_xlabel('Risco (%)');ax2.set_ylabel('Retorno (R$)')
    ax2.set_title('3. Fronteira Eficiente')
    ax2.legend()

    # 4) Waterfall Chart (Fatores)
    ax3=ax[3]
    cum=[0]+list(np.cumsum(contribuicoes))
    for i,val in enumerate(contribuicoes):
        ax3.bar(fatores[i],val,bottom=cum[i],color='orange',edgecolor='black')
    ax3.set_ylabel('Risco (%)'); ax3.set_title('4. Waterfall de Contribuições')

    # Ajustes de layout e exibição
    plt.tight_layout()
    buf_risk=BytesIO(); fig.savefig(buf_risk,format='png',dpi=300,bbox_inches='tight'); buf_risk.seek(0)
    st.pyplot(fig)
    plt.close(fig)

    # Botão PDF
    dados={
        'Cliente':nome_cliente,'CNPJ':cnpj_cliente,'Valor':formatar_moeda(valor),
        'Prazo':prazo,'Taxa':f"{taxa_ideal}%",'Retorno':formatar_moeda(retorno),'Preço IA':formatar_moeda(preco_sugerido),'Risco Total':f"{risco_total}%"
    }
    pdf_bytes=gerar_pdf(dados,buf_risk,buf_risk,buf_risk,buf_risk)
    st.download_button('📄 Baixar PDF',data=pdf_bytes,file_name='relatorio.pdf')

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
import numpy as np
import pandas as pd

# Configuração de localização para formatação brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')

# Funções utilitárias
def formatar_moeda(valor):
    try:
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    except:
        return f"R$ {valor:.2f}".replace(".", ",")

def calcular_preco_minimo(custo_base, risco, margem_pct):
    ajuste = 1 + risco
    margem = 1 + margem_pct/100
    return custo_base * ajuste * margem

def clean_text(text):
    return unicodedata.normalize('NFKD', text).encode('latin1','ignore').decode('latin1')

# Geração de PDF
def gerar_pdf(data, img_risco, img_fatores, img_dist):
    pdf = FPDF()
    pdf.add_page(); pdf.set_font('Arial', size=12)
    pdf.cell(200,10, txt='Relatório de Precificação e Risco de Crédito', ln=True, align='C')
    pdf.ln(10)
    # Dados principais
    for k,v in data.items():
        if k != 'Correlação':
            pdf.cell(0,8, clean_text(f"{k}: {v}"), ln=True)
    pdf.ln(5)
    pdf.set_font('Arial','I',11)
    texto = (
        "Como a IA chegou no preço mínimo?\n"
        "- Considera valor do empréstimo e protege do risco.\n"
        "- Adiciona margem de lucro para rentabilidade."
    )
    pdf.multi_cell(0,8, clean_text(texto))

    def add_chart(img, legend):
        if img:
            with tempfile.NamedTemporaryFile(delete=False,suffix='.png') as tmp:
                tmp.write(img.getvalue()); path=tmp.name
            pdf.add_page(); pdf.image(path, w=180); pdf.ln(5)
            pdf.multi_cell(0,8, clean_text(legend))

    add_chart(img_risco, "Zona verde 0–30% baixo risco; amarelo 30–60% intermediário; vermelho 60–100% alto risco.")
    add_chart(img_fatores, "Fatores de risco: indicadores que mais afetam inadimplência.")
    add_chart(img_dist, "Histograma de risco comparando simulações ao risco atual.")

    # Cenários
    pdf.add_page()
    pdf.multi_cell(0,8, clean_text(
        f"Melhor caso (0% risco): {data['Melhor Caso']}\n"
        f"Pior caso   (100% risco): {data['Pior Caso']}"
    ))
    # Correlações
    pdf.add_page(); pdf.multi_cell(0,8, clean_text("Correlação entre variáveis:"))
    for idx,row in data['Correlação'].iterrows():
        line = ", ".join([f"{c}: {row[c]:.2f}" for c in data['Correlação'].columns])
        pdf.cell(0,6, clean_text(f"{idx}: {line}"), ln=True)
    pdf.ln(3)
    # Alerta, resumo e apetite
    pdf.multi_cell(0,8, clean_text(data['Alerta Outlier']))
    pdf.ln(2); pdf.multi_cell(0,8, clean_text(data['Resumo Executivo']))
    pdf.ln(2); pdf.multi_cell(0,8, clean_text(data['Adequação Risco']))
    return BytesIO(pdf.output(dest='S').encode('latin1'))

# Configuração da página Streamlit
st.set_page_config(page_title='IA Crédito + Risco de Inadimplência', layout='centered')
st.title('IA para Precificação de Antecipação de Crédito')
client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])

# Formulário de entrada
st.header('1. Informações da Operação')
with st.form('form'):
    st.subheader('1. Dados da Operação')
    nome = st.text_input('Nome do cliente')
    cnpj = st.text_input('CNPJ (opcional)')
    valor = st.number_input('Valor da operação (R$)', min_value=0.0, format='%.2f')
    dt_op = st.date_input('Data da operação', datetime.today())
    dt_vc = st.date_input('Data de vencimento')
    rating = st.slider('Rating (0 alto risco,100 baixo risco)',0,100,80)
    margem = st.number_input('Margem desejada (%)',0.0,100.0,1.0)
    custo = st.number_input('Custo do capital (%)',0.0,100.0,1.5)
    tx_conc = st.number_input('Taxa concorrência (%)',0.0,100.0,4.5)
    st.markdown('---')
    st.subheader('2. Avaliação de Risco (Manual)')
    score = st.number_input('Score Serasa (0-1000)',0,1000,750)
    idade = st.number_input('Idade da empresa (anos)',0,100,5)
    protesto = st.selectbox('Possui protestos?', ['Não','Sim'])
    fatur = st.number_input('Faturamento (R$)',min_value=0.0)
    submitted = st.form_submit_button('Simular')

if submitted:
    # Cálculos
    prazo=(dt_vc-dt_op).days
    risco=(100-rating)/100
    adj = max(0.5-(valor/100000),0)
    taxa = round(custo+margem+(risco*2.0)+adj,2)
    marg_est = round(taxa-custo,2)
    ret = round(valor*(marg_est/100),2)
    preco = calcular_preco_minimo(valor,risco,margem)

    # Exibição original preferida
    st.markdown('## Resultado da Simulação')
    st.write(f'**Prazo da operação:** {prazo} dias')
    st.write(f'**Taxa ideal sugerida:** {taxa}%')
    st.write(f'**Retorno esperado:** {formatar_moeda(ret)}')
    st.markdown(f'### 💰 Preço sugerido pela IA: **{formatar_moeda(preco)}**')

    # Risco manual
    rs = 0 if score>=800 else 1 if score<600 else 0.5
    ri = 0 if idade>=5 else 0.5
    rp = 1 if protesto=='Sim' else 0
    rf = 0 if fatur>=500000 else 0.5
    rt = round((rs*0.4+ri*0.2+rp*0.25+rf*0.15)*100,2)
    cor = '🟢 Baixo' if rt<=30 else '🟡 Moderado' if rt<=60 else '🔴 Alto'
    st.write(f'**Risco de inadimplência (Manual):** {cor} ({rt}%)')
    st.markdown('---')

    # Gráficos originais
    fig,ax=plt.subplots(figsize=(6,4))
    ax.axvspan(0,30,color='green',alpha=0.2)
    ax.axvspan(30,60,color='yellow',alpha=0.2)
    ax.axvspan(60,100,color='red',alpha=0.2)
    ax.scatter(rt,ret,s=150,color='blue',edgecolor='navy')
    ax.annotate(f"{rt:.1f}% / {formatar_moeda(ret)}",(rt,ret),xytext=(10,10),textcoords='offset points',color='blue')
    ax.set_xlabel('Risco (%)'); ax.set_ylabel('Retorno (R$)'); ax.xaxis.set_major_formatter(PercentFormatter())
    ax.set_title('Análise de Risco x Retorno')
    buf_r = BytesIO(); fig.savefig(buf_r,format='png',dpi=300,bbox_inches='tight'); buf_r.seek(0)
    st.pyplot(fig); plt.close(fig)

    fig2,ax2=plt.subplots(figsize=(6,4))
    fatores=['Score Serasa','Idade','Protestos','Faturamento']
    pesos=[rs*0.4,ri*0.2,rp*0.25,rf*0.15]; pesos=[p*100 for p in pesos]
    bars=ax2.bar(fatores,pesos,edgecolor='black')
    for b in bars: ax2.annotate(f"{b.get_height():.1f}%",(b.get_x()+b.get_width()/2,b.get_height()),ha='center',va='bottom')
    ax2.set_ylabel('Peso (%)'); ax2.set_title('Análise de Fatores de Risco')
    buf_f = BytesIO(); fig2.savefig(buf_f,format='png',dpi=300,bbox_inches='tight'); buf_f.seek(0)
    st.pyplot(fig2); plt.close(fig2)

    # 1) Distribuição de Risco
    sim = np.clip(np.random.normal(rating,10,500),0,100)
    sim_risk=100-sim
    fig3,ax3=plt.subplots(figsize=(6,3))
    ax3.hist(sim_risk,bins=20,edgecolor='black'); ax3.axvline(rt,color='red',linestyle='--',label='Seu risco')
    ax3.set_xlabel('Risco (%)'); ax3.set_ylabel('Frequência'); ax3.legend(); ax3.set_title('Histograma de Risco')
    buf_d=BytesIO(); fig3.savefig(buf_d,format='png',dpi=300,bbox_inches='tight'); buf_d.seek(0)
    st.pyplot(fig3); plt.close(fig3)

    # 4) Cenários
    st.subheader('Cenários: Melhor vs. Pior Caso')
    melhor=calcular_preco_minimo(valor,0,margem); pior=calcular_preco_minimo(valor,1,margem)
    st.write(f"Melhor caso (0% risco): {formatar_moeda(melhor)}")
    st.write(f"Pior caso   (100% risco): {formatar_moeda(pior)}")

    # 6) Heatmap de Correlações
    st.subheader('Heatmap de Correlações')
    df=pd.DataFrame({'rating':[rating],'score':[score],'idade':[idade],'fatur':[fatur],'risco':[rt],'retorno':[ret]})
    corr=df.corr(); st.write(corr)

    # 8) Alerta de Outlier
    media,desv=sim_risk.mean(),sim_risk.std()
    st.subheader('Alerta de Outlier')
    if rt>media+2*desv: st.warning('⚠️ Seu risco está muito acima da média.')
    else: st.success('✅ Risco dentro da faixa esperada.')

    # 9) Resumo Executivo
    st.subheader('Resumo Executivo')
    resumo=f"Cliente {nome} apresenta risco de {rt:.1f}% e retorno de {formatar_moeda(ret)}. Taxa ideal: {taxa}%"
    st.info(resumo)

    # 10) Adequação ao Apetite
    st.subheader('Adequação ao Apetite de Risco')
    limite=50
    if rt<=limite: st.success(f'👍 Operação dentro do apetite (≤ {limite}%)')
    else: st.error(f'⚠️ Operação fora do apetite (> {limite}%)')

    # Download PDF
    dados={
        'Cliente':nome,'CNPJ':cnpj,'Valor':formatar_moeda(valor),'Prazo':f"{prazo} dias",
        'Taxa Ideal':f"{taxa}%",'Retorno':formatar_moeda(ret),'Preço IA':formatar_moeda(preco),
        'Melhor Caso':formatar_moeda(melhor),'Pior Caso':formatar_moeda(pior),
        'Correlação':corr,'Alerta Outlier':('⚠️ acima' if rt>media+2*desv else '✅ dentro'),
        'Resumo Executivo':resumo,'Adequação Risco':('👍 dentro' if rt<=limite else '⚠️ fora')
    }
    pdf_bytes=gerar_pdf(dados,buf_r,buf_f,buf_d)
    st.download_button('📄 Baixar relatório em PDF',pdf_bytes,'relatorio_credito.pdf')

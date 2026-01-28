import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
from senior_aut import (
    iniciar_selenium, login, acessar_marcacoes, navegar_para_mes,
    extrair_registros, gerar_planilha, extrair_nome_usuario
)
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch


def gerar_pdf(df, nome_usuario, periodo_inicio, periodo_fim):
    """Gera PDF com os dados do banco de horas"""
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=40, bottomMargin=20)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2563EB'),
        spaceAfter=12,
        alignment=1
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    elements.append(Paragraph(f"📊 Relatório de Banco de Horas", title_style))
    elements.append(Paragraph(f"<b>Usuário:</b> {nome_usuario}", normal_style))
    elements.append(Paragraph(f"<b>Período:</b> {periodo_inicio} a {periodo_fim}", normal_style))
    elements.append(Paragraph(f"<b>Gerado em:</b> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}", normal_style))
    elements.append(Spacer(1, 12))
    
    data = [["Data", "Entrada", "Saída Almoço", "Volta Almoço", "Saída", "Trabalhadas", "Abonas", "Carga", "Banco do Dia", "Saldo Acum."]]
    
    for _, row in df.iterrows():
        marcacoes_str = row["Marcações"] if pd.notna(row["Marcações"]) else ""
        marcacoes = marcacoes_str.split(" | ") if marcacoes_str else []
        
        while len(marcacoes) < 4:
            marcacoes.append("")
        
        data.append([
            row["Data"],
            marcacoes[0] if len(marcacoes) > 0 else "",
            marcacoes[1] if len(marcacoes) > 1 else "",
            marcacoes[2] if len(marcacoes) > 2 else "",
            marcacoes[3] if len(marcacoes) > 3 else "",
            row["Horas Trabalhadas"],
            row["Abonas"],
            row["Carga Horária"],
            row["Banco do Dia"],
            row["Saldo Acumulado"]
        ])
    
    table = Table(data, colWidths=[0.8*inch, 0.9*inch, 1.1*inch, 1.1*inch, 0.9*inch, 0.85*inch, 0.75*inch, 0.75*inch, 0.9*inch, 0.9*inch])
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
    ]))
    
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# Configuração da página
st.set_page_config(
    page_title="Senior Ponto - Banco de Horas",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
    <style>
        * { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif; }
        
        .main { background: linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%); }
        [data-testid="stMainBlockContainer"] { background: linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%); }
        
        [data-testid="stSidebar"] { background: linear-gradient(180deg, #2563EB 0%, #1E40AF 100%); }
        [data-testid="stSidebar"] * { color: #FFFFFF !important; }
        
        .stTabs [data-baseweb="tab-list"] button { 
            font-size: 15px; font-weight: 600; color: #374151; border-bottom: 3px solid transparent; transition: all 0.3s; 
        }
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] { 
            border-bottom: 3px solid #2563EB; color: #2563EB; 
        }
        
        .stButton > button { 
            background: linear-gradient(135deg, #2563EB 0%, #1E40AF 100%) !important; 
            color: white !important; border: none !important; border-radius: 8px !important; 
            font-weight: 600 !important; font-size: 15px !important; padding: 12px 24px !important; 
            transition: all 0.3s !important; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3) !important; 
        }
        .stButton > button:hover { 
            transform: translateY(-2px) !important; box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4) !important; 
        }
        
        .stTextInput > div > div > input, .stSelectbox > div > div > select, .stNumberInput > div > div > input { 
            border: 2px solid #E5E7EB !important; border-radius: 8px !important; font-size: 14px !important; 
            padding: 10px 12px !important; transition: all 0.3s !important; 
        }
        .stTextInput > div > div > input:focus, .stSelectbox > div > div > select:focus, .stNumberInput > div > div > input:focus { 
            border-color: #2563EB !important; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important; 
        }
        
        .stMetric { 
            background: white !important; padding: 20px !important; border-radius: 12px !important; 
            border-left: 4px solid #2563EB !important; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05) !important; 
            transition: all 0.3s !important; 
        }
        .stMetric:hover { 
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1) !important; transform: translateY(-2px) !important; 
        }
        
        .stInfo { 
            background-color: #EFF6FF !important; border-left: 4px solid #2563EB !important; 
            border-radius: 8px !important; padding: 15px !important; 
        }
        .stSuccess { 
            background-color: #ECFDF5 !important; border-left: 4px solid #10B981 !important; border-radius: 8px !important; 
        }
        .stError { 
            background-color: #FEF2F2 !important; border-left: 4px solid #EF4444 !important; border-radius: 8px !important; 
        }
        
        h1 { color: #111827 !important; font-size: 2.5em !important; font-weight: 700 !important; margin-bottom: 12px !important; }
        h2 { 
            color: #111827 !important; font-size: 1.8em !important; font-weight: 700 !important; 
            margin-top: 24px !important; margin-bottom: 16px !important; border-bottom: 2px solid #2563EB !important; padding-bottom: 8px !important; 
        }
        h3 { color: #374151 !important; font-weight: 700 !important; }
        
        .stDataFrame { border-radius: 12px !important; overflow: hidden !important; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05) !important; }
        .stProgress > div > div { background: linear-gradient(90deg, #2563EB 0%, #1E40AF 100%) !important; border-radius: 10px !important; }
        
        .stCheckbox label { color: #374151 !important; font-weight: 600 !important; font-size: 14px !important; }
        
        a { color: #2563EB !important; text-decoration: none; font-weight: 600; }
        a:hover { color: #1E40AF !important; text-decoration: underline; }
        
        hr { border: none; height: 2px; background: linear-gradient(90deg, #E5E7EB 0%, #D1D5DB 50%, #E5E7EB 100%); margin: 24px 0; }
        
        .stDownloadButton > button { 
            background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important; 
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3) !important; 
        }
        .stDownloadButton > button:hover { 
            transform: translateY(-2px) !important; box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4) !important; 
        }
        
        .stCaption { color: #6B7280 !important; font-size: 13px !important; }
    </style>
""", unsafe_allow_html=True)

# ============ SIDEBAR ============
st.sidebar.markdown("""
    <div style='text-align: center; padding: 30px 0 20px 0;'>
        <h1 style='margin: 0; font-size: 32px;'>⏱️</h1>
        <h2 style='margin: 12px 0 0 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px;'>Senior Ponto</h2>
        <p style='margin: 4px 0 0 0; font-size: 12px; opacity: 0.9;'>Banco de Horas</p>
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

pagina = st.sidebar.radio(
    "Menu",
    ["🏠 Inicial", "📊 Dashboard", "📋 Dados", "⚙️ Configurações"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")

# Footer com autor
st.sidebar.markdown("""
    <div style='position: fixed; bottom: 20px; left: 10px; right: 10px; 
                 text-align: center; background: rgba(255, 255, 255, 0.08); 
                 padding: 15px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.15);
                 font-size: 11px;'>
        <p style='margin: 0 0 10px 0; font-weight: 600; font-size: 12px;'>Versão 2.1</p>
        <p style='margin: 0 0 8px 0; opacity: 0.85;'>Sistema de Extração Automática</p>
        <div style='border-top: 1px solid rgba(255, 255, 255, 0.2); margin: 8px 0; padding-top: 8px;'>
            <p style='margin: 0 0 3px 0; opacity: 0.7; font-size: 10px;'>CRIADO POR</p>
            <p style='margin: 0; font-weight: 700; font-size: 12px;'>João Pedro da Silveira</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# ============ PÁGINA INICIAL ============
if pagina == "🏠 Inicial":
    st.markdown("# 📥 Extração de Dados")
    st.markdown("Preencha seus dados para extrair o banco de horas")
    
    st.markdown("---")
    
    st.markdown("## 🔐 Credenciais de Acesso")
    
    col1, col2 = st.columns(2)
    with col1:
        usuario = st.text_input("👤 Usuário", placeholder="Seu login do Senior")
    with col2:
        senha = st.text_input("🔑 Senha", placeholder="Sua senha", type="password")
    
    st.markdown("---")
    
    st.markdown("## 📅 Período de Extração")
    st.info("**Nota:** O sistema irá extrair do mês/ano atual até a data que você especificar")
    
    agora = datetime.now()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📆 Mês Atual", f"{agora.month:02d}/{agora.year}")
    
    with col2:
        mes_fim = st.selectbox("Extrair até o mês:", range(1, 13), index=agora.month-2 if agora.month > 2 else 0)
    
    with col3:
        ano_fim = st.selectbox("Extrair até o ano:", range(2020, 2027), index=agora.year-2020)
    
    st.markdown("---")
    
    st.markdown("## ⚙️ Opções Avançadas")
    
    col1, col2 = st.columns(2)
    with col1:
        mostrar_chrome = st.checkbox("☑ Mostrar navegador (mais lento, útil para debug)")
    with col2:
        st.caption("Desative para processamento mais rápido")
    
    st.markdown("---")
    
    if st.button("🚀 PROCESSAR", use_container_width=True):
        if not usuario or not senha:
            st.error("❌ Usuário e senha são obrigatórios!")
        else:
            with st.spinner("⏳ Processando... Por favor, aguarde"):
                try:
                    progresso = st.progress(0)
                    status = st.status("Iniciando processamento...", expanded=True)
                    
                    status.write("👉 Iniciando navegador...")
                    ver_chrome = "s" if mostrar_chrome else "n"
                    driver = iniciar_selenium(ver_chrome)
                    progresso.progress(10)
                    
                    status.write("👉 Fazendo login...")
                    login(driver, usuario, senha)
                    progresso.progress(20)
                    
                    status.write("👉 Acessando marcações...")
                    acessar_marcacoes(driver)
                    progresso.progress(30)
                    
                    status.write("👉 Extraindo nome do usuário...")
                    nome_usuario = extrair_nome_usuario(driver)
                    progresso.progress(35)
                    
                    registros = []
                    mes = agora.month
                    ano = agora.year
                    
                    mes_temp, ano_temp = mes, ano
                    total_meses = 0
                    while ano_temp > ano_fim or (ano_temp == ano_fim and mes_temp >= mes_fim):
                        total_meses += 1
                        mes_temp -= 1
                        if mes_temp < 1:
                            mes_temp = 12
                            ano_temp -= 1
                    
                    mes_processado = 0
                    while ano > ano_fim or (ano == ano_fim and mes >= mes_fim):
                        mes_processado += 1
                        status.write(f"[{mes_processado}/{total_meses}] 📅 Processando {mes:02d}/{ano}...")
                        
                        navegar_para_mes(driver, mes, ano)
                        registros_mes = extrair_registros(driver)
                        registros.extend(registros_mes)
                        
                        progresso.progress(35 + int((mes_processado / total_meses) * 50))
                        
                        mes -= 1
                        if mes < 1:
                            mes = 12
                            ano -= 1
                    
                    driver.quit()
                    status.write("👉 Organizando dados...")
                    registros = sorted(registros, key=lambda x: x["Data ISO"])
                    progresso.progress(85)
                    
                    status.write("👉 Gerando planilha e dashboard...")
                    gerar_planilha(registros, nome_usuario)
                    progresso.progress(95)
                    
                    status.write("✅ Processamento concluído!")
                    progresso.progress(100)
                    
                    st.success(f"✅ Sucesso! {len(registros)} registros processados para {nome_usuario}")
                    st.info("📊 Vá para a aba **Dashboard** para visualizar seus dados!")
                    
                except Exception as e:
                    st.error(f"❌ Erro: {str(e)}")

# ============ PÁGINA DASHBOARD ============
elif pagina == "📊 Dashboard":
    st.markdown("# 📊 Dashboard")
    
    if not os.path.exists("dashboard/dashboard_data.json"):
        st.warning("⚠️ Nenhum dado processado ainda. Vá para a aba **Inicial** e processe seus dados.")
    else:
        with open("dashboard/dashboard_data.json") as f:
            data = json.load(f)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"## 👤 {data.get('usuario', 'Usuário')}")
        with col2:
            st.caption(f"Atualizado: {data.get('data_relatorio', 'N/A')}")
        
        st.markdown("---")
        
        st.markdown("## 📈 Resumo")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Saldo Atual", data["kpis"]["saldo_atual"])
        with col2:
            st.metric("Dias Crédito", data["kpis"]["dias_credito"])
        with col3:
            st.metric("Dias Débito", data["kpis"]["dias_debito"])
        with col4:
            st.metric("Dias Trabalhados", data["kpis"]["dias_trabalhados"])
        
        st.markdown("---")
        
        st.markdown("## 📉 Evolução do Saldo")
        df_evolucao = pd.DataFrame(data["evolucao"])
        st.line_chart(df_evolucao.set_index("data")["saldo"])
        
        st.markdown("---")
        
        st.markdown("## 📋 Detalhes Diários")
        df_detalhes = pd.DataFrame(data["detalhes"])
        st.dataframe(df_detalhes, use_container_width=True)
        
        st.markdown("---")
        
        st.markdown("## 💾 Exportar Dados")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if os.path.exists("controle_banco_horas.xlsx"):
                df = pd.read_excel("controle_banco_horas.xlsx")
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Baixar CSV",
                    data=csv,
                    file_name=f"banco_horas_{data.get('usuario', 'relatorio').replace(' ', '_')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if os.path.exists("controle_banco_horas.xlsx"):
                with open("controle_banco_horas.xlsx", "rb") as f:
                    excel_data = f.read()
                st.download_button(
                    label="📄 Baixar Excel",
                    data=excel_data,
                    file_name=f"banco_horas_{data.get('usuario', 'relatorio').replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        with col3:
            if os.path.exists("controle_banco_horas.xlsx"):
                df = pd.read_excel("controle_banco_horas.xlsx")
                periodo_inicio = df["Data"].min() if not df.empty else "N/A"
                periodo_fim = df["Data"].max() if not df.empty else "N/A"
                pdf_data = gerar_pdf(df, data.get('usuario', 'Usuário'), periodo_inicio, periodo_fim)
                st.download_button(
                    label="📊 Baixar PDF",
                    data=pdf_data,
                    file_name=f"banco_horas_{data.get('usuario', 'relatorio').replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )

# ============ PÁGINA DADOS ============
elif pagina == "📋 Dados":
    st.markdown("# 📋 Dados Processados")
    
    if not os.path.exists("controle_banco_horas.xlsx"):
        st.warning("⚠️ Nenhum dado processado ainda.")
    else:
        df = pd.read_excel("controle_banco_horas.xlsx")
        
        if os.path.exists("dashboard/dashboard_data.json"):
            with open("dashboard/dashboard_data.json") as f:
                data = json.load(f)
                st.markdown(f"## 👤 {data.get('usuario', 'Usuário')}")
        
        st.markdown("## 📊 Tabela Completa")
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.markdown("## 📈 Estatísticas")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Dias", len(df))
        with col2:
            st.metric("Período", f"{df['Data'].min()} a {df['Data'].max()}")
        with col3:
            st.metric("Registros", len(df))
        
        st.markdown("---")
        st.markdown("## 💾 Exportar Dados")
        
        col1, col2, col3 = st.columns(3)
        
        usuario = data.get('usuario', 'relatorio').replace(' ', '_') if 'data' in locals() else 'relatorio'
        
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Baixar CSV",
                data=csv,
                file_name=f"banco_horas_{usuario}.csv",
                mime="text/csv"
            )
        
        with col2:
            with open("controle_banco_horas.xlsx", "rb") as f:
                excel_data = f.read()
            st.download_button(
                label="📄 Baixar Excel",
                data=excel_data,
                file_name=f"banco_horas_{usuario}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col3:
            periodo_inicio = df["Data"].min() if not df.empty else "N/A"
            periodo_fim = df["Data"].max() if not df.empty else "N/A"
            usuario_display = data.get('usuario', 'Usuário') if 'data' in locals() else 'Usuário'
            pdf_data = gerar_pdf(df, usuario_display, periodo_inicio, periodo_fim)
            st.download_button(
                label="📊 Baixar PDF",
                data=pdf_data,
                file_name=f"banco_horas_{usuario}.pdf",
                mime="application/pdf"
            )

# ============ PÁGINA CONFIGURAÇÕES ============
elif pagina == "⚙️ Configurações":
    st.markdown("# ⚙️ Configurações")
    
    st.markdown("## 📝 Informações do Sistema")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **Sistema:** Senior Ponto
        **Versão:** 2.1 Web
        **Data:** Janeiro 2026
        **Status:** ✅ Pronto
        """)
    
    with col2:
        st.info("""
        **Python:** 3.8+
        **Framework:** Streamlit
        **Drivers:** Selenium
        **Banco:** Pandas + OpenPyXL
        """)
    
    st.markdown("---")
    
    st.markdown("## 📖 Como Usar")
    
    with st.expander("ℹ️ Passo a Passo"):
        st.markdown("""
        1. **Acesse a aba Inicial**
        2. **Preencha seu login e senha** do Senior Ponto
        3. **Selecione o período** que deseja extrair
        4. **Clique em PROCESSAR** e aguarde
        5. **Visualize no Dashboard** os resultados
        """)
    
    with st.expander("🔒 Segurança"):
        st.markdown("""
        - ✅ Dados processados localmente
        - ✅ Nenhuma informação armazenada em servidor externo
        - ✅ Senha usada apenas para autenticação
        - ✅ Totalmente seguro e privado
        """)
    
    with st.expander("📥 Exportação"):
        st.markdown("""
        Exporte seus dados em 3 formatos:
        - **CSV**: Para Excel ou Google Sheets
        - **Excel**: Arquivo .xlsx completo
        - **PDF**: Relatório profissional formatado
        """)
    
    st.markdown("---")
    
    st.markdown("## 🎯 Desenvolvido por")
    st.markdown("""
    <div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #2563EB 0%, #1E40AF 100%);
                border-radius: 12px; color: white;'>
        <h3 style='margin: 0 0 5px 0; color: white;'>João Pedro da Silveira</h3>
        <p style='margin: 0; opacity: 0.9;'>Sistema de Extração Automática de Banco de Horas</p>
        <p style='margin: 8px 0 0 0; opacity: 0.7; font-size: 13px;'>Versão 2.1 - 2026</p>
    </div>
    """, unsafe_allow_html=True)

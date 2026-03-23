import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Bot de Reservas", layout="wide")
st.title("Bot de Reservas")

COLUNAS = {
    "Informe a data da reserva:": "Data da reserva",
    "Pais": "País",
    "Informe a sociedade": "Sociedade",
    "Pagamento ou Recebimento": "Pagamento ou Recebimento",
    "Informe o banco": "Banco",
    "Selecione a conta corrente": "Conta corrente",
    "Valor": "Valor",
    "Descrição": "Descrição",
    "Área solicitante": "Área solicitante",
    "User solicitante": "User solicitante",
}

def get_email_from_user(username):
    # TODO: integrar com Active Directory da empresa
    return f"{username.lower()}@empresa.com"

def send_email(to_email, df):
    # TODO: configurar SMTP corporativo
    st.info(f"[SIMULAÇÃO] E-mail enviado para {to_email}")

def ler_planilha(arquivo):
    df = pd.read_excel(arquivo)
    df = df.rename(columns=COLUNAS)
    df = df[[c for c in COLUNAS.values() if c in df.columns]]
    df = df.dropna(how="all").reset_index(drop=True)
    df = df.astype(str).replace("nan", "")
    return df

def validar_dados(df):
    erros = []
    campos_obrigatorios = list(COLUNAS.values())

    for i, row in df.iterrows():
        linha = i + 1

        # Campos obrigatórios
        for campo in campos_obrigatorios:
            if campo not in row or str(row[campo]).strip() == "":
                erros.append(f"Linha {linha}: campo **{campo}** está vazio.")

        # Validação de data (dd/mm/aaaa)
        data_str = str(row.get("Data da reserva", "")).strip()
        if data_str:
            # Aceita tanto dd/mm/aaaa quanto ddmmaaaa
            data_limpa = data_str.replace("/", "").replace("-", "")
            if len(data_limpa) == 8 and data_limpa.isdigit():
                try:
                    datetime.strptime(data_limpa, "%d%m%Y")
                except ValueError:
                    erros.append(f"Linha {linha}: **Data da reserva** inválida. Use o formato dd/mm/aaaa.")
            else:
                erros.append(f"Linha {linha}: **Data da reserva** inválida. Use o formato dd/mm/aaaa.")

        # Validação de valor numérico e maior que zero
        valor_str = str(row.get("Valor", "")).strip()
        if valor_str:
            try:
                valor = float(valor_str.replace(",", "."))
                if valor <= 0:
                    erros.append(f"Linha {linha}: **Valor** deve ser maior que zero.")
            except ValueError:
                erros.append(f"Linha {linha}: **Valor** deve ser numérico.")

    return erros

# Inicializa estado
if "etapa" not in st.session_state:
    st.session_state.etapa = "upload"
if "df" not in st.session_state:
    st.session_state.df = None

# ─── ETAPA 1: UPLOAD ────────────────────────────────────────────────────────
if st.session_state.etapa == "upload":
    st.subheader("Passo 1 - Envie a planilha preenchida")
    arquivo = st.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"])

    if arquivo:
        df = ler_planilha(arquivo)
        if not df.empty:
            st.success(f"Planilha lida com sucesso! {len(df)} registro(s) encontrado(s).")
            st.dataframe(df, use_container_width=True)
            if st.button("Processar informações"):
                erros = validar_dados(df)
                if erros:
                    st.error("Corrija os erros abaixo antes de continuar:")
                    for erro in erros:
                        st.warning(erro)
                else:
                    st.session_state.df = df
                    st.session_state.etapa = "processar"
                    st.rerun()
        else:
            st.error("Não foi possível ler os dados da planilha. Verifique o formato.")

# ─── ETAPA 2: CONFIRMAR PROCESSAMENTO ───────────────────────────────────────
elif st.session_state.etapa == "processar":
    st.subheader("Passo 2 - Confirme os dados")
    st.dataframe(st.session_state.df, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Sim - Processar"):
            st.session_state.etapa = "resumo"
            st.rerun()
    with col2:
        if st.button("✏️ Não - Editar dados"):
            st.session_state.etapa = "editar"
            st.rerun()

# ─── ETAPA 3: EDIÇÃO ────────────────────────────────────────────────────────
elif st.session_state.etapa == "editar":
    st.subheader("Editar dados")
    df_editado = st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic")

    if st.button("Salvar alterações"):
        erros = validar_dados(df_editado)
        if erros:
            st.error("Corrija os erros abaixo antes de continuar:")
            for erro in erros:
                st.warning(erro)
        else:
            st.session_state.df = df_editado
            st.session_state.etapa = "processar"
            st.rerun()

# ─── ETAPA 4: RESUMO E CONFIRMAÇÃO FINAL ────────────────────────────────────
elif st.session_state.etapa == "resumo":
    st.subheader("Resumo do processamento")
    df = st.session_state.df
    st.write(f"**Processado em:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    st.dataframe(df, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Sim - Confirmar e gravar"):
            st.session_state.etapa = "concluido"
            st.rerun()
    with col2:
        if st.button("✏️ Não - Editar dados"):
            st.session_state.etapa = "editar"
            st.rerun()

# ─── ETAPA 5: CONCLUÍDO ─────────────────────────────────────────────────────
elif st.session_state.etapa == "concluido":
    st.success("✅ Dados gravados com sucesso!")
    df = st.session_state.df
    usuarios = df["User solicitante"].dropna().unique()
    for username in usuarios:
        email = get_email_from_user(username)
        send_email(email, df)
        st.write(f"Resumo enviado por e-mail para: **{email}**")
    st.markdown("---")
    st.dataframe(df, use_container_width=True)

    if st.button("Nova reserva"):
        st.session_state.etapa = "upload"
        st.session_state.df = None
        st.rerun()

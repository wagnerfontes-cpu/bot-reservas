import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta

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

BRASILIA = timezone(timedelta(hours=-3))

def horario_brasilia():
    return datetime.now(BRASILIA)

def apos_limite():
    agora = horario_brasilia()
    limite = agora.replace(hour=13, minute=0, second=0, microsecond=0)
    return agora > limite

def get_email_from_user(username):
    # TODO: integrar com Active Directory da empresa
    return f"{username.lower()}@empresa.com"

def send_email(to_email, df):
    # TODO: configurar SMTP corporativo
    st.info(f"[SIMULAÇÃO] E-mail enviado para {to_email}")

def verificar_duplicata(row):
    # TODO: substituir pela consulta real ao BigQuery quando as credenciais estiverem disponíveis
    # Exemplo de query a ser executada:
    # SELECT * FROM `projeto.dataset.reservas`
    # WHERE user_solicitante = '{user}'
    #   AND data_reserva = '{data}'
    #   AND banco = '{banco}'
    #   AND conta_corrente = '{conta}'
    #   AND sociedade = '{sociedade}'
    # LIMIT 1
    return None  # Retorna None quando não há duplicata, ou um dict com os dados do registro anterior

def formatar_valor(val):
    if pd.isna(val) or str(val).strip() == "":
        return ""
    try:
        numero = float(str(val).replace(".", "").replace(",", "."))
        return f"{numero:_.2f}".replace(".", ",").replace("_", ".")
    except Exception:
        return str(val)

def ler_planilha(arquivo):
    df = pd.read_excel(arquivo)
    df = df.rename(columns=COLUNAS)
    df = df[[c for c in COLUNAS.values() if c in df.columns]]
    df = df.dropna(how="all").reset_index(drop=True)
    if "Data da reserva" in df.columns:
        def formatar_data(val):
            if pd.isna(val) or str(val).strip() == "":
                return ""
            try:
                if hasattr(val, 'strftime'):
                    return val.strftime("%d/%m/%Y")
                data_limpa = str(val).replace("/", "").replace("-", "").strip()
                if len(data_limpa) == 8 and data_limpa.isdigit():
                    return datetime.strptime(data_limpa, "%d%m%Y").strftime("%d/%m/%Y")
            except Exception:
                pass
            return str(val)
        df["Data da reserva"] = df["Data da reserva"].apply(formatar_data)
    if "Valor" in df.columns:
        df["Valor"] = df["Valor"].apply(formatar_valor)
    df = df.astype(str).replace("nan", "")
    return df

def validar_dados(df, checar_justificativa=False):
    erros = []
    campos_obrigatorios = list(COLUNAS.values())

    for i, row in df.iterrows():
        linha = i + 1

        for campo in campos_obrigatorios:
            if campo not in row or str(row[campo]).strip() == "":
                erros.append(f"Linha {linha}: campo **{campo}** está vazio.")

        data_str = str(row.get("Data da reserva", "")).strip()
        if data_str:
            data_limpa = data_str.replace("/", "").replace("-", "")
            if len(data_limpa) == 8 and data_limpa.isdigit():
                try:
                    datetime.strptime(data_limpa, "%d%m%Y")
                except ValueError:
                    erros.append(f"Linha {linha}: **Data da reserva** inválida. Use o formato dd/mm/aaaa.")
            else:
                erros.append(f"Linha {linha}: **Data da reserva** inválida. Use o formato dd/mm/aaaa.")

        valor_str = str(row.get("Valor", "")).strip()
        if valor_str:
            try:
                valor = float(valor_str.replace(",", "."))
                if valor <= 0:
                    erros.append(f"Linha {linha}: **Valor** deve ser maior que zero.")
            except ValueError:
                erros.append(f"Linha {linha}: **Valor** deve ser numérico.")

        if checar_justificativa:
            justificativa = str(row.get("Justificativa", "")).strip()
            if not justificativa:
                erros.append(f"Linha {linha}: campo **Justificativa** é obrigatório para nova solicitação.")

    return erros

# ─── Inicializa estado ───────────────────────────────────────────────────────
for key, val in {
    "etapa": "upload",
    "df": None,
    "df_anterior": None,
    "erros_validacao": [],
    "fora_horario": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

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
                st.session_state.df = df
                if erros:
                    st.session_state.erros_validacao = erros
                else:
                    st.session_state.erros_validacao = []
                    st.session_state.etapa = "processar"
                st.rerun()

            if st.session_state.erros_validacao:
                st.error("Foram encontrados erros. Corrija abaixo ou ajuste a planilha e suba novamente:")
                for erro in st.session_state.erros_validacao:
                    st.warning(erro)
                if st.button("✏️ Corrigir diretamente na tela"):
                    st.session_state.erros_validacao = []
                    st.session_state.etapa = "editar"
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
            # Verifica duplicata para cada linha
            duplicatas = []
            for i, row in st.session_state.df.iterrows():
                registro_anterior = verificar_duplicata(row)
                if registro_anterior:
                    duplicatas.append((i, registro_anterior))

            if duplicatas:
                st.session_state.df_anterior = duplicatas[0][1]
                st.session_state.etapa = "duplicata"
            else:
                st.session_state.etapa = "resumo"
            st.rerun()
    with col2:
        if st.button("✏️ Não - Editar dados"):
            st.session_state.etapa = "editar"
            st.rerun()

# ─── ETAPA 3: EDIÇÃO ────────────────────────────────────────────────────────
elif st.session_state.etapa == "editar":
    st.subheader("Editar dados")

    if st.session_state.erros_validacao:
        st.error("Corrija os erros abaixo antes de continuar:")
        for erro in st.session_state.erros_validacao:
            st.warning(erro)

    df_editado = st.data_editor(st.session_state.df, use_container_width=True, num_rows="dynamic")

    if st.button("Salvar alterações"):
        erros = validar_dados(df_editado)
        if erros:
            st.session_state.erros_validacao = erros
            st.session_state.df = df_editado
            st.rerun()
        else:
            st.session_state.erros_validacao = []
            st.session_state.df = df_editado
            st.session_state.etapa = "processar"
            st.rerun()

# ─── ETAPA 4: DUPLICATA DETECTADA ───────────────────────────────────────────
elif st.session_state.etapa == "duplicata":
    st.warning("Já existe uma reserva registrada para este usuário, dia, banco, conta e empresa.")
    st.subheader("Reserva já registrada (somente leitura):")
    df_anterior = pd.DataFrame([st.session_state.df_anterior])
    st.dataframe(df_anterior, use_container_width=True)

    st.markdown("---")
    st.write("Deseja incluir uma nova solicitação?")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Sim - Incluir nova solicitação"):
            # Adiciona campo Justificativa ao novo registro
            df_novo = st.session_state.df.copy()
            if "Justificativa" not in df_novo.columns:
                df_novo["Justificativa"] = ""
            st.session_state.df = df_novo
            st.session_state.etapa = "nova_solicitacao"
            st.rerun()
    with col2:
        if st.button("❌ Não - Cancelar"):
            st.session_state.etapa = "upload"
            st.session_state.df = None
            st.session_state.df_anterior = None
            st.rerun()

# ─── ETAPA 5: NOVA SOLICITAÇÃO COM JUSTIFICATIVA ─────────────────────────────
elif st.session_state.etapa == "nova_solicitacao":
    st.subheader("Reserva já registrada (somente leitura):")
    df_anterior = pd.DataFrame([st.session_state.df_anterior])
    st.dataframe(df_anterior, use_container_width=True)

    st.markdown("---")
    st.subheader("Nova solicitação — preencha a Justificativa:")

    if st.session_state.erros_validacao:
        st.error("Corrija os erros abaixo antes de continuar:")
        for erro in st.session_state.erros_validacao:
            st.warning(erro)

    df_editado = st.data_editor(st.session_state.df, use_container_width=True, num_rows="fixed")

    if st.button("Salvar nova solicitação"):
        erros = validar_dados(df_editado, checar_justificativa=True)
        if erros:
            st.session_state.erros_validacao = erros
            st.session_state.df = df_editado
            st.rerun()
        else:
            st.session_state.erros_validacao = []
            st.session_state.df = df_editado
            st.session_state.etapa = "resumo"
            st.rerun()

# ─── ETAPA 6: RESUMO E CONFIRMAÇÃO FINAL ────────────────────────────────────
elif st.session_state.etapa == "resumo":
    st.subheader("Resumo do processamento")
    agora = horario_brasilia()
    st.write(f"**Processado em:** {agora.strftime('%d/%m/%Y %H:%M:%S')} (Brasília)")
    st.dataframe(st.session_state.df, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Sim - Confirmar e gravar"):
            st.session_state.fora_horario = apos_limite()
            st.session_state.etapa = "concluido"
            st.rerun()
    with col2:
        if st.button("✏️ Não - Editar dados"):
            st.session_state.etapa = "editar"
            st.rerun()

# ─── ETAPA 7: CONCLUÍDO ─────────────────────────────────────────────────────
elif st.session_state.etapa == "concluido":
    df = st.session_state.df

    if st.session_state.fora_horario:
        st.warning("⏰ Sua solicitação de alteração está em fluxo de aprovação. Aguarde retorno da Tesouraria.")
    else:
        st.success("✅ Dados gravados com sucesso!")

    usuarios = df["User solicitante"].dropna().unique()
    for username in usuarios:
        email = get_email_from_user(username)
        send_email(email, df)
        st.write(f"Resumo enviado por e-mail para: **{email}**")

    st.markdown("---")
    st.dataframe(df, use_container_width=True)

    if st.session_state.df_anterior:
        st.markdown("---")
        st.subheader("Reserva anterior registrada (somente leitura):")
        st.dataframe(pd.DataFrame([st.session_state.df_anterior]), use_container_width=True)

    if st.button("Nova reserva"):
        for key in ["etapa", "df", "df_anterior", "erros_validacao", "fora_horario"]:
            del st.session_state[key]
        st.rerun()

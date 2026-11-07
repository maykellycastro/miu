import os
import streamlit as st
import torch
try:
    from google import genai as genai_novo
    from google.genai import types as genai_types
    SDK_NOVO = True
except ImportError:
    import google.generativeai as genai_antigo
    SDK_NOVO = False
from transformers import pipeline
import re
import time
import urllib.parse
import calendar
from datetime import datetime, date
import pandas as pd
from diffusers import StableDiffusionPipeline


st.set_page_config(page_title="Assistente MIO", layout="wide")


# A chave NÃO deve ficar no código. Defina a variável de ambiente GEMINI_API_KEY
# (ou use st.secrets em .streamlit/secrets.toml).
# Para teste local: cole sua chave entre as aspas. Nunca compartilhe/suba este arquivo com a chave preenchida.
CHAVE_DIRETA = "AQ.Ab8RN6IEW5F7A67UD69guetICeyP1uGc33MkaaRaygRyf8iOCw"

def obter_chave_gemini():
    chave = CHAVE_DIRETA or os.getenv("AQ.Ab8RN6IEW5F7A67UD69guetICeyP1uGc33MkaaRaygRyf8iOCw")
    if not chave:
        try:
            chave = st.secrets["AQ.Ab8RN6IEW5F7A67UD69guetICeyP1uGc33MkaaRaygRyf8iOCw"]
        except Exception:
            chave = None
    return chave

GEMINI_API_KEY = obter_chave_gemini()
MSG_SEM_CHAVE = (
    "Chave do Gemini não configurada. Defina GEMINI_API_KEY (variável de ambiente ou "
    "arquivo .streamlit/secrets.toml) e reinicie o app."
)
MODELO_GEMINI = "gemini-2.5-flash"
SYSTEM_MIO = "Você é a MIO, uma assistente terapêutica. Seu objetivo é ajudar o usuário a explorar seus sentimentos."
SYSTEM_CLINICO = (
    "Você é um assistente de apoio à decisão clínica para psicólogos e psiquiatras. "
    "Você nunca emite diagnóstico definitivo: apenas hipóteses a serem investigadas "
    "pelo profissional, de forma cautelosa e baseada somente nos dados fornecidos."
)

def gerar_texto(prompt, system_instruction):
    """Chama o Gemini e devolve o texto. Levanta erro com mensagem clara se algo falhar."""
    if not GEMINI_API_KEY:
        raise RuntimeError(MSG_SEM_CHAVE)
    if SDK_NOVO:
        cliente = genai_novo.Client(api_key= "AQ.Ab8RN6IEW5F7A67UD69guetICeyP1uGc33MkaaRaygRyf8iOCw")
        resposta = cliente.models.generate_content(
            model=MODELO_GEMINI,
            contents=prompt,
            config=genai_types.GenerateContentConfig(system_instruction=system_instruction),
        )
    else:
        genai_antigo.configure(api_key="AQ.Ab8RN6IEW5F7A67UD69guetICeyP1uGc33MkaaRaygRyf8iOCw")
        modelo = genai_antigo.GenerativeModel(model_name=MODELO_GEMINI, system_instruction=system_instruction)
        resposta = modelo.generate_content(prompt)
    try:
        texto = resposta.text
    except Exception:
        texto = None
    if not texto:
        raise RuntimeError("O Gemini não retornou texto (a resposta pode ter sido bloqueada pelos filtros de segurança). Tente reformular.")
    return texto

# Configurações do envio de documentos
TIPOS_PERMITIDOS = ["pdf", "docx", "txt", "png", "jpg", "jpeg"]
TAMANHO_MAX_MB = 10


@st.cache_resource
def load_sentiment_model():
    return pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

@st.cache_resource
def load_image_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ultimo_erro = None
    for model_id in ("stable-diffusion-v1-5/stable-diffusion-v1-5", "runwayml/stable-diffusion-v1-5"):
        try:
            pipe = StableDiffusionPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32
            )
            return pipe.to(device)
        except Exception as e:
            ultimo_erro = e
    raise RuntimeError(f"Não foi possível carregar o modelo de imagem: {ultimo_erro}")

def clean_prompt(text):
    cleaned = re.sub(r'[^\w\s]', '', text)
    return cleaned[:100]

classifier = load_sentiment_model()


if "usuarios_db" not in st.session_state:
    st.session_state.usuarios_db = {"Duda": "1234"}
if "terapeutas_db" not in st.session_state:
    st.session_state.terapeutas_db = {"12345": "admin"} # CRP: Senha

if "autenticado" not in st.session_state: st.session_state.autenticado = False
if "historico_conversa" not in st.session_state: st.session_state.historico_conversa = []
if "meus_relatorios" not in st.session_state: st.session_state.meus_relatorios = []
if "meus_documentos" not in st.session_state: st.session_state.meus_documentos = []
if "quiz_cadastro_temp" not in st.session_state: st.session_state.quiz_cadastro_temp = None
if "quiz_inicial" not in st.session_state: st.session_state.quiz_inicial = {}
if "testes_personalidade" not in st.session_state: st.session_state.testes_personalidade = {}
if "contatos_familia" not in st.session_state: st.session_state.contatos_familia = {}
if "hipoteses_diagnosticas" not in st.session_state: st.session_state.hipoteses_diagnosticas = {}
if "historico_humor" not in st.session_state: st.session_state.historico_humor = {}
if "modo_terapeuta" not in st.session_state: st.session_state.modo_terapeuta = False
if "tela_atual" not in st.session_state: st.session_state.tela_atual = "login" # login, cadastro_user, cadastro_terapeuta
if "usuario_atual" not in st.session_state: st.session_state.usuario_atual = None



def exibir_calendario_humor():
    st.markdown("### 📅 Calendário de Humor")
    hoje = date.today()
    cal = calendar.Calendar(firstweekday=6)
    semanas = cal.monthdatescalendar(hoje.year, hoje.month)
    cols_header = st.columns(7)
    for i, nome_dia in enumerate(["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]):
        cols_header[i].caption(nome_dia)
    for semana in semanas:
        cols = st.columns(7)
        for i, dia in enumerate(semana):
            if dia.month == hoje.month:
                data_str = dia.strftime("%Y-%m-%d")
                humor = st.session_state.historico_humor.get(data_str, "")
                emoji = "😊" if humor == "POSITIVE" else "😔" if humor == "NEGATIVE" else ""
                with cols[i]:
                    st.write(f"**{dia.day}**")
                    if emoji: st.write(emoji)
            else:
                cols[i].write("")

@st.dialog("Relatório do Dia", width="large")
def modal_relatorio():
    st.write("### 📝 Reflexão Diária")
    with st.form("form_relatorio", clear_on_submit=True):
        data_relatorio = st.date_input("Data", value=date.today())
        titulo = st.text_input("Título do dia")
        conteudo = st.text_area("O que aconteceu hoje?", height=200)
        enviar = st.form_submit_button("Salvar Relatório", use_container_width=True)
        if enviar and conteudo:
            analise = classifier(conteudo[:512])[0]
            st.session_state.historico_humor[data_relatorio.strftime("%Y-%m-%d")] = analise['label']
            st.session_state.meus_relatorios.append({
                "usuario": st.session_state.usuario_atual,
                "data": data_relatorio,
                "titulo": titulo,
                "texto": conteudo,
                "humor": analise['label']
            })
            st.success("Relatório salvo!")
            time.sleep(1)
            st.rerun()

@st.dialog("MIO", width="large")
def modal_mio():
    tab1, tab2 = st.tabs(["Sentimento", "Conversa"])
    with tab1:
        st.subheader("Qual seu humor hoje?")
        sentiment_input = st.text_input("Como você se sente?")
        if st.button("Analisar Humor"):
            if sentiment_input:
                res = classifier(sentiment_input)[0]
                st.session_state.historico_humor[date.today().strftime("%Y-%m-%d")] = res['label']
                st.info(f"Sentimento registrado: {'😊' if res['label'] == 'POSITIVE' else '😔'}")
                st.rerun()
    with tab2:
        container_chat = st.container(height=400)
        with container_chat:
            for chat in st.session_state.historico_conversa:
                if chat.get("usuario") != st.session_state.usuario_atual:
                    continue
                with st.chat_message("user"): st.write(chat["pergunta"])
                with st.chat_message("assistant"):
                    st.write(chat["resposta"])
                    if chat.get("imagem"): st.image(chat["imagem"], width=400)
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_input("Diga algo:")
            gerar_img = st.checkbox(
                "Gerar imagem junto da resposta (muito lento sem placa de vídeo)",
                value=torch.cuda.is_available(),
            )
            if st.form_submit_button("Enviar") and user_input:
                resposta_txt = None
                try:
                    with st.spinner("A MIO está pensando..."):
                        resposta_txt = gerar_texto(user_input, SYSTEM_MIO)
                except Exception as e:
                    st.error(f"Erro ao falar com o Gemini: {e}")
                if resposta_txt:
                    img = None
                    if gerar_img:
                        try:
                            with st.spinner("Gerando imagem..."):
                                img = load_image_model()(prompt=f"Digital art, {clean_prompt(resposta_txt)}", num_inference_steps=20).images[0]
                        except Exception as e:
                            print(f"[MIO] imagem não gerada: {e}")
                            st.toast("A imagem não pôde ser gerada, mas a resposta foi salva.")
                    st.session_state.historico_conversa.append({"usuario": st.session_state.usuario_atual, "pergunta": user_input, "resposta": resposta_txt, "imagem": img})
                    st.rerun()


# ---------------------------------------------------------------------------
# NOVA FUNÇÃO: tela do usuário para enviar documentos
# ---------------------------------------------------------------------------
@st.dialog("Enviar Documentos", width="large")
def tela_enviar_documentos():
    st.write("### 📎 Enviar documentos ao terapeuta")
    st.caption(
        f"Formatos aceitos: {', '.join(t.upper() for t in TIPOS_PERMITIDOS)} "
        f"— até {TAMANHO_MAX_MB} MB por arquivo."
    )

    with st.form("form_documentos", clear_on_submit=True):
        arquivos = st.file_uploader(
            "Selecione um ou mais arquivos",
            type=TIPOS_PERMITIDOS,
            accept_multiple_files=True,
        )
        descricao = st.text_area(
            "Descrição (opcional)",
            placeholder="Ex.: laudo médico, exame, anotações...",
            height=100,
        )
        enviar = st.form_submit_button("Enviar", use_container_width=True)

        if enviar:
            if not arquivos:
                st.warning("Selecione pelo menos um arquivo.")
            else:
                enviados = 0
                for arq in arquivos:
                    if arq.size > TAMANHO_MAX_MB * 1024 * 1024:
                        st.error(f"'{arq.name}' passa de {TAMANHO_MAX_MB} MB e não foi enviado.")
                        continue
                    st.session_state.meus_documentos.append({
                        "usuario": st.session_state.usuario_atual,
                        "nome": arq.name,
                        "tipo": arq.type,
                        "tamanho": arq.size,
                        "conteudo": arq.getvalue(),
                        "descricao": descricao,
                        "data": datetime.now(),
                    })
                    enviados += 1
                if enviados:
                    st.success(f"{enviados} documento(s) enviado(s) com sucesso!")
                    time.sleep(1)
                    st.rerun()

    # Lista dos documentos já enviados pelo próprio usuário
    st.divider()
    st.write("#### Meus documentos enviados")
    meus = [d for d in st.session_state.meus_documentos
            if d["usuario"] == st.session_state.usuario_atual]
    if not meus:
        st.info("Você ainda não enviou nenhum documento.")
    else:
        for i, d in enumerate(reversed(meus)):
            kb = d["tamanho"] / 1024
            st.write(f"📄 **{d['nome']}** — {kb:.1f} KB — {d['data'].strftime('%d/%m/%Y %H:%M')}")
            if d["descricao"]:
                st.caption(d["descricao"])


# ---------------------------------------------------------------------------
# NOVAS FUNÇÕES: quiz do cadastro, teste de personalidade e ferramentas do terapeuta
# ---------------------------------------------------------------------------

# ---- Quiz do cadastro -----------------------------------------------------
QUIZ_PERGUNTAS = [
    "Pouco interesse ou prazer em fazer as coisas",
    "Sentir-se para baixo, deprimido(a) ou sem esperança",
    "Dificuldade para dormir ou dormir demais",
    "Sentir-se nervoso(a), ansioso(a) ou muito tenso(a)",
    "Cansaço ou falta de energia",
    "Dificuldade de concentração",
]
QUIZ_OPCOES = {
    "Nunca": 0,
    "Alguns dias": 1,
    "Mais da metade dos dias": 2,
    "Quase todos os dias": 3,
}
QUIZ_MAX = len(QUIZ_PERGUNTAS) * 3

def nivel_quiz(pontos):
    if pontos <= 5:
        return "Baixo"
    if pontos <= 11:
        return "Moderado"
    return "Alto"

@st.dialog("Quiz inicial", width="large")
def modal_quiz():
    st.write("### 🧠 Quiz de bem-estar")
    st.caption("Nas últimas 2 semanas, com que frequência você foi incomodado(a) por:")
    with st.form("form_quiz"):
        respostas = {}
        for i, pergunta in enumerate(QUIZ_PERGUNTAS):
            respostas[pergunta] = st.radio(
                pergunta, list(QUIZ_OPCOES.keys()), horizontal=True, key=f"quiz_{i}"
            )
        enviar = st.form_submit_button("Ver resultado", use_container_width=True)

    if enviar:
        pontos = sum(QUIZ_OPCOES[r] for r in respostas.values())
        st.session_state.quiz_cadastro_temp = {
            "respostas": respostas,
            "pontos": pontos,
            "nivel": nivel_quiz(pontos),
            "data": datetime.now(),
        }

    resultado = st.session_state.quiz_cadastro_temp
    if resultado:
        st.success(
            f"Quiz registrado: {resultado['pontos']}/{QUIZ_MAX} pontos "
            f"(nível de atenção: {resultado['nivel']})."
        )
        st.caption("Este quiz não é um diagnóstico; ele ajuda o terapeuta a conhecer você melhor.")
        if resultado["nivel"] == "Alto":
            st.warning(
                "Suas respostas indicam bastante sofrimento. Considere conversar com um "
                "profissional em breve. Se precisar de apoio imediato, ligue para o CVV: 188 (24h, gratuito)."
            )
        if st.button("Concluir", key="quiz_concluir", use_container_width=True):
            st.rerun()


# ---- Teste de personalidade (Big Five, versão curta de 10 itens) ----------
PERSONALIDADE_ITENS = [
    ("Extrovertido(a), entusiasmado(a)", "extroversao", False),
    ("Crítico(a), briguento(a)", "amabilidade", True),
    ("Confiável, autodisciplinado(a)", "conscienciosidade", False),
    ("Ansioso(a), facilmente chateado(a)", "estabilidade", True),
    ("Aberto(a) a novas experiências, criativo(a)", "abertura", False),
    ("Reservado(a), quieto(a)", "extroversao", True),
    ("Compreensivo(a), afetuoso(a)", "amabilidade", False),
    ("Desorganizado(a), descuidado(a)", "conscienciosidade", True),
    ("Calmo(a), emocionalmente estável", "estabilidade", False),
    ("Convencional, pouco criativo(a)", "abertura", True),
]
TRACOS = {
    "extroversao": "Extroversão",
    "amabilidade": "Amabilidade",
    "conscienciosidade": "Conscienciosidade",
    "estabilidade": "Estabilidade emocional",
    "abertura": "Abertura a experiências",
}

def exibir_resultado_personalidade(resultado):
    for chave, valor in resultado["tracos"].items():
        nivel = "baixa" if valor < 3 else "média" if valor <= 5 else "alta"
        st.write(f"**{TRACOS[chave]}** — {valor:.1f}/7 ({nivel})")
        st.progress((valor - 1) / 6)
    st.caption(f"Realizado em {resultado['data'].strftime('%d/%m/%Y %H:%M')}")

@st.dialog("Teste de Personalidade", width="large")
def modal_teste_personalidade():
    usuario = st.session_state.usuario_atual
    st.write("### 🧩 Teste de Personalidade (Big Five — versão curta)")
    st.caption("De 1 (discordo totalmente) a 7 (concordo totalmente): o quanto isso descreve você?")
    with st.form("form_personalidade"):
        respostas = []
        for i, (texto, _, _) in enumerate(PERSONALIDADE_ITENS):
            respostas.append(st.slider(f"Eu me vejo como: {texto}", 1, 7, 4, key=f"pers_{i}"))
        enviar = st.form_submit_button("Ver resultado", use_container_width=True)

    if enviar:
        somas = {chave: [] for chave in TRACOS}
        for valor, (_, traco, invertido) in zip(respostas, PERSONALIDADE_ITENS):
            somas[traco].append(8 - valor if invertido else valor)
        st.session_state.testes_personalidade[usuario] = {
            "tracos": {chave: sum(v) / len(v) for chave, v in somas.items()},
            "data": datetime.now(),
        }

    resultado = st.session_state.testes_personalidade.get(usuario)
    if resultado:
        st.divider()
        st.write("#### Seu resultado")
        exibir_resultado_personalidade(resultado)
        st.caption("Este teste é apenas um retrato de como você se vê hoje, não um diagnóstico.")


# ---- Ferramentas do terapeuta ---------------------------------------------

def lista_pacientes():
    return sorted(st.session_state.usuarios_db.keys())

def rotulo_humor(label):
    return "😊 Positivo" if label == "POSITIVE" else "😔 Negativo" if label == "NEGATIVE" else "—"

def dados_do_paciente(paciente):
    relatorios = sorted(
        [r for r in st.session_state.meus_relatorios if r.get("usuario") == paciente],
        key=lambda r: r["data"],
    )
    documentos = [d for d in st.session_state.meus_documentos if d["usuario"] == paciente]
    conversas = [c for c in st.session_state.historico_conversa if c.get("usuario") == paciente]
    return relatorios, documentos, conversas

def montar_resumo_paciente(paciente):
    relatorios, _, conversas = dados_do_paciente(paciente)
    quiz = st.session_state.quiz_inicial.get(paciente)
    pers = st.session_state.testes_personalidade.get(paciente)
    partes = []
    if quiz:
        partes.append(f"Quiz inicial de bem-estar: {quiz['pontos']}/{QUIZ_MAX} pontos (nível {quiz['nivel']}).")
        for pergunta, resposta in quiz["respostas"].items():
            partes.append(f"  - {pergunta}: {resposta}")
    if pers:
        partes.append(
            "Teste de personalidade (escala 1 a 7): "
            + ", ".join(f"{TRACOS[k]} {v:.1f}" for k, v in pers["tracos"].items())
        )
    for r in relatorios[-10:]:
        partes.append(
            f"Relatório {r['data'].strftime('%d/%m/%Y')} | humor: {r['humor']} | "
            f"título: {r['titulo']} | texto: {r['texto'][:800]}"
        )
    for c in conversas[-10:]:
        partes.append(f"Fala do paciente à MIO: {c['pergunta'][:300]}")
    return "\n".join(partes)

def link_whatsapp(telefone, mensagem):
    digitos = re.sub(r"\D", "", telefone)
    if len(digitos) in (10, 11):
        digitos = "55" + digitos
    return f"https://wa.me/{digitos}?text={urllib.parse.quote(mensagem)}"


def tela_historico_paciente():
    st.markdown("### 🗂️ Histórico do Paciente")
    pacientes = lista_pacientes()
    if not pacientes:
        st.info("Nenhum paciente cadastrado.")
        return
    paciente = st.selectbox("Paciente", pacientes, key="hist_paciente")
    relatorios, documentos, conversas = dados_do_paciente(paciente)
    quiz = st.session_state.quiz_inicial.get(paciente)
    pers = st.session_state.testes_personalidade.get(paciente)

    m1, m2, m3 = st.columns(3)
    m1.metric("Relatórios", len(relatorios))
    m2.metric("Documentos", len(documentos))
    m3.metric("Conversas com a MIO", len(conversas))

    t_rel, t_doc, t_conv, t_testes = st.tabs(["Relatórios", "Documentos", "Conversas", "Quiz e Personalidade"])

    with t_rel:
        if not relatorios:
            st.info("Nenhum relatório deste paciente.")
        for r in sorted(relatorios, key=lambda r: r["data"], reverse=True):
            with st.expander(f"{r['data'].strftime('%d/%m/%Y')} — {r['titulo'] or 'Sem título'} ({rotulo_humor(r['humor'])})"):
                st.write(r["texto"])

    with t_doc:
        if not documentos:
            st.info("Nenhum documento deste paciente.")
        for i, d in enumerate(reversed(documentos)):
            with st.expander(f"{d['data'].strftime('%d/%m/%Y %H:%M')} — {d['nome']}"):
                if d["descricao"]:
                    st.write(d["descricao"])
                st.download_button(
                    "Baixar documento",
                    data=d["conteudo"],
                    file_name=d["nome"],
                    mime=d["tipo"] or "application/octet-stream",
                    key=f"hist_dl_{paciente}_{i}",
                )

    with t_conv:
        if not conversas:
            st.info("Nenhuma conversa deste paciente com a MIO.")
        for c in conversas:
            with st.chat_message("user"):
                st.write(c["pergunta"])
            with st.chat_message("assistant"):
                st.write(c["resposta"])

    with t_testes:
        st.write("**Quiz inicial**")
        if quiz:
            st.write(f"{quiz['pontos']}/{QUIZ_MAX} pontos — nível de atenção: {quiz['nivel']}")
            for pergunta, resposta in quiz["respostas"].items():
                st.caption(f"{pergunta}: {resposta}")
        else:
            st.info("O paciente não fez o quiz.")
        st.write("**Teste de personalidade**")
        if pers:
            exibir_resultado_personalidade(pers)
        else:
            st.info("O paciente não fez o teste de personalidade.")


def tela_planilha_pacientes():
    st.markdown("### 📊 Planilha de Pacientes")
    linhas = []
    for paciente in lista_pacientes():
        relatorios, documentos, conversas = dados_do_paciente(paciente)
        quiz = st.session_state.quiz_inicial.get(paciente)
        pers = st.session_state.testes_personalidade.get(paciente)
        ultimo = relatorios[-1] if relatorios else None
        linhas.append({
            "Paciente": paciente,
            "Relatórios": len(relatorios),
            "Documentos": len(documentos),
            "Conversas MIO": len(conversas),
            "Último relatório": ultimo["data"].strftime("%d/%m/%Y") if ultimo else "—",
            "Último humor": rotulo_humor(ultimo["humor"]) if ultimo else "—",
            "Quiz inicial": f"{quiz['nivel']} ({quiz['pontos']}/{QUIZ_MAX})" if quiz else "—",
            "Personalidade": "Feito" if pers else "—",
            "Contatos da família": len(st.session_state.contatos_familia.get(paciente, [])),
        })
    if not linhas:
        st.info("Nenhum paciente cadastrado.")
        return

    df = pd.DataFrame(linhas)
    busca = st.text_input("Buscar paciente", key="planilha_busca")
    if busca:
        df = df[df["Paciente"].str.contains(busca, case=False, na=False)]
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "Baixar planilha (CSV)",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="pacientes.csv",
        mime="text/csv",
    )


def tela_possiveis_diagnosticos():
    st.markdown("### 🩺 Possíveis Diagnósticos")
    st.warning(
        "Ferramenta de apoio ao profissional. As hipóteses geradas por IA NÃO são diagnóstico "
        "e não substituem a avaliação clínica. Os dados do paciente são enviados ao serviço de IA "
        "(Gemini) para a análise."
    )
    pacientes = lista_pacientes()
    if not pacientes:
        st.info("Nenhum paciente cadastrado.")
        return
    paciente = st.selectbox("Paciente", pacientes, key="diag_paciente")
    resumo = montar_resumo_paciente(paciente)

    with st.expander("Dados que serão analisados"):
        st.text(resumo if resumo else "Sem dados para este paciente.")
    observacoes = st.text_area("Suas observações clínicas (opcional)", key=f"diag_obs_{paciente}")

    if st.button("Gerar hipóteses diagnósticas", key="diag_gerar", use_container_width=True):
        if not GEMINI_API_KEY:
            st.error(MSG_SEM_CHAVE)
        elif not resumo:
            st.warning("Este paciente ainda não tem dados (relatórios, quiz, personalidade ou conversas).")
        else:
            prompt = f"""Dados do paciente "{paciente}":

{resumo}

Observações do terapeuta: {observacoes or 'nenhuma'}

Com base APENAS nesses dados, responda em português, com estas seções:
1. Resumo do quadro observado
2. Hipóteses a investigar (cite a categoria do CID-11 ou DSM-5-TR, o nível de confiança — baixo ou médio — e os sinais nos dados que a sustentam)
3. O que ainda falta avaliar (critérios, duração dos sintomas, prejuízo funcional, fatores de risco)
4. Instrumentos e perguntas sugeridos para a próxima sessão
5. Sinais de alerta que exijam atenção imediata, se houver

Não afirme diagnóstico. Deixe claro que são hipóteses para avaliação do profissional."""
            with st.spinner("Analisando os dados..."):
                try:
                    texto_hip = gerar_texto(prompt, SYSTEM_CLINICO)
                    st.session_state.hipoteses_diagnosticas[paciente] = {
                        "texto": texto_hip,
                        "data": datetime.now(),
                    }
                except Exception as e:
                    st.error(f"Erro ao gerar a análise: {e}")

    salvo = st.session_state.hipoteses_diagnosticas.get(paciente)
    if salvo:
        st.divider()
        st.caption(f"Gerado em {salvo['data'].strftime('%d/%m/%Y %H:%M')}")
        st.markdown(salvo["texto"])


def tela_contato_familia():
    st.markdown("### 👨‍👩‍👧 Contato com a Família")
    pacientes = lista_pacientes()
    if not pacientes:
        st.info("Nenhum paciente cadastrado.")
        return
    paciente = st.selectbox("Paciente", pacientes, key="fam_paciente")
    contatos = st.session_state.contatos_familia.setdefault(paciente, [])

    with st.form("form_novo_contato", clear_on_submit=True):
        st.write("**Adicionar contato**")
        nome = st.text_input("Nome do familiar")
        parentesco = st.selectbox("Parentesco", ["Mãe", "Pai", "Irmão(ã)", "Cônjuge", "Filho(a)", "Responsável legal", "Outro"])
        telefone = st.text_input("Telefone com DDD (WhatsApp)", placeholder="67 99999-9999")
        if st.form_submit_button("Salvar contato", use_container_width=True):
            digitos = re.sub(r"\D", "", telefone)
            if not nome or len(digitos) < 10:
                st.error("Informe o nome e um telefone válido com DDD.")
            else:
                contatos.append({"nome": nome, "parentesco": parentesco, "telefone": telefone})
                st.success("Contato salvo!")

    if not contatos:
        st.info("Nenhum contato de familiar cadastrado para este paciente.")
        return

    st.write("**Contatos cadastrados**")
    for i, c in enumerate(contatos):
        col_info, col_rm = st.columns([5, 1])
        col_info.write(f"👤 {c['nome']} ({c['parentesco']}) — {c['telefone']}")
        if col_rm.button("🗑️", key=f"fam_rm_{paciente}_{i}"):
            contatos.pop(i)
            st.rerun()

    st.divider()
    st.write("**Enviar mensagem**")
    opcoes = [f"{c['nome']} ({c['parentesco']})" for c in contatos]
    idx = st.selectbox("Contato", range(len(opcoes)), format_func=lambda i: opcoes[i], key=f"fam_sel_{paciente}")
    contato = contatos[idx]
    mensagem = st.text_area(
        "Mensagem",
        value=f"Olá, {contato['nome']}. Aqui é o(a) terapeuta responsável pelo acompanhamento de {paciente}. Gostaria de conversar com você quando for possível.",
        key=f"fam_msg_{paciente}_{idx}",
    )
    autorizado = st.checkbox(
        "O paciente autorizou o contato com este familiar",
        key=f"fam_aut_{paciente}_{idx}",
    )
    if autorizado:
        st.link_button("Abrir no WhatsApp 💬", link_whatsapp(contato["telefone"], mensagem), use_container_width=True)
    else:
        st.caption("Confirme a autorização do paciente (sigilo profissional) para liberar o envio.")


def tela_cadastro_terapeuta():
    empty_l, center_col, empty_r = st.columns([1, 1.5, 1])
    with center_col:
        st.markdown("<h2 style='text-align: center;'>CADASTRO DE TERAPEUTA</h2>", unsafe_allow_html=True)
        with st.form("form_reg_terapeuta"):
            novo_crp = st.text_input("Registro Profissional (CRP/CRM)")
            nova_senha = st.text_input("Defina uma Senha", type="password")
            confirmar = st.text_input("Confirme a Senha", type="password")
            if st.form_submit_button("Finalizar Cadastro", use_container_width=True):
                if novo_crp in st.session_state.terapeutas_db:
                    st.error("Este registro já está cadastrado.")
                elif nova_senha != confirmar:
                    st.error("As senhas não conferem.")
                elif novo_crp and nova_senha:
                    st.session_state.terapeutas_db[novo_crp] = nova_senha
                    st.success("Terapeuta cadastrado com sucesso!")
                    time.sleep(1)
                    st.session_state.tela_atual = "login"
                    st.rerun()
        if st.button("Voltar"):
            st.session_state.tela_atual = "login"
            st.rerun()

def login_terapeuta():
    st.markdown("## 🩺 Acesso Profissional")
    with st.form("form_terapeuta"):
        registro = st.text_input("CRP/CRM")
        senha_t = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            if registro in st.session_state.terapeutas_db and st.session_state.terapeutas_db[registro] == senha_t:
                st.session_state.autenticado = True
                st.session_state.modo_terapeuta = True
                st.session_state.usuario_atual = f"Terapeuta ({registro})"
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Voltar"):
            st.session_state.modo_terapeuta = False
            st.rerun()
    with col2:
        if st.button("Criar Conta de Terapeuta"):
            st.session_state.tela_atual = "cadastro_terapeuta"
            st.rerun()

def tela_cadastro_user():
    empty_l, center_col, empty_r = st.columns([1, 1.5, 1])
    with center_col:
        st.markdown("<h2 style='text-align: center;'>NOVO CADASTRO</h2>", unsafe_allow_html=True)
        with st.form("form_registro"):
            novo_usuario = st.text_input("Escolha um Usuário")
            nova_senha = st.text_input("Escolha uma Senha", type="password")
            confirmar = st.text_input("Confirme a Senha", type="password")
            if st.form_submit_button("Cadastrar", use_container_width=True):
                if novo_usuario in st.session_state.usuarios_db:
                    st.error("Usuário já existe.")
                elif nova_senha != confirmar:
                    st.error("As senhas não coincidem.")
                elif novo_usuario and nova_senha:
                    st.session_state.usuarios_db[novo_usuario] = nova_senha
                    if st.session_state.quiz_cadastro_temp:
                        st.session_state.quiz_inicial[novo_usuario] = st.session_state.quiz_cadastro_temp
                        st.session_state.quiz_cadastro_temp = None
                    st.success("Cadastro realizado!")
                    time.sleep(1)
                    st.session_state.tela_atual = "login"
                    st.rerun()
        if st.session_state.quiz_cadastro_temp:
            st.caption("✅ Quiz concluído — ele será vinculado ao seu cadastro.")
        if st.button("Fazer Quiz 🧠", use_container_width=True):
            modal_quiz()
        if st.button("Voltar para Login"):
            st.session_state.tela_atual = "login"
            st.rerun()

def login_screen():
    empty_l, center_col, empty_r = st.columns([1, 1.5, 1])
    with center_col:
        st.markdown("<h2 style='text-align: center;'>BEM VINDO</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                if usuario in st.session_state.usuarios_db and st.session_state.usuarios_db[usuario] == senha:
                    st.session_state.autenticado = True
                    st.session_state.usuario_atual = usuario
                    st.rerun()
                else:
                    st.error("Dados incorretos.")
        
        st.divider()
        if st.button("Criar Minha Conta ", use_container_width=True):
            st.session_state.tela_atual = "cadastro_user"
            st.rerun()
        if st.button("Sou Terapeuta 🩺", use_container_width=True):
            st.session_state.modo_terapeuta = True
            st.rerun()



if not st.session_state.autenticado:
    if st.session_state.tela_atual == "cadastro_terapeuta":
        tela_cadastro_terapeuta()
    elif st.session_state.modo_terapeuta:
        login_terapeuta()
    elif st.session_state.tela_atual == "cadastro_user":
        tela_cadastro_user()
    else:
        login_screen()
else:
    # --- ÁREA LOGADA ---
    if st.session_state.modo_terapeuta:
        st.title("👨‍⚕️ Painel do Terapeuta")
        st.write(f"Bem-vindo, {st.session_state.usuario_atual}")

        aba_rel, aba_docs, aba_hist, aba_plan, aba_diag, aba_fam = st.tabs([
            "📝 Relatórios", "📎 Documentos", "🗂️ Histórico", "📊 Planilha", "🩺 Possíveis Diagnósticos", "👨‍👩‍👧 Família"
        ])
        with aba_hist: tela_historico_paciente()
        with aba_plan: tela_planilha_pacientes()
        with aba_diag: tela_possiveis_diagnosticos()
        with aba_fam: tela_contato_familia()

        with aba_rel:
            if st.session_state.meus_relatorios:
                for r in st.session_state.meus_relatorios:
                    with st.expander(f"{r['data']} - Paciente: {r.get('usuario', 'Desconhecido')}"):
                        st.write(f"**Título:** {r['titulo']}")
                        st.write(r['texto'])
                        st.caption(f"Humor: {r['humor']}")
            else:
                st.info("Nenhum relatório disponível.")

        with aba_docs:
            if st.session_state.meus_documentos:
                for idx, d in enumerate(reversed(st.session_state.meus_documentos)):
                    titulo_doc = f"{d['data'].strftime('%d/%m/%Y %H:%M')} - Paciente: {d['usuario']} - {d['nome']}"
                    with st.expander(titulo_doc):
                        if d["descricao"]:
                            st.write(f"**Descrição:** {d['descricao']}")
                        st.caption(f"Tamanho: {d['tamanho'] / 1024:.1f} KB")
                        st.download_button(
                            "Baixar documento",
                            data=d["conteudo"],
                            file_name=d["nome"],
                            mime=d["tipo"] or "application/octet-stream",
                            key=f"dl_doc_{idx}",
                        )
            else:
                st.info("Nenhum documento recebido.")
    else:
        st.title("Sistema Operacional MIO")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Iniciar Conversa Terapêutica", use_container_width=True): modal_mio()
        with col2:
            if st.button("Escrever Relatório do Dia", use_container_width=True): modal_relatorio()
        col3, col4 = st.columns(2)
        with col3:
            if st.button("Enviar Documentos 📎", use_container_width=True): tela_enviar_documentos()
        with col4:
            if st.button("Teste de Personalidade 🧩", use_container_width=True): modal_teste_personalidade()

    # SIDEBAR
    with st.sidebar:
        st.write(f"Sessão: {st.session_state.usuario_atual}")
        if st.button("Sair"):
            st.session_state.autenticado = False
            st.session_state.modo_terapeuta = False
            st.session_state.tela_atual = "login"
            st.rerun()
        st.divider()
        exibir_calendario_humor()
        st.divider()
        st.link_button("Falar com Terapeuta", f"https://wa.me/5567984746659?text=Ajuda")

    
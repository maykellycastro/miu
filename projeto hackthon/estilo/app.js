// ===== Configuração =====
// Vazio = modo demonstração (tudo salvo no navegador). Para usar IA real, aponte para o seu backend
// (POST /chat, /sentimento, /diagnostico). A chave do Gemini deve ficar SOMENTE no servidor.
const API_URL = "";
const KEY = "mio";
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let db; try { db = JSON.parse(localStorage.getItem(KEY)); } catch (e) { }
// Demo: contas de teste iguais às do projeto Python (senhas em texto puro só valem no modo demo).
db = db || { users: { Duda: "1234" }, ther: { "12345": "admin" }, reports: [], docs: [], chats: [], mood: {}, quiz: {}, fam: {} };
db.pers ??= {};
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(db)); } catch (e) { toast("Armazenamento local cheio."); } };
const S = { view: "login", user: null, tmpQuiz: null, tab: "rel", pat: null, q: "", aut: false, msg: "", hip: {} };
const today = () => new Date().toLocaleDateString("sv");
const fmt = d => new Date(d).toLocaleString("pt-BR");
const EM = { POSITIVE: "😊", NEGATIVE: "😔", NEUTRAL: "😐" };
const pats = () => Object.keys(db.users).sort();
function toast(m) { const t = document.createElement("div"); t.className = "toast"; t.textContent = m; document.body.append(t); setTimeout(() => t.remove(), 2600); }

// ===== IA (backend ou demo) =====
async function api(path, body) {
  const r = await fetch(API_URL + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error("Erro " + r.status);
  return r.json();
}
async function sentimento(t) {
  if (API_URL) return (await api("/sentimento", { texto: t })).label;
  return /triste|mal|ansios|cansad|medo|sozinh|raiva|péssim|pessim/i.test(t) ? "NEGATIVE" : /feliz|bem|ótim|otim|alegr|calm|tranquil|grat|bom|boa/i.test(t) ? "POSITIVE" : "NEUTRAL";
}
async function conversar(t, img) {
  if (API_URL) return api("/chat", { mensagem: t, gerar_imagem: img }); // {resposta, imagem(URL ou data URI, opcional)}
  return { resposta: "Entendi: “" + t.slice(0, 80) + "”. Quer me contar mais sobre como isso faz você se sentir?" };
}

// ===== Quiz =====
const QP = ["Pouco interesse ou prazer em fazer as coisas", "Sentir-se para baixo, deprimido(a) ou sem esperança", "Dificuldade para dormir ou dormir demais", "Sentir-se nervoso(a), ansioso(a) ou muito tenso(a)", "Cansaço ou falta de energia", "Dificuldade de concentração"];
const QO = ["Nunca", "Alguns dias", "Mais da metade dos dias", "Quase todos os dias"];
const nivel = p => p <= 5 ? "Baixo" : p <= 11 ? "Moderado" : "Alto";
const quizTxt = q => q ? `${q.pontos}/18 pontos (nível ${q.nivel})` : "—";

// ===== Teste de personalidade (Big Five, versão curta) =====
const PI = [["Extrovertido(a), entusiasmado(a)", "extroversao", 0], ["Crítico(a), briguento(a)", "amabilidade", 1], ["Confiável, autodisciplinado(a)", "conscienciosidade", 0], ["Ansioso(a), facilmente chateado(a)", "estabilidade", 1], ["Aberto(a) a novas experiências, criativo(a)", "abertura", 0], ["Reservado(a), quieto(a)", "extroversao", 1], ["Compreensivo(a), afetuoso(a)", "amabilidade", 0], ["Desorganizado(a), descuidado(a)", "conscienciosidade", 1], ["Calmo(a), emocionalmente estável", "estabilidade", 0], ["Convencional, pouco criativo(a)", "abertura", 1]];
const TR = { extroversao: "Extroversão", amabilidade: "Amabilidade", conscienciosidade: "Conscienciosidade", estabilidade: "Estabilidade emocional", abertura: "Abertura a experiências" };
const persHtml = r => r ? Object.entries(r.tracos).map(([k, v]) => `<p><b>${TR[k]}</b> — ${v.toFixed(1)}/7 (${v < 3 ? "baixa" : v <= 5 ? "média" : "alta"})<progress max="6" value="${v - 1}" style="width:100%"></progress></p>`).join("") + `<small>Realizado em ${fmt(r.data)}</small>` : "<small>Não realizado.</small>";

// ===== Telas =====
const V = {}, T = {}, A = {}, F = {}, C = {};
const back = (to = "login") => `<button type="button" class="ghost" data-a="go:${to}">Voltar</button>`;
V.login = () => `<main class="card auth"><h1>BEM-VINDO</h1><form data-f="login" class="auth"><input name="u" placeholder="Usuário" required><input name="p" type="password" placeholder="Senha" required><button>Entrar</button></form><hr><button class="ghost" data-a="go:regUser">Criar minha conta</button><button class="ghost" data-a="go:loginT">Sou terapeuta 🩺</button></main>`;
V.regUser = () => `<main class="card auth"><h1>NOVO CADASTRO</h1><form data-f="regUser" class="auth"><input name="u" placeholder="Escolha um usuário" required><input name="p" type="password" placeholder="Senha" required><input name="c" type="password" placeholder="Confirme a senha" required><button>Cadastrar</button></form>${S.tmpQuiz ? "<small>✅ Quiz concluído: será vinculado ao seu cadastro.</small>" : ""}<button class="ghost" data-a="quiz">Fazer quiz 🧠</button>${back()}</main>`;
V.loginT = () => `<main class="card auth"><h1>🩺 Acesso profissional</h1><form data-f="loginT" class="auth"><input name="r" placeholder="CRP/CRM" required><input name="p" type="password" placeholder="Senha" required><button>Entrar</button></form><button class="ghost" data-a="go:regT">Criar conta de terapeuta</button>${back()}</main>`;
V.regT = () => `<main class="card auth"><h1>CADASTRO DE TERAPEUTA</h1><form data-f="regT" class="auth"><input name="r" placeholder="Registro profissional (CRP/CRM)" required><input name="p" type="password" placeholder="Senha" required><input name="c" type="password" placeholder="Confirme a senha" required><button>Finalizar cadastro</button></form>${back("loginT")}</main>`;

function cal(m) {
  const n = new Date(), y = n.getFullYear(), mo = n.getMonth(), first = new Date(y, mo, 1).getDay(), days = new Date(y, mo + 1, 0).getDate();
  let h = "<h3>📅 Calendário de humor</h3><div class='cal'>" + ["D", "S", "T", "Q", "Q", "S", "S"].map(d => `<small>${d}</small>`).join("") + "<i></i>".repeat(first);
  for (let d = 1; d <= days; d++) { const k = `${y}-${String(mo + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`; h += `<span>${d}<br>${EM[m[k]] || "&nbsp;"}</span>`; }
  return h + "</div>";
}
V.user = () => `<div class="layout"><aside class="card"><p>Sessão: <b>${esc(S.user)}</b></p><button class="ghost" data-a="logout">Sair</button><hr>${cal(db.mood[S.user] || {})}<hr><a class="btn" target="_blank" rel="noopener" href="https://wa.me/5567984746659?text=Ajuda">Falar com terapeuta</a></aside><main><h1>Sistema Operacional MIO</h1><div class="grid"><button class="tile" data-a="mChat">💬 Iniciar conversa terapêutica</button><button class="tile" data-a="mRep">📝 Escrever relatório do dia</button><button class="tile" data-a="mDocs">📎 Enviar documentos</button><button class="tile" data-a="mPers">🧩 Teste de personalidade</button></div></main></div>`;

const TABS = [["rel", "📝 Relatórios"], ["docs", "📎 Documentos"], ["hist", "🗂️ Histórico"], ["plan", "📊 Planilha"], ["diag", "🩺 Diagnósticos"], ["fam", "👨‍👩‍👧 Família"]];
V.ther = () => `<main class="wide"><div class="bar"><h1>👨‍⚕️ Painel do terapeuta</h1><button class="ghost" data-a="logout">Sair</button></div><p class="mu">Bem-vindo, ${esc(S.user)}</p><nav class="tabs">${TABS.map(([k, l]) => `<button class="${S.tab == k ? "on" : ""}" data-a="tab:${k}">${l}</button>`).join("")}</nav><section class="card">${T[S.tab]()}</section></main>`;

const selPat = () => { S.pat = pats().includes(S.pat) ? S.pat : pats()[0]; return pats().length ? `<select data-c="pat">${pats().map(p => `<option ${p == S.pat ? "selected" : ""}>${esc(p)}</option>`).join("")}</select>` : "<p>Nenhum paciente cadastrado.</p>"; };
const of = (list, p) => list.filter(x => x.u === p);
T.rel = () => db.reports.length ? db.reports.slice().reverse().map(r => `<details><summary>${esc(r.d)} · ${esc(r.u)} · ${EM[r.h] || ""} ${esc(r.t || "Sem título")}</summary><pre>${esc(r.x)}</pre></details>`).join("") : "<p>Nenhum relatório disponível.</p>";
T.docs = () => db.docs.length ? db.docs.slice().reverse().map(d => `<details><summary>${fmt(d.at)} · ${esc(d.u)} · ${esc(d.n)}</summary><p>${esc(d.desc)}</p><small>${(d.s / 1024).toFixed(1)} KB</small><br><a class="btn" download="${esc(d.n)}" href="${d.data}">Baixar</a></details>`).join("") : "<p>Nenhum documento recebido.</p>";
T.hist = () => {
  const s = selPat(), p = S.pat; if (!p) return s; const r = of(db.reports, p), c = of(db.chats, p);
  return `${s}<p>Relatórios: <b>${r.length}</b> · Documentos: <b>${of(db.docs, p).length}</b> · Conversas: <b>${c.length}</b></p><h3>Quiz inicial</h3><p>${quizTxt(db.quiz[p])}</p>${(db.quiz[p]?.respostas || []).map(([q, a]) => `<small>${esc(q)}: ${esc(a)}</small><br>`).join("")}<h3>Personalidade</h3>${persHtml(db.pers[p])}<h3>Documentos</h3>${of(db.docs, p).map(d => `<p>📄 ${esc(d.n)} · ${fmt(d.at)} <a download="${esc(d.n)}" href="${d.data}">Baixar</a></p>`).join("") || "<small>Nenhum.</small>"}<h3>Relatórios</h3>${r.map(x => `<details><summary>${esc(x.d)} · ${EM[x.h] || ""} ${esc(x.t)}</summary><pre>${esc(x.x)}</pre></details>`).join("") || "<small>Nenhum.</small>"}<h3>Conversas</h3><div class="chat">${c.map(x => `<p class="me">${esc(x.q)}</p><p class="ai">${esc(x.r)}</p>${x.img ? `<img src="${esc(x.img)}" alt="Imagem gerada pela MIO" style="max-width:100%;border-radius:10px">` : ""}`).join("") || "<small>Nenhuma.</small>"}</div>`;
};
const rows = () => pats().filter(p => p.toLowerCase().includes(S.q.toLowerCase())).map(p => {
  const r = of(db.reports, p).sort((a, b) => a.d < b.d ? -1 : 1), u = r.at(-1);
  return { Paciente: p, Relatórios: r.length, Documentos: of(db.docs, p).length, "Conversas MIO": of(db.chats, p).length, "Último relatório": u ? u.d : "—", "Último humor": u ? EM[u.h] : "—", Quiz: quizTxt(db.quiz[p]), Personalidade: db.pers[p] ? "Feito" : "—", Contatos: (db.fam[p] || []).length };
});
T.plan = () => { const r = rows(), h = r[0] ? Object.keys(r[0]) : []; return `<input data-c="q" placeholder="Buscar paciente (Enter)" value="${esc(S.q)}">${r.length ? `<div style="overflow:auto"><table><tr>${h.map(k => `<th>${k}</th>`).join("")}</tr>${r.map(o => `<tr>${h.map(k => `<td>${esc(o[k])}</td>`).join("")}</tr>`).join("")}</table></div><br><button data-a="csv">Baixar planilha (CSV)</button>` : "<p>Nenhum paciente.</p>"}`; };
const resumo = p => [db.quiz[p] ? "Quiz inicial: " + quizTxt(db.quiz[p]) + "\n" + db.quiz[p].respostas.map(([q, a]) => "- " + q + ": " + a).join("\n") : "", db.pers[p] ? "Teste de personalidade (1 a 7): " + Object.entries(db.pers[p].tracos).map(([k, v]) => TR[k] + " " + v.toFixed(1)).join(", ") : "", ...of(db.reports, p).slice(-10).map(r => `Relatório ${r.d} | humor ${r.h} | ${r.t} | ${r.x.slice(0, 800)}`), ...of(db.chats, p).slice(-10).map(c => "Fala do paciente à MIO: " + c.q.slice(0, 300))].filter(Boolean).join("\n");
T.diag = () => { const s = selPat(), p = S.pat; return `<p class="warn">Ferramenta de apoio ao profissional. Hipóteses geradas por IA <b>não</b> são diagnóstico e não substituem a avaliação clínica.</p>${s}${p ? `<details><summary>Dados que serão analisados</summary><pre>${esc(resumo(p) || "Sem dados.")}</pre></details><button data-a="diag">Gerar hipóteses diagnósticas</button>${S.hip[p] ? `<hr><pre>${esc(S.hip[p])}</pre>` : ""}` : ""}`; };
const wa = (t, m) => { let d = t.replace(/\D/g, ""); if (d.length == 10 || d.length == 11) d = "55" + d; return `https://wa.me/${d}?text=${encodeURIComponent(m)}`; };
T.fam = () => {
  const s = selPat(), p = S.pat; if (!p) return s; const l = db.fam[p] || [], msg = S.msg || `Olá. Aqui é o(a) terapeuta responsável pelo acompanhamento de ${p}. Gostaria de conversar com você quando for possível.`;
  return `${s}<form data-f="fam"><input name="n" placeholder="Nome do familiar" required><select name="k">${["Mãe", "Pai", "Irmão(ã)", "Cônjuge", "Filho(a)", "Responsável legal", "Outro"].map(o => `<option>${o}</option>`).join("")}</select><input name="t" placeholder="Telefone com DDD (WhatsApp)" required><button>Salvar contato</button></form><hr><textarea data-c="msg" rows="3">${esc(msg)}</textarea><label><input type="checkbox" data-c="aut" ${S.aut ? "checked" : ""} style="width:auto"> O paciente autorizou o contato com familiares</label>${l.map((c, i) => `<p>👤 ${esc(c.n)} (${esc(c.k)}) · ${esc(c.t)} ${S.aut ? `<a class="btn" target="_blank" rel="noopener" href="${wa(c.t, msg)}">WhatsApp</a>` : ""} <button class="ghost" data-a="rmfam:${i}">🗑️</button></p>`).join("") || "<small>Nenhum contato.</small>"}${S.aut ? "" : "<br><small>Confirme a autorização do paciente (sigilo profissional) para liberar o envio.</small>"}`;
};

// ===== Modais =====
const open = h => { $("#mb").innerHTML = h; $("#modal").hidden = false; };
A.close = () => { $("#modal").hidden = true; render(); };
const chatHtml = () => { const c = of(db.chats, S.user); return `<h2>MIO</h2><form data-f="humor" class="row"><input name="t" placeholder="Como você se sente hoje?" required><button>Registrar humor</button></form><div class="chat" id="chat">${c.map(x => `<p class="me">${esc(x.q)}</p><p class="ai">${esc(x.r)}</p>${x.img ? `<img src="${esc(x.img)}" alt="Imagem gerada pela MIO" style="max-width:100%;border-radius:10px">` : ""}`).join("") || "<small>Nenhuma conversa ainda.</small>"}</div><form data-f="chat"><div class="row"><input name="t" placeholder="Diga algo…" required autocomplete="off"><button>Enviar</button></div><label><input type="checkbox" name="img" style="width:auto"> Gerar imagem junto da resposta (lento sem placa de vídeo; requer backend)</label></form>`; };
const scrollChat = () => { const c = $("#chat"); if (c) c.scrollTop = c.scrollHeight; };
A.mChat = () => { open(chatHtml()); scrollChat(); };
A.mRep = () => open(`<h2>📝 Reflexão diária</h2><form data-f="rep"><input type="date" name="d" value="${today()}" required><input name="t" placeholder="Título do dia"><textarea name="x" rows="7" placeholder="O que aconteceu hoje?" required></textarea><button>Salvar relatório</button></form>`);
const docsHtml = () => `<h2>📎 Enviar documentos ao terapeuta</h2><small>Formatos: PDF, DOCX, TXT, PNG, JPG, JPEG · até 10 MB por arquivo.</small><form data-f="docs"><input type="file" name="arq" multiple accept=".pdf,.docx,.txt,.png,.jpg,.jpeg" required><textarea name="desc" rows="3" placeholder="Descrição (opcional): laudo, exame, anotações…"></textarea><button>Enviar</button></form><hr><h3>Meus documentos enviados</h3>${of(db.docs, S.user).reverse().map(d => `<p>📄 <b>${esc(d.n)}</b> · ${(d.s / 1024).toFixed(1)} KB · ${fmt(d.at)}<br><small>${esc(d.desc)}</small></p>`).join("") || "<small>Você ainda não enviou nenhum documento.</small>"}`;
A.mDocs = () => open(docsHtml());
A.mPers = () => open(`<h2>🧩 Teste de personalidade (Big Five, versão curta)</h2><small>De 1 (discordo totalmente) a 7 (concordo totalmente): o quanto isso descreve você?</small><form data-f="pers">${PI.map(([t], i) => `<p>Eu me vejo como: ${t}<input type="range" name="p${i}" min="1" max="7" value="4"></p>`).join("")}<button>Ver resultado</button></form>${db.pers[S.user] ? `<hr><h3>Seu último resultado</h3>${persHtml(db.pers[S.user])}` : ""}`);
A.quiz = () => open(`<h2>🧠 Quiz de bem-estar</h2><small>Nas últimas 2 semanas, com que frequência você foi incomodado(a) por:</small><form data-f="quiz">${QP.map((q, i) => `<p>${q}<br><span class="opts">${QO.map((o, j) => `<label><input type="radio" name="q${i}" value="${j}" required> ${o}</label>`).join("")}</span></p>`).join("")}<button>Ver resultado</button></form>`);

// ===== Ações =====
A.go = v => { S.view = v; render(); };
A.tab = v => { S.tab = v; render(); };
A.logout = () => { S.user = null; S.view = "login"; render(); };
A.rmfam = i => { db.fam[S.pat].splice(i, 1); save(); render(); };
A.csv = () => {
  const r = rows(), h = Object.keys(r[0]); const q = v => `"${String(v).replace(/"/g, '""')}"`;
  const b = new Blob(["\ufeff" + [h.map(q).join(","), ...r.map(o => h.map(k => q(o[k])).join(","))].join("\n")], { type: "text/csv" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = "pacientes.csv"; a.click();
};
A.diag = async () => {
  if (!API_URL) return toast("Conecte o backend (POST /diagnostico): a chave do Gemini deve ficar só no servidor."); const p = S.pat, r = resumo(p);
  if (!r) return toast("Este paciente ainda não tem dados."); toast("Analisando os dados…");
  try { S.hip[p] = (await api("/diagnostico", { paciente: p, resumo: r })).texto; render(); } catch (e) { toast("Erro ao gerar a análise: " + e.message); }
};
C.pat = v => { S.pat = v; render(); };
C.q = v => { S.q = v; render(); };
C.msg = v => { S.msg = v; render(); };
C.aut = (v, el) => { S.aut = el.checked; render(); };

F.login = d => { if (db.users[d.u] === d.p) { S.user = d.u; S.view = "user"; render(); } else toast("Dados incorretos."); };
F.loginT = d => { if (db.ther[d.r] === d.p) { S.user = `Terapeuta (${d.r})`; S.view = "ther"; render(); } else toast("Credenciais inválidas."); };
F.regUser = d => {
  if (d.u in db.users) return toast("Usuário já existe."); if (d.p !== d.c) return toast("As senhas não coincidem.");
  db.users[d.u] = d.p; if (S.tmpQuiz) { db.quiz[d.u] = S.tmpQuiz; S.tmpQuiz = null; } save(); toast("Cadastro realizado!"); S.view = "login"; render();
};
F.regT = d => {
  if (d.r in db.ther) return toast("Este registro já está cadastrado."); if (d.p !== d.c) return toast("As senhas não conferem.");
  db.ther[d.r] = d.p; save(); toast("Terapeuta cadastrado com sucesso!"); S.view = "loginT"; render();
};
F.pers = d => {
  const g = {}; PI.forEach(([, k, inv], i) => { const v = +d["p" + i]; (g[k] ??= []).push(inv ? 8 - v : v); });
  db.pers[S.user] = { tracos: Object.fromEntries(Object.entries(g).map(([k, a]) => [k, a.reduce((x, y) => x + y) / a.length])), data: Date.now() }; save();
  open(`<h2>Seu resultado</h2>${persHtml(db.pers[S.user])}<small>Este teste é apenas um retrato de como você se vê hoje, não um diagnóstico.</small><br><br><button data-a="close">Concluir</button>`);
};
F.quiz = d => {
  const pontos = QP.reduce((s, _, i) => s + +d["q" + i], 0); S.tmpQuiz = { pontos, nivel: nivel(pontos), respostas: QP.map((q, i) => [q, QO[d["q" + i]]]), data: Date.now() };
  open(`<h2>Quiz registrado</h2><p>${quizTxt(S.tmpQuiz)}</p><small>Este quiz não é um diagnóstico; ele ajuda o terapeuta a conhecer você melhor.</small>${S.tmpQuiz.nivel == "Alto" ? `<p class="warn">Suas respostas indicam bastante sofrimento. Considere conversar com um profissional em breve. Se precisar de apoio imediato, ligue para o CVV: <b>188</b> (24h, gratuito).</p>` : ""}<br><button data-a="close">Concluir</button>`);
};
F.humor = async d => { try { const l = await sentimento(d.t); (db.mood[S.user] ??= {})[today()] = l; save(); toast("Humor registrado: " + EM[l]); } catch (e) { toast("Erro: " + e.message); } };
F.chat = async d => { toast("A MIO está pensando…"); try { const r = await conversar(d.t, !!d.img); db.chats.push({ u: S.user, q: d.t, r: r.resposta, img: r.imagem }); save(); open(chatHtml()); scrollChat(); } catch (e) { toast("Erro ao falar com a MIO: " + e.message); } };
F.rep = async d => { try { const h = await sentimento(d.x); db.reports.push({ u: S.user, d: d.d, t: d.t, x: d.x, h }); (db.mood[S.user] ??= {})[d.d] = h; save(); toast("Relatório salvo!"); A.close(); } catch (e) { toast("Erro: " + e.message); } };
F.fam = (d, f) => { if (d.t.replace(/\D/g, "").length < 10) return toast("Informe um telefone válido com DDD."); (db.fam[S.pat] ??= []).push(d); save(); render(); };
F.docs = async (d, f) => {
  const ok = ["pdf", "docx", "txt", "png", "jpg", "jpeg"]; let n = 0;
  for (const a of f.arq.files) {
    if (!ok.includes(a.name.split(".").pop().toLowerCase())) { toast(`'${a.name}': formato não permitido.`); continue; }
    if (a.size > 10 * 1048576) { toast(`'${a.name}' passa de 10 MB.`); continue; }
    const data = await new Promise(r => { const fr = new FileReader(); fr.onload = () => r(fr.result); fr.readAsDataURL(a); });
    db.docs.push({ u: S.user, n: a.name, s: a.size, desc: d.desc, at: Date.now(), data }); n++;
  }
  if (n) { save(); toast(n + " documento(s) enviado(s)!"); open(docsHtml()); }
};

// ===== Eventos =====
function render() { $("#app").innerHTML = V[S.view](); }
document.addEventListener("click", e => { const b = e.target.closest("[data-a]"); if (b) { const [a, v] = b.dataset.a.split(":"); A[a]?.(v, b); } });
document.addEventListener("submit", async e => { const f = e.target.dataset.f; if (!f) return; e.preventDefault(); await F[f]?.(Object.fromEntries(new FormData(e.target)), e.target); });
document.addEventListener("change", e => { const c = e.target.dataset.c; if (c) C[c]?.(e.target.value, e.target); });
render();
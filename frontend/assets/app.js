"use strict";

/** Controla a interface web e mantém conteúdo externo fora do HTML executável. */
(function iniciarInterface() {
  const apiBase = document.querySelector('meta[name="api-base-url"]').content.replace(/\/$/, "");
  const limiteRequisicaoMs = 60_000;

  const elemento = (seletor) => document.querySelector(seletor);
  const elementos = (seletor) => Array.from(document.querySelectorAll(seletor));

  class ErroInterface extends Error {
    constructor(mensagem, campo = null) {
      super(mensagem);
      this.campo = campo;
    }
  }

  function obterTokenApi() {
    const tokenCodificado = document.querySelector('meta[name="api-auth-token"]')?.content.trim();
    if (!tokenCodificado || tokenCodificado === "__AUTH_TOKEN_BASE64__") {
      throw new ErroInterface("A credencial da interface não está configurada.");
    }

    try {
      const bytes = Uint8Array.from(window.atob(tokenCodificado), (caractere) => caractere.charCodeAt(0));
      const token = new TextDecoder().decode(bytes).trim();
      if (!token) throw new Error("Token vazio");
      return token;
    } catch (_erro) {
      throw new ErroInterface("A credencial da interface possui formato inválido.");
    }
  }

  function separarSprints(valor) {
    const sprints = valor
      .split(/[\n,]/)
      .map((sprint) => sprint.trim())
      .filter(Boolean);
    return [...new Set(sprints)];
  }

  function validarSprints(sprints, campo) {
    if (sprints.length > 20) {
      throw new ErroInterface("Informe no máximo 20 sprints por consulta.", campo);
    }
  }

  function criarElemento(tag, classe, texto) {
    const no = document.createElement(tag);
    if (classe) no.className = classe;
    if (texto !== undefined) no.textContent = String(texto);
    return no;
  }

  function preencherEtiquetas(container, valores) {
    container.replaceChildren();
    if (!valores.length) {
      container.append(criarElemento("span", "etiqueta neutra", "Nenhuma informada"));
      return;
    }
    valores.forEach((valor) => container.append(criarElemento("span", "etiqueta", valor)));
  }

  function mensagemDoErroHttp(status, corpo) {
    if (Array.isArray(corpo?.detail)) {
      const detalhes = corpo.detail.map((item) => item.msg).filter(Boolean);
      if (detalhes.length) return `Revise os dados informados: ${detalhes.join("; ")}.`;
    }
    if (typeof corpo?.detail === "string") return corpo.detail;

    const mensagens = {
      400: "A requisição enviada é inválida.",
      401: "A credencial configurada para a interface foi recusada.",
      404: "A sprint solicitada não foi encontrada.",
      413: "A requisição ultrapassou o tamanho permitido.",
      422: "Revise os dados informados.",
      429: "Limite de consultas atingido. Aguarde antes de tentar novamente.",
      502: "Uma integração necessária está temporariamente indisponível.",
      504: "A consulta excedeu o tempo limite. Tente novamente.",
    };
    return mensagens[status] || "Não foi possível concluir a consulta.";
  }

  async function chamarApi(caminho, payload) {
    const token = obterTokenApi();

    const controlador = new AbortController();
    const temporizador = window.setTimeout(() => controlador.abort(), limiteRequisicaoMs);

    try {
      const resposta = await fetch(`${apiBase}${caminho}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(payload),
        signal: controlador.signal,
        credentials: "omit",
      });
      const corpo = await resposta.json().catch(() => ({}));
      if (!resposta.ok) throw new ErroInterface(mensagemDoErroHttp(resposta.status, corpo));
      return corpo;
    } catch (erro) {
      if (erro.name === "AbortError") {
        throw new ErroInterface("A consulta demorou mais de 60 segundos e foi cancelada.");
      }
      if (erro instanceof ErroInterface) throw erro;
      throw new ErroInterface("Não foi possível conectar à API. Verifique se o ambiente está ativo.");
    } finally {
      window.clearTimeout(temporizador);
    }
  }

  function definirCarregamento(formulario, ativo) {
    formulario.setAttribute("aria-busy", String(ativo));
    const botao = formulario.querySelector('button[type="submit"]');
    botao.disabled = ativo;
    botao.classList.toggle("em-carregamento", ativo);
  }

  function mostrarErro(id, erro) {
    const caixa = elemento(id);
    caixa.textContent = erro.message;
    caixa.hidden = false;
    if (erro.campo) elemento(`#${erro.campo}`)?.focus();
  }

  function limparErro(id) {
    const caixa = elemento(id);
    caixa.textContent = "";
    caixa.hidden = true;
  }

  function validarTexto(campo, rotulo) {
    const valor = campo.value.trim();
    if (!valor) throw new ErroInterface(`${rotulo} não pode ficar em branco.`, campo.id);
    if (valor.length > 4000) throw new ErroInterface(`${rotulo} deve ter no máximo 4000 caracteres.`, campo.id);
    return valor;
  }

  function renderizarFontes(fontes) {
    const container = elemento("#fontes-resumo");
    container.replaceChildren();
    if (!fontes.length) {
      container.append(criarElemento("p", "estado-vazio", "A API não retornou fontes detalhadas."));
      return;
    }

    fontes.forEach((fonte, indice) => {
      const detalhes = criarElemento("details", "fonte-item");
      const titulo = fonte.titulo || fonte.caminho || `Fonte ${indice + 1}`;
      const resumo = criarElemento("summary", null);
      resumo.append(criarElemento("span", "fonte-indice", String(indice + 1).padStart(2, "0")));
      const identificacao = criarElemento("span", "fonte-identificacao");
      identificacao.append(criarElemento("strong", null, titulo));
      identificacao.append(criarElemento("small", null, `${fonte.sprint} · ${fonte.tipo}`));
      resumo.append(identificacao);
      resumo.append(criarElemento("span", "fonte-abrir", "Ver detalhes"));

      const corpo = criarElemento("dl", "metadados");
      [["Origem", fonte.origem], ["Caminho", fonte.caminho], ["Tipo", fonte.tipo]].forEach(([termo, valor]) => {
        corpo.append(criarElemento("dt", null, termo));
        corpo.append(criarElemento("dd", null, valor || "—"));
      });
      detalhes.append(resumo, corpo);
      container.append(detalhes);
    });
  }

  function renderizarResumo(dados) {
    elemento("#texto-resumo").textContent = dados.resposta;
    preencherEtiquetas(elemento("#sprints-consultadas-resumo"), dados.sprints_consultadas || []);
    renderizarFontes(dados.fontes || []);
    const resultado = elemento("#resultado-resumos");
    resultado.hidden = false;
    resultado.focus({ preventScroll: true });
    resultado.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function valorMetadado(valor) {
    if (valor === null || valor === undefined || valor === "") return "—";
    if (typeof valor === "object") return JSON.stringify(valor);
    return String(valor);
  }

  function renderizarFragmentos(fragmentos) {
    const container = elemento("#fragmentos-rag");
    container.replaceChildren();
    elemento("#quantidade-fragmentos").textContent = `${fragmentos.length} resultado${fragmentos.length === 1 ? "" : "s"}`;

    if (!fragmentos.length) {
      container.append(criarElemento("p", "estado-vazio", "Nenhum fragmento relevante foi encontrado."));
      return;
    }

    fragmentos.forEach((fragmento, indice) => {
      const artigo = criarElemento("article", "fragmento");
      const cabecalho = criarElemento("header", null);
      const posicao = criarElemento("div", "fragmento-posicao");
      posicao.append(criarElemento("span", null, `#${String(indice + 1).padStart(2, "0")}`));
      posicao.append(criarElemento("strong", null, fragmento.sprint));
      cabecalho.append(posicao);
      const score = Number(fragmento.score);
      cabecalho.append(criarElemento("span", "score", `score ${Number.isFinite(score) ? score.toFixed(4) : "—"}`));

      artigo.append(cabecalho);
      artigo.append(criarElemento("p", "fragmento-conteudo", fragmento.conteudo));

      const metadados = criarElemento("dl", "metadados compacto");
      const entradas = [["Origem", fragmento.origem], ...Object.entries(fragmento.metadados || {})];
      entradas.forEach(([termo, valor]) => {
        metadados.append(criarElemento("dt", null, termo));
        metadados.append(criarElemento("dd", null, valorMetadado(valor)));
      });
      artigo.append(metadados);
      container.append(artigo);
    });
  }

  function renderizarRag(dados) {
    preencherEtiquetas(elemento("#sprints-consultadas-rag"), dados.sprints_consultadas || []);
    renderizarFragmentos(dados.fragmentos || []);
    const resultado = elemento("#resultado-rag");
    resultado.hidden = false;
    resultado.focus({ preventScroll: true });
    resultado.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  elemento("#form-resumos").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    limparErro("#mensagem-resumos");
    elemento("#resultado-resumos").hidden = true;
    definirCarregamento(formulario, true);
    try {
      const pergunta = validarTexto(elemento("#pergunta-resumo"), "A pergunta");
      const sprints = separarSprints(elemento("#sprints-resumo").value);
      validarSprints(sprints, "sprints-resumo");
      renderizarResumo(await chamarApi("/v1/resumos", { pergunta, sprints }));
    } catch (erro) {
      mostrarErro("#mensagem-resumos", erro instanceof ErroInterface ? erro : new ErroInterface("Erro inesperado."));
    } finally {
      definirCarregamento(formulario, false);
    }
  });

  elemento("#form-rag").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    limparErro("#erro-rag");
    elemento("#resultado-rag").hidden = true;
    definirCarregamento(formulario, true);
    try {
      const mensagem = validarTexto(elemento("#mensagem-rag"), "A mensagem");
      const sprints = separarSprints(elemento("#sprints-rag").value);
      validarSprints(sprints, "sprints-rag");
      const rank = Number(elemento("#rank-rag").value);
      const tamanhoFragmento = Number(elemento("#tamanho-fragmento").value);
      if (!Number.isInteger(rank) || rank < 1 || rank > 10) {
        throw new ErroInterface("Rank deve ser um inteiro entre 1 e 10.", "rank-rag");
      }
      if (!Number.isInteger(tamanhoFragmento) || tamanhoFragmento < 1 || tamanhoFragmento > 3000) {
        throw new ErroInterface("Tamanho do fragmento deve ser um inteiro entre 1 e 3000.", "tamanho-fragmento");
      }
      renderizarRag(await chamarApi("/v1/rag", {
        sprints,
        mensagem,
        rank,
        tamanho_fragmento: tamanhoFragmento,
      }));
    } catch (erro) {
      mostrarErro("#erro-rag", erro instanceof ErroInterface ? erro : new ErroInterface("Erro inesperado."));
    } finally {
      definirCarregamento(formulario, false);
    }
  });

  elementos("[data-painel]").forEach((aba) => {
    aba.addEventListener("click", () => {
      elementos("[data-painel]").forEach((item) => {
        const selecionada = item === aba;
        item.classList.toggle("ativa", selecionada);
        item.setAttribute("aria-selected", String(selecionada));
        item.tabIndex = selecionada ? 0 : -1;
        elemento(`#${item.dataset.painel}`).hidden = !selecionada;
      });
    });
    aba.addEventListener("keydown", (evento) => {
      if (!["ArrowLeft", "ArrowRight"].includes(evento.key)) return;
      evento.preventDefault();
      const abas = elementos("[data-painel]");
      const deslocamento = evento.key === "ArrowRight" ? 1 : -1;
      abas[(abas.indexOf(aba) + deslocamento + abas.length) % abas.length].click();
      abas[(abas.indexOf(aba) + deslocamento + abas.length) % abas.length].focus();
    });
  });

  elementos("[data-pergunta]").forEach((botao) => {
    botao.addEventListener("click", () => {
      const campo = elemento("#pergunta-resumo");
      campo.value = botao.dataset.pergunta;
      campo.dispatchEvent(new Event("input"));
      campo.focus();
    });
  });

  [["#pergunta-resumo", "#contador-pergunta"], ["#mensagem-rag", "#contador-mensagem"]].forEach(([campoId, contadorId]) => {
    const campo = elemento(campoId);
    campo.addEventListener("input", () => {
      elemento(contadorId).textContent = `${campo.value.length} / 4000`;
    });
  });

  elemento("#rank-rag").addEventListener("input", (evento) => {
    const valor = Number(evento.target.value);
    elemento("#valor-rank").textContent = `${valor} fragmento${valor === 1 ? "" : "s"}`;
  });

  async function verificarSaude() {
    const estado = elemento("#estado-api");
    const texto = elemento("#estado-api-texto");
    try {
      const resposta = await fetch(`${apiBase}/health`, { headers: { Accept: "application/json" }, credentials: "omit" });
      if (!resposta.ok) throw new Error();
      estado.classList.add("disponivel");
      texto.textContent = "API disponível";
    } catch (_erro) {
      estado.classList.add("indisponivel");
      texto.textContent = "API indisponível";
    }
  }

  verificarSaude();
})();

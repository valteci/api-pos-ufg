"""Serviço de chunking para transformar sprints em fragmentos indexáveis."""

import hashlib
import json
from collections.abc import Iterable

from app.domain.rag import FragmentoSprint, ValorMetadado
from app.domain.sprint import JsonObjeto, Sprint, Subtarefa, Tarefa
from app.services.sprint_loader import (
    CHAVES_DESCRICAO,
    CHAVES_RESPONSAVEL,
    CHAVES_STATUS,
    CHAVES_SUBTAREFAS,
    CHAVES_TITULO,
)

CHAVES_CONHECIDAS = frozenset(
    CHAVES_TITULO
    + CHAVES_DESCRICAO
    + CHAVES_STATUS
    + CHAVES_RESPONSAVEL
    + CHAVES_SUBTAREFAS
)


class ServicoChunkingSprint:
    """Converte tarefas e subtarefas de sprints em fragmentos textuais."""

    def __init__(self, *, tamanho_maximo_fragmento: int = 3000) -> None:
        """Inicializa o serviço com limite de tamanho por fragmento.

        Args:
            tamanho_maximo_fragmento: Tamanho máximo de cada fragmento textual
                usado na indexação. Textos maiores são divididos sem misturar
                sprints diferentes.
        """
        if tamanho_maximo_fragmento < 1:
            raise ValueError("Tamanho máximo de fragmento deve ser positivo.")
        self.tamanho_maximo_fragmento = tamanho_maximo_fragmento

    def fragmentar_sprints(self, sprints: Iterable[Sprint]) -> list[FragmentoSprint]:
        """Gera fragmentos para várias sprints preservando a ordem recebida."""
        fragmentos: list[FragmentoSprint] = []
        for sprint in sprints:
            fragmentos.extend(self.fragmentar_sprint(sprint))
        return fragmentos

    def fragmentar_sprint(self, sprint: Sprint) -> list[FragmentoSprint]:
        """Gera fragmentos de tarefas e subtarefas de uma sprint.

        Cada fragmento recebe metadados com sprint, origem, tipo e caminho. O
        conteúdo de um fragmento nunca combina dados de mais de uma sprint.
        """
        fragmentos: list[FragmentoSprint] = []
        origem = sprint.arquivo_origem.name

        for tarefa in sprint.tarefas:
            fragmentos.extend(self._fragmentar_tarefa(sprint.identificador, origem, tarefa))
            for subtarefa in tarefa.subtarefas:
                fragmentos.extend(
                    self._fragmentar_subtarefa(
                        sprint=sprint.identificador,
                        origem=origem,
                        tarefa=tarefa,
                        subtarefa=subtarefa,
                    )
                )

        return fragmentos

    def _fragmentar_tarefa(
        self,
        sprint: str,
        origem: str,
        tarefa: Tarefa,
    ) -> list[FragmentoSprint]:
        """Cria fragmento textual para uma tarefa."""
        metadados = self._metadados_base(
            sprint=sprint,
            origem=origem,
            tipo="tarefa",
            caminho=tarefa.caminho,
            titulo_tarefa=tarefa.titulo,
            status=tarefa.status,
            responsavel=tarefa.responsavel,
        )
        linhas = [
            f"Sprint: {sprint}",
            f"Origem: {origem}",
            "Tipo: tarefa",
            f"Caminho: {tarefa.caminho}",
        ]
        linhas.extend(self._linhas_item("Tarefa", tarefa.titulo, tarefa.descricao))
        linhas.extend(self._linhas_status_responsavel(tarefa.status, tarefa.responsavel))
        linhas.extend(self._linhas_campos_adicionais(tarefa.dados))
        linhas.extend(self._linhas_subtarefas(tarefa.subtarefas))

        return self._criar_fragmentos(
            texto="\n".join(linhas),
            sprint=sprint,
            origem=origem,
            tipo="tarefa",
            caminho=tarefa.caminho,
            metadados=metadados,
        )

    def _fragmentar_subtarefa(
        self,
        *,
        sprint: str,
        origem: str,
        tarefa: Tarefa,
        subtarefa: Subtarefa,
    ) -> list[FragmentoSprint]:
        """Cria fragmento textual para uma subtarefa com contexto da tarefa."""
        metadados = self._metadados_base(
            sprint=sprint,
            origem=origem,
            tipo="subtarefa",
            caminho=subtarefa.caminho,
            titulo_tarefa=tarefa.titulo,
            titulo_subtarefa=subtarefa.titulo,
            status=subtarefa.status,
            responsavel=subtarefa.responsavel,
        )
        linhas = [
            f"Sprint: {sprint}",
            f"Origem: {origem}",
            "Tipo: subtarefa",
            f"Caminho: {subtarefa.caminho}",
        ]
        linhas.extend(self._linhas_item("Tarefa pai", tarefa.titulo, tarefa.descricao))
        linhas.extend(self._linhas_item("Subtarefa", subtarefa.titulo, subtarefa.descricao))
        linhas.extend(self._linhas_status_responsavel(subtarefa.status, subtarefa.responsavel))
        linhas.extend(self._linhas_campos_adicionais(subtarefa.dados))

        return self._criar_fragmentos(
            texto="\n".join(linhas),
            sprint=sprint,
            origem=origem,
            tipo="subtarefa",
            caminho=subtarefa.caminho,
            metadados=metadados,
        )

    def _criar_fragmentos(
        self,
        *,
        texto: str,
        sprint: str,
        origem: str,
        tipo: str,
        caminho: str,
        metadados: dict[str, ValorMetadado],
    ) -> list[FragmentoSprint]:
        """Divide texto grande em partes rastreáveis e determinísticas."""
        partes = self._dividir_texto_com_cabecalho(
            texto=texto,
            sprint=sprint,
            origem=origem,
            tipo=tipo,
            caminho=caminho,
        )
        total_partes = len(partes)
        fragmentos: list[FragmentoSprint] = []

        for indice, parte in enumerate(partes, start=1):
            metadados_parte = dict(metadados)
            metadados_parte["parte"] = indice
            metadados_parte["total_partes"] = total_partes
            fragmentos.append(
                FragmentoSprint(
                    id=self._gerar_id_fragmento(
                        sprint=sprint,
                        tipo=tipo,
                        caminho=caminho,
                        parte=indice,
                    ),
                    conteudo=parte,
                    sprint=sprint,
                    origem=origem,
                    tipo=tipo,
                    caminho=caminho,
                    metadados=metadados_parte,
                )
            )

        return fragmentos

    def _dividir_texto_com_cabecalho(
        self,
        *,
        texto: str,
        sprint: str,
        origem: str,
        tipo: str,
        caminho: str,
    ) -> list[str]:
        """Divide texto garantindo cabeçalho de origem em cada parte."""
        texto_normalizado = "\n".join(linha.rstrip() for linha in texto.splitlines()).strip()
        if len(texto_normalizado) <= self.tamanho_maximo_fragmento:
            return [texto_normalizado]

        linhas = texto_normalizado.splitlines()
        corpo = "\n".join(linhas[4:]).strip()
        cabecalho = (
            f"Sprint: {sprint}\n"
            f"Origem: {origem}\n"
            f"Tipo: {tipo}\n"
            f"Caminho: {caminho}\n"
        )
        limite_corpo = max(1, self.tamanho_maximo_fragmento - len(cabecalho) - 20)
        partes_corpo = self._dividir_texto(corpo, limite=limite_corpo)
        total_partes = len(partes_corpo)

        return [
            f"{cabecalho}Parte: {indice}/{total_partes}\n{parte}".strip()
            for indice, parte in enumerate(partes_corpo, start=1)
        ]

    def _dividir_texto(self, texto: str, *, limite: int | None = None) -> list[str]:
        """Divide texto respeitando o limite configurado por fragmento."""
        tamanho_limite = limite or self.tamanho_maximo_fragmento
        texto_normalizado = "\n".join(linha.rstrip() for linha in texto.splitlines()).strip()
        if len(texto_normalizado) <= tamanho_limite:
            return [texto_normalizado]

        partes: list[str] = []
        restante = texto_normalizado
        while len(restante) > tamanho_limite:
            corte = restante.rfind("\n", 0, tamanho_limite)
            if corte < max(1, tamanho_limite // 2):
                corte = restante.rfind(" ", 0, tamanho_limite)
            if corte < 1:
                corte = tamanho_limite

            partes.append(restante[:corte].strip())
            restante = restante[corte:].strip()

        if restante:
            partes.append(restante)

        return partes

    @staticmethod
    def _metadados_base(
        *,
        sprint: str,
        origem: str,
        tipo: str,
        caminho: str,
        titulo_tarefa: str | None = None,
        titulo_subtarefa: str | None = None,
        status: str | None = None,
        responsavel: str | None = None,
    ) -> dict[str, ValorMetadado]:
        """Monta metadados básicos aceitos pelo ChromaDB."""
        metadados: dict[str, ValorMetadado] = {
            "sprint": sprint,
            "origem": origem,
            "tipo": tipo,
            "caminho": caminho,
        }
        opcionais = {
            "titulo_tarefa": titulo_tarefa,
            "titulo_subtarefa": titulo_subtarefa,
            "status": status,
            "responsavel": responsavel,
        }
        for chave, valor in opcionais.items():
            if valor:
                metadados[chave] = valor

        return metadados

    @staticmethod
    def _linhas_item(prefixo: str, titulo: str | None, descricao: str | None) -> list[str]:
        """Cria linhas de título e descrição de uma tarefa ou subtarefa."""
        linhas: list[str] = []
        if titulo:
            linhas.append(f"{prefixo}: {titulo}")
        if descricao:
            linhas.append(f"Descrição: {descricao}")
        return linhas

    @staticmethod
    def _linhas_status_responsavel(status: str | None, responsavel: str | None) -> list[str]:
        """Cria linhas de status e responsável quando existirem."""
        linhas: list[str] = []
        if status:
            linhas.append(f"Status: {status}")
        if responsavel:
            linhas.append(f"Responsável: {responsavel}")
        return linhas

    @staticmethod
    def _linhas_subtarefas(subtarefas: list[Subtarefa]) -> list[str]:
        """Inclui resumo das subtarefas no fragmento da tarefa pai."""
        if not subtarefas:
            return ["Subtarefas: nenhuma"]

        linhas = ["Subtarefas:"]
        for subtarefa in subtarefas:
            detalhes = [subtarefa.titulo or f"subtarefa[{subtarefa.indice}]"]
            if subtarefa.status:
                detalhes.append(f"status={subtarefa.status}")
            if subtarefa.responsavel:
                detalhes.append(f"responsável={subtarefa.responsavel}")
            linhas.append(f"- {'; '.join(detalhes)}")
        return linhas

    @staticmethod
    def _linhas_campos_adicionais(dados: JsonObjeto) -> list[str]:
        """Serializa campos fora do conjunto normalizado em ordem estável."""
        adicionais = {
            chave: dados[chave]
            for chave in sorted(dados)
            if chave not in CHAVES_CONHECIDAS
        }
        if not adicionais:
            return []

        return [
            "Campos adicionais: "
            + json.dumps(
                adicionais,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
                separators=(",", ":"),
            )
        ]

    @staticmethod
    def _gerar_id_fragmento(*, sprint: str, tipo: str, caminho: str, parte: int) -> str:
        """Gera ID estável a partir da origem lógica do fragmento."""
        base = f"{sprint}|{tipo}|{caminho}|{parte}"
        digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]
        return f"{sprint}:{tipo}:{digest}"

"""Testes estruturais e de segurança da interface web."""

import base64
import os
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
DIRETORIO_FRONTEND = RAIZ_PROJETO / "frontend"


class ColetorEstruturaHtml(HTMLParser):
    """Coleta identificadores e elementos relevantes do documento HTML."""

    def __init__(self) -> None:
        """Inicializa as coleções usadas nas asserções."""
        super().__init__()
        self.identificadores: list[str] = []
        self.formularios: list[str] = []
        self.paineis: list[str] = []

    def handle_starttag(self, tag: str, atributos: list[tuple[str, str | None]]) -> None:
        """Registra atributos de elementos de abertura."""
        atributos_dict = dict(atributos)
        identificador = atributos_dict.get("id")
        if identificador:
            self.identificadores.append(identificador)
        if tag == "form" and identificador:
            self.formularios.append(identificador)
        if atributos_dict.get("role") == "tabpanel" and identificador:
            self.paineis.append(identificador)


class InterfaceWebTestCase(unittest.TestCase):
    """Cobre os contratos mínimos do frontend estático."""

    @classmethod
    def setUpClass(cls) -> None:
        """Carrega os arquivos da interface uma única vez."""
        cls.html = (DIRETORIO_FRONTEND / "index.html").read_text(encoding="utf-8")
        cls.javascript = (DIRETORIO_FRONTEND / "assets" / "app.js").read_text(
            encoding="utf-8"
        )
        cls.nginx = (DIRETORIO_FRONTEND / "nginx.conf").read_text(encoding="utf-8")
        caminho_compose = RAIZ_PROJETO / "docker-compose.yml"
        cls.compose = (
            caminho_compose.read_text(encoding="utf-8") if caminho_compose.is_file() else ""
        )

    def test_documento_possui_fluxos_de_resumo_e_rag(self) -> None:
        """Garante que as duas funcionalidades principais estejam acessíveis."""
        coletor = ColetorEstruturaHtml()
        coletor.feed(self.html)

        self.assertIn("form-resumos", coletor.formularios)
        self.assertIn("form-rag", coletor.formularios)
        self.assertCountEqual(coletor.paineis, ["painel-resumos", "painel-rag"])

    def test_documento_nao_possui_identificadores_duplicados(self) -> None:
        """Evita associações ambíguas de labels e seletores JavaScript."""
        coletor = ColetorEstruturaHtml()
        coletor.feed(self.html)

        self.assertEqual(len(coletor.identificadores), len(set(coletor.identificadores)))

    def test_frontend_chama_rotas_autenticadas_com_bearer_token(self) -> None:
        """Confirma integração com os contratos HTTP protegidos."""
        self.assertIn('chamarApi("/v1/resumos"', self.javascript)
        self.assertIn('chamarApi("/v1/rag"', self.javascript)
        self.assertIn('meta[name="api-auth-token"]', self.javascript)
        self.assertIn("window.atob(tokenCodificado)", self.javascript)
        self.assertIn("Authorization: `Bearer ${token}`", self.javascript)
        self.assertIn('fetch(`${apiBase}/health`', self.javascript)

    def test_token_vem_do_metadado_sem_campo_de_digitacao(self) -> None:
        """Evita solicitar manualmente uma credencial já configurada no ambiente."""
        self.assertIn(
            '<meta name="api-auth-token" content="__AUTH_TOKEN_BASE64__" />',
            self.html,
        )
        self.assertNotIn('id="token-api"', self.html)
        self.assertNotIn('id="alternar-token"', self.html)

    def test_identidade_visual_nao_cria_marca_para_a_interface(self) -> None:
        """Mantém a identificação da página estritamente descritiva."""
        self.assertNotIn("pulso da sprint", self.html.lower())
        self.assertNotIn("As respostas são limitadas aos arquivos JSON", self.html)
        self.assertIn("Consulta de sprints com IA", self.html)
        self.assertIn("Interface web da API de sprints", self.html)

    def test_token_nao_e_persistido_e_respostas_nao_usam_inner_html(self) -> None:
        """Reduz persistência de credenciais e execução de conteúdo não confiável."""
        conteudo = self.javascript.lower()

        self.assertNotIn("localstorage", conteudo)
        self.assertNotIn("sessionstorage", conteudo)
        self.assertNotIn("document.cookie", conteudo)
        self.assertNotIn("innerhtml", conteudo)
        self.assertIn("textcontent", conteudo)

    def test_script_injeta_token_codificado_sem_alterar_o_modelo(self) -> None:
        """Gera o HTML servido a partir do token de ambiente sem expor texto bruto."""
        script = DIRETORIO_FRONTEND / "preparar-index.sh"
        valor_ficticio = 'credencial-ficticia-para-teste-"<&'

        with tempfile.TemporaryDirectory() as diretorio_temporario:
            caminho_saida = Path(diretorio_temporario) / "index.html"
            ambiente = os.environ.copy()
            ambiente.update(
                {
                    "AUTH_TOKEN": valor_ficticio,
                    "CAMINHO_MODELO_FRONTEND": str(DIRETORIO_FRONTEND / "index.html"),
                    "CAMINHO_INDEX_FRONTEND": str(caminho_saida),
                }
            )
            subprocess.run(
                ["/bin/sh", str(script)],
                check=True,
                capture_output=True,
                text=True,
                env=ambiente,
            )
            html_gerado = caminho_saida.read_text(encoding="utf-8")

        esperado = base64.b64encode(valor_ficticio.encode("utf-8")).decode("ascii")
        self.assertIn(f'content="{esperado}"', html_gerado)
        self.assertNotIn("__AUTH_TOKEN_BASE64__", html_gerado)
        self.assertNotIn(valor_ficticio, html_gerado)
        self.assertIn("__AUTH_TOKEN_BASE64__", self.html)

    def test_nginx_aplica_cabecalhos_e_proxy_reverso(self) -> None:
        """Valida proteções do documento e comunicação interna com a API."""
        self.assertIn("Content-Security-Policy", self.nginx)
        self.assertIn("X-Content-Type-Options", self.nginx)
        self.assertIn("frame-ancestors 'none'", self.nginx)
        self.assertIn("resolver 127.0.0.11", self.nginx)
        self.assertIn("rewrite ^/api/(.*)$ /$1 break;", self.nginx)
        self.assertIn("proxy_pass http://$api_upstream;", self.nginx)

    @unittest.skipUnless(
        (RAIZ_PROJETO / "docker-compose.yml").is_file(),
        "docker-compose.yml não está montado no ambiente de testes.",
    )
    def test_compose_publica_frontend_com_token_vindo_do_ambiente(self) -> None:
        """Confirma a geração do HTML sem valor de credencial versionado."""
        self.assertIn("  frontend:", self.compose)
        self.assertIn('      - "3000:80"', self.compose)
        self.assertIn(
            "AUTH_TOKEN: ${AUTH_TOKEN:?AUTH_TOKEN deve ser configurado no .env}",
            self.compose,
        )
        self.assertIn(
            "./frontend/index.html:/opt/frontend/index.html.template:ro",
            self.compose,
        )
        self.assertIn(
            "./frontend/preparar-index.sh:/opt/frontend/preparar-index.sh:ro",
            self.compose,
        )
        self.assertNotIn(
            "./frontend/index.html:/usr/share/nginx/html/index.html:ro",
            self.compose,
        )
        self.assertNotIn("./frontend:/usr/share/nginx/html:ro", self.compose)
        self.assertIn("./frontend:/app/frontend:ro", self.compose)


if __name__ == "__main__":
    unittest.main()

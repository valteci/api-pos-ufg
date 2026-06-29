"""Middlewares de segurança da aplicação."""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class LimitePayloadMiddleware(BaseHTTPMiddleware):
    """Rejeita requisições com `Content-Length` acima do limite configurado."""

    def __init__(self, app: Callable[..., Awaitable[None]], max_payload_bytes: int) -> None:
        """Inicializa o middleware com o limite máximo em bytes."""
        super().__init__(app)
        self.max_payload_bytes = max_payload_bytes

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Aplica a validação antes de executar a rota."""
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                tamanho_payload = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Header Content-Length inválido."},
                )

            if tamanho_payload > self.max_payload_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "detail": (
                            "Payload excede o limite configurado de "
                            f"{self.max_payload_bytes} bytes."
                        )
                    },
                )

        return await call_next(request)


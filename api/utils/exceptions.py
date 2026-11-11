from typing import Any


class BaseAppException(Exception):
    """Base for every error the API raises on purpose."""

    def __init__(
        self,
        message: str,
        error_code: str,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.http_status = http_status
        self.details = details or {}


# ---- domain

class PromptNotFoundException(BaseAppException):
    def __init__(self, prompt_id: str | None = None) -> None:
        label = f"Prompt {prompt_id}" if prompt_id else "Prompt"
        super().__init__(f"{label} não encontrado", "PROMPT_NOT_FOUND", 404)


class VersionNotFoundException(BaseAppException):
    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__("Versão não encontrada neste prompt", "VERSION_NOT_FOUND", 404, details)


class PromptAlreadyDeletedException(BaseAppException):
    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            "O prompt está excluído; restaure-o antes de continuar",
            "PROMPT_ALREADY_DELETED",
            409,
            details,
        )


class PromptNotDeletedException(BaseAppException):
    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__("O prompt não está excluído", "PROMPT_NOT_DELETED", 409, details)


class InvalidVersionComparisonException(BaseAppException):
    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            "Não é possível comparar uma versão com ela mesma",
            "INVALID_VERSION_COMPARISON",
            422,
            details,
        )


class DomainRuleException(BaseAppException):
    """A business rule of the core rejected the operation."""

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__("A operação viola uma regra de negócio", "DOMAIN_RULE_VIOLATION", 409, details)


class InvalidRequestException(BaseAppException):
    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__("Requisição inválida", "INVALID_REQUEST", 422, details)


# ---- infrastructure

class NATSPublishException(BaseAppException):
    def __init__(self, reason: str = "") -> None:
        super().__init__(
            "Não foi possível enviar a mensagem ao serviço interno",
            "NATS_PUBLISH_FAILED",
            503,
            {"reason": reason} if reason else None,
        )


class CoreTimeoutException(BaseAppException):
    def __init__(self) -> None:
        super().__init__(
            "O serviço interno demorou demais para responder", "CORE_TIMEOUT", 504
        )


class CoreUnavailableException(BaseAppException):
    def __init__(self) -> None:
        super().__init__("O serviço interno está indisponível", "CORE_UNAVAILABLE", 503)


class CoreResponseException(BaseAppException):
    """The core answered with something we could not understand or with an internal error."""

    def __init__(self, reason: str = "") -> None:
        super().__init__(
            "O serviço interno retornou uma resposta inválida",
            "CORE_RESPONSE_ERROR",
            502,
            {"reason": reason} if reason else None,
        )

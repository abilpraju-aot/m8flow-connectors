"""Local connector interface for m8flow (no Spiff dependency)."""
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import TypedDict


class CommandResponseDict(TypedDict):
    """Response envelope for command body."""

    body: str
    mimetype: str
    http_status: int


class CommandErrorDict(TypedDict):
    """Error envelope for workflow logs."""

    error_code: str
    message: str


class ConnectorProxyResponseDict(TypedDict, total=False):
    """Full response returned by connector commands (m8flow proxy contract)."""

    command_response: CommandResponseDict
    error: CommandErrorDict | None
    command_response_version: int


class ConnectorCommand(ABC):
    """Base for m8flow connector commands. Uses Salesforce OAuth access token; obtain and store via m8flow/platform."""

    @abstractmethod
    def execute(self, config: Any, task_data: Any) -> ConnectorProxyResponseDict:
        """Execute the command. Returns dict with command_response, error, command_response_version."""
        ...

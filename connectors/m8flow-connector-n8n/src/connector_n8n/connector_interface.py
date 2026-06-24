"""Connector interface for m8flow; inherits from spiffworkflow_connector_command so the proxy recognizes commands."""
from abc import abstractmethod
from typing import Any
from typing import TypedDict

from spiffworkflow_connector_command.command_interface import ConnectorCommand as SpiffConnectorCommand


class CommandResponseDict(TypedDict, total=False):
    """Response envelope for command body."""

    body: str
    mimetype: str
    http_status: int
    parsed_body: Any


class CommandErrorDict(TypedDict):
    """Error envelope for workflow logs."""

    error_code: str
    message: str


class ConnectorProxyResponseDict(TypedDict, total=False):
    """Full response returned by connector commands (m8flow proxy contract)."""

    command_response: CommandResponseDict
    error: CommandErrorDict | None
    command_response_version: int


class ConnectorCommand(SpiffConnectorCommand):
    """Base for m8flow n8n connector commands.

    Public-API commands authenticate with an n8n API key (Settings > n8n API), sent as the
    ``X-N8N-API-KEY`` header. Webhook invocation uses the webhook's own auth (none / header / basic).
    Obtain and store credentials via m8flow/platform; they are never logged.
    """

    @abstractmethod
    def execute(self, config: Any, task_data: Any) -> ConnectorProxyResponseDict:
        """Execute the command. Returns dict with command_response, error, command_response_version."""
        ...

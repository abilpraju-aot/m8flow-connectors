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
    """Base for m8flow GitHub connector commands.

    Token must be a valid GitHub personal access token (PAT) or OAuth token; obtain and store it
    via m8flow/platform.
    """

    @abstractmethod
    def execute(self, config: Any, task_data: Any) -> ConnectorProxyResponseDict:
        """Execute the command. Returns dict with command_response, error, command_response_version."""
        ...

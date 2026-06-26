"""n8n connector commands for m8flow. Export for connector proxy discovery."""
from connector_n8n.commands.get_execution import GetExecution
from connector_n8n.commands.get_workflow import GetWorkflow
from connector_n8n.commands.list_executions import ListExecutions
from connector_n8n.commands.list_workflows import ListWorkflows
from connector_n8n.commands.trigger_workflow import TriggerWorkflow

__all__ = ["TriggerWorkflow", "ListWorkflows", "GetWorkflow", "ListExecutions", "GetExecution"]

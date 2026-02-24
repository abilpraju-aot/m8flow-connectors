"""Salesforce connector commands for m8flow. Export for connector proxy discovery."""
from connector_salesforce.commands.create_contact import CreateContact
from connector_salesforce.commands.create_lead import CreateLead
from connector_salesforce.commands.delete_contact import DeleteContact
from connector_salesforce.commands.delete_lead import DeleteLead
from connector_salesforce.commands.read_contact import ReadContact
from connector_salesforce.commands.read_lead import ReadLead
from connector_salesforce.commands.update_contact import UpdateContact
from connector_salesforce.commands.update_lead import UpdateLead

__all__ = [
    "CreateLead",
    "CreateContact",
    "ReadLead",
    "ReadContact",
    "UpdateLead",
    "UpdateContact",
    "DeleteLead",
    "DeleteContact",
]

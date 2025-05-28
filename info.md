Usage:

Create configuration:
bashpython script.py --create-config

Update config.json with your actual API tokens and mappings
Run the sync:
bashpython script.py <product_id>


Configuration Example:
The script will create a sample config that includes:

API credentials for both Aha! and Jira
Field mappings (assignee, status, priority)
Custom field mappings
Project settings

Field Mappings Handled:

Name → Summary: Direct mapping
Description: Enhanced with custom fields, portal info, and Aha! URL
Assignee: Maps email addresses between systems
Status: Configurable workflow status mapping
Priority: Based on idea score
Labels: From categories + "aha-import" tag
Custom Fields: Configurable mapping to Jira custom fields

The script includes proper error handling, logging, and will create a detailed sync report showing successful and failed transfers.
Would you like me to modify any specific aspects of the mapping or add additional features?RetryClaude does not have the ability to run the code it generates yet.N

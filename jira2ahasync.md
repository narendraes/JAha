
## Key Features

1. **Fetches Jira Issues**: Gets all issues from your specified project that contain Aha reference numbers in the custom field
2. **Retrieves Aha Data**: Uses the Aha API to get idea descriptions and attachments
3. **Updates Jira**: Synchronizes the description and attachments back to Jira
4. **Configurable**: Allows customization of additional fields to sync

## Setup Instructions

1. **Install Required Dependencies**:
```bash
pip install requests
```

2. **Set Environment Variables**:
```bash
export JIRA_URL="https://your-domain.atlassian.net"
export JIRA_USERNAME="your-email@company.com"
export JIRA_TOKEN="your-jira-api-token"
export JIRA_PROJECT_KEY="YOUR_PROJECT_KEY"
export JIRA_AHA_FIELD="customfield_12345"  # Replace with actual field ID
export AHA_DOMAIN="yourcompany.aha.io"
export AHA_API_KEY="your-aha-api-key"
export UPDATE_DESCRIPTION="true"
export UPDATE_ATTACHMENTS="true"
export DRY_RUN="false"  # Set to "true" for testing
```

3. **Run the Script**:
```bash
python jira_aha_sync.py
```

## Customization Options

### Additional Field Mappings
To sync other fields between Aha and Jira, modify the `additional_field_mappings` in the Config class:

```python
additional_field_mappings = {
    "status": "customfield_10001",
    "priority": "customfield_10002",
    "custom_aha_field": "customfield_10003"
}
```

### Custom Processing
You can extend the script by:
- Adding custom field transformations in `sync_issue_with_aha()`
- Implementing different description formats
- Adding filtering logic for specific issue types
- Adding error handling and retry mechanisms

## Safety Features

- **Dry Run Mode**: Test the script without making changes by setting `DRY_RUN=true`
- **Comprehensive Logging**: Detailed logs for monitoring and debugging
- **Error Handling**: Graceful handling of API errors and network issues

## Authentication Requirements

- **Jira**: Requires username and API token (create at: Account Settings → Security → API tokens)
- **Aha**: Requires API key (create at: Account Settings → API → Personal API Key)

The script is designed to be run periodically (e.g., via cron job) to keep Jira and Aha synchronized. Make sure to test with `DRY_RUN=true` first to verify the configuration works correctly.

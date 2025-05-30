
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

I'll update the script to add a test run command that allows you to process only 1-5 issues for testing purposes.Perfect! I've updated the script to include comprehensive test run capabilities. Here are the new testing features:

## Test Run Commands

### 1. Basic Test Run (processes 3 issues by default)
```bash
python jira_aha_sync.py --test
```

### 2. Test Run with Custom Limit (1-5 issues)
```bash
python jira_aha_sync.py --test --test-limit 2    # Process only 2 issues
python jira_aha_sync.py --test --test-limit 5    # Process up to 5 issues
```

### 3. Dry Run Test (no actual changes made)
```bash
python jira_aha_sync.py --test --dry-run         # Test mode + no changes
python jira_aha_sync.py --test --test-limit 1 --dry-run  # 1 issue, no changes
```

### 4. List Issues Only (see what would be processed)
```bash
python jira_aha_sync.py --list-issues            # Show all matching issues
python jira_aha_sync.py --test --list-issues     # Show limited test issues
```

## Environment Variable Options

You can also control test mode via environment variables:

```bash
export TEST_RUN="true"
export TEST_ISSUE_LIMIT="2"
python jira_aha_sync.py
```

## Recommended Testing Workflow

1. **First, list the issues to see what will be processed:**
   ```bash
   python jira_aha_sync.py --list-issues
   ```

2. **Run a safe test with 1 issue and dry-run:**
   ```bash
   python jira_aha_sync.py --test --test-limit 1 --dry-run
   ```

3. **If everything looks good, test with actual changes on 1 issue:**
   ```bash
   python jira_aha_sync.py --test --test-limit 1
   ```

4. **Gradually increase the test limit:**
   ```bash
   python jira_aha_sync.py --test --test-limit 3
   ```

5. **Finally, run the full sync:**
   ```bash
   python jira_aha_sync.py
   ```

## New Features Added

- **Command line argument parsing** for flexible testing options
- **Test mode limiting** to process only 1-5 issues
- **Issue listing** to preview what will be processed
- **Combined modes** (test + dry-run for maximum safety)
- **Clear logging** to show when test mode is active

This approach allows you to safely test the integration with a small number of issues before running it on your entire project!

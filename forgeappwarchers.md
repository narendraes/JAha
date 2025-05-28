## Technical Implementation Document: Forge App to Add Project Role or Group as Watchers on Issue Creation

### Overview

This document describes the design and implementation steps for a Forge app that automatically adds all users from a selected group or project role as watchers to issues created in a specific Jira Cloud project. The app will allow a Jira admin to configure which group/role to use per project. On issue creation, all current members of the chosen group/role will be added as watchers to the new issue.

---

## 1. Requirements

- **Jira Cloud instance with Forge enabled**
- **Admin permissions** to install/manage Forge apps and configure project permissions
- **Target group or project role** (e.g., "QA-Team" or "Developers") exists in Jira
- **Users to be added as watchers have "Browse Project" and "Manage Watcher List" permissions** on the project[5][12]

---

## 2. High-Level Architecture

- **Forge App**: Listens to the `issue_created` event for the selected project.
- **Configuration UI**: Allows admin to select the group or role for each project.
- **On Issue Creation**:
  - Fetch all users in the configured group/role.
  - For each user, call the Jira REST API to add them as a watcher to the new issue.

---

## 3. Forge App Implementation Steps

### 3.1. App Manifest (`manifest.yml`)

Define the app modules, permissions, and event subscriptions.

```yaml
app:
  id: <your-app-id>
  name: project-role-watchers

modules:
  jira:issueCreated:
    - key: add-watchers-on-create
      function: main
      events:
        - created

  jira:adminPage:
    - key: config-page
      function: config
      title: Configure Default Watcher Group/Role

permissions:
  scopes:
    - read:jira-user
    - read:jira-work
    - write:jira-work
    - read:group:jira
    - read:project:jira
    - manage:jira-configuration
```


### 3.2. Configuration UI

- Use a Forge custom admin page to let the admin choose the group or project role for the project.
- Store the configuration (project-key → group/role) using Forge Storage API.

### 3.3. Event Handler (Backend Function)

#### a. On `issue_created` event:
- Get the project key from the event payload.
- Retrieve the configured group/role for the project from storage.
- Fetch all users in the group or role (see API endpoints below).
- For each user, add them as a watcher to the issue.

---

## 4. Jira REST API Endpoints

### 4.1. Get Group Members

```http
GET /rest/api/3/group/member?groupname=<group-name>
```
- Returns paginated list of users in the group.
- Requires `read:jira-user` and `read:group:jira` scopes[3][9].

### 4.2. Get Users in a Project Role

```http
GET /rest/api/3/project/{projectKey}/role/{roleId}
```
- Returns users assigned to a specific role in a project.
- Requires `read:jira-user` and `read:project:jira` scopes.

### 4.3. Add Watcher to Issue

```http
POST /rest/api/3/issue/{issueIdOrKey}/watchers
Content-Type: application/json
Body: "<accountId>"
```
- Add a user as watcher by their accountId.
- Requires `write:jira-work` and `write:issue.watcher:jira` scopes[8].

---

## 5. Sample Forge Handler (Pseudo-code/JS)

```javascript
import { storage, events, requestJira } from '@forge/api';

export async function run(event, context) {
  const { issue, project } = event;
  const projectKey = project.key;
  // Retrieve configured group or role for this project
  const config = await storage.get(projectKey);
  let users = [];

  if (config.type === 'group') {
    // Fetch group members
    let startAt = 0, isLast = false;
    while (!isLast) {
      const res = await requestJira(`/rest/api/3/group/member?groupname=${config.value}&startAt=${startAt}`);
      const data = await res.json();
      users.push(...data.values);
      isLast = data.isLast;
      startAt = data.startAt + data.maxResults;
    }
  } else if (config.type === 'role') {
    // Fetch users in project role
    const res = await requestJira(`/rest/api/3/project/${projectKey}/role/${config.value}`);
    const data = await res.json();
    users = data.actors.filter(actor => actor.type === 'atlassian-user-account');
  }

  // Add each user as watcher
  for (const user of users) {
    await requestJira(`/rest/api/3/issue/${issue.key}/watchers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(user.accountId)
    });
  }
}
```


---

## 6. Enablement & Installation Instructions

1. **Install Forge CLI**:  
   ```
   npm install -g @forge/cli
   ```

2. **Create the app**:  
   ```
   forge create
   ```

3. **Configure manifest.yml** as above.

4. **Develop the configuration and event handler functions**.

5. **Deploy the app**:  
   ```
   forge deploy
   ```

6. **Install the app on your Jira Cloud site**:  
   ```
   forge install
   ```

7. **Configure the app**:  
   - Go to the admin page provided by the app.
   - Select the project and choose the group or role whose members should be added as watchers.

8. **Test**:  
   - Create an issue in the configured project.
   - Confirm that all members of the selected group/role are added as watchers.

---

## 7. Permissions Checklist

- **App scopes**: `read:jira-user`, `read:jira-work`, `write:jira-work`, `read:group:jira`, `read:project:jira`, `manage:jira-configuration`[7][10].
- **Jira project permissions**: Users to be added as watchers must have "Browse Project" and "Manage Watcher List" permissions[5][12].
- **Jira global setting**: "Allow users to watch issues" must be enabled[6][8].

---

## 8. Notes & Limitations

- **Group/role membership is checked dynamically** at issue creation, so changes in membership are always respected.
- **API rate limits**: Adding many watchers in large groups may hit API limits.
- **Only users with proper permissions** will be successfully added as watchers; others will be skipped.

---

## 9. References

- [Jira REST API: Group Members][3][9]
- [Jira REST API: Project Roles][4]
- [Jira REST API: Add Watcher][8]
- [Forge Manifest Documentation][7]
- [Forge Permissions][10]
- [Jira Cloud: Allow users to watch issues][6]

---

**This Forge app provides a robust, maintainable, and admin-configurable solution to automatically add all users from a selected group or project role as watchers on issue creation, scoped to the project(s) of your choosing.**

Sources
[1] Add Watchers Automatically to Jira Issues on Creation https://support.atlassian.com/jira/kb/automatically-add-watchers-to-the-issues-on-creation/
[2] Automatically Add Watchers to Issues on Creation - Atlassian Support https://support.atlassian.com/jira/kb/automatically-add-watchers-to-issues-on-creation/
[3] The Jira Cloud platform REST API - Atlassian Developer https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-groups/
[4] Assign users to project roles in Jira using REST API https://support.atlassian.com/jira/kb/adding-a-user-to-project-roles-via-jira-rest-api/
[5] Permission to add watchers to Jira Ticket - Atlassian Community https://community.atlassian.com/forums/Jira-questions/Permission-to-add-watchers-to-Jira-Ticket/qaq-p/2330588
[6] Configuring Jira application options - Atlassian Documentation https://confluence.atlassian.com/adminjiraserver/configuring-jira-application-options-938847824.html
[7] Manifest - Forge - Atlassian Developer https://developer.atlassian.com/platform/forge/manifest/
[8] The Jira Cloud platform REST API - Atlassian Developer https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issue-watchers/
[9] Is there a normal way to get all group members via REST API in Jira ... https://community.developer.atlassian.com/t/is-there-a-normal-way-to-get-all-group-members-via-rest-api-in-jira-cloud/53296
[10] Forge - Permissions - Atlassian https://go.atlassian.com/forge-permissions
[11] Customizing Jira with Forge | New 2024 | Atlassian Developer Training https://www.youtube.com/watch?v=yFW8lZQOhaM
[12] JIRA Cloud - Users are able to add watchers but th... https://community.atlassian.com/forums/Jira-questions/JIRA-Cloud-Users-are-able-to-add-watchers-but-then-they-are/qaq-p/1607212
[13] How to use Class 'IssueWatcherAddedEvent' in Forge App (Custom ... https://community.developer.atlassian.com/t/how-to-use-class-issuewatcheraddedevent-in-forge-app-custom-events-webhooks-web-triggers/55365
[14] Is there any way to add Watchers on issue creation in Jira version ... https://community.atlassian.com/forums/Jira-questions/Is-there-any-way-to-add-Watchers-on-issue-creation-in-Jira/qaq-p/1218744
[15] How add group in watchers group jira? - Atlassian Community https://community.atlassian.com/forums/Jira-questions/How-add-group-in-watchers-group-jira/qaq-p/2048547
[16] Jira Cloud Rest API Create Issue - Atlassian Developer https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/
[17] Solved: Can we add a group of users as watchers or it need... https://community.atlassian.com/forums/Confluence-questions/Can-we-add-a-group-of-users-as-watchers-or-it-needs-to-be/qaq-p/2616570
[18] The Jira Cloud platform REST API - Atlassian Developer https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-group-and-user-picker/
[19] Jira REST API examples - Atlassian Developer https://developer.atlassian.com/server/jira/platform/jira-rest-api-examples/
[20] Jira scopes for OAuth 2.0 (3LO) and Forge apps - Atlassian Developer https://developer.atlassian.com/cloud/jira/platform/scopes-for-oauth-2-3LO-and-forge-apps/
[21] Jira User cannot add Watchers to an issue - Atlassian Support https://support.atlassian.com/jira/kb/jira-user-cannot-add-watchers-to-an-issue/
[22] Watchers self url not working within Forge https://community.developer.atlassian.com/t/watchers-self-url-not-working-within-forge/53821
[23] Get users from group REST api - Response nextPage https://community.atlassian.com/forums/Jira-questions/Get-users-from-group-REST-api-Response-nextPage-URL-missing-the/qaq-p/1926614
[24] Trying to pull a list of group members from REST API - jira - Reddit https://www.reddit.com/r/jira/comments/lhmsyj/trying_to_pull_a_list_of_group_members_from_rest/
[25] How to Add Issue Watchers in Jira Through REST API - YouTube https://www.youtube.com/watch?v=LQRyaM_2v-Y
[26] Get details of a user groups using Jira REST API - Forge https://community.developer.atlassian.com/t/get-details-of-a-user-groups-using-jira-rest-api/79177
[27] Jira API - Add Watcher - PowerShell Help https://forums.powershell.org/t/jira-api-add-watcher/23770
[28] Solved: permission for watchers - Atlassian Community https://community.atlassian.com/forums/Jira-questions/permission-for-watchers/qaq-p/2264322
[29] Watching Issues in Jira: The Comprehensive Playbook - Idalko https://idalko.com/jira-watch-issues/

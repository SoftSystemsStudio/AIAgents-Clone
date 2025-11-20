# Gmail Cleanup Agent Setup Guide

## 📧 Overview

The Gmail Cleanup Agent is an AI assistant that can analyze and clean your Gmail inbox using natural language commands. It can:

- **Analyze** your inbox to identify cleanup opportunities
- **Delete** emails from specific senders (promotions, notifications, spam)
- **Archive** old emails to keep them but clear your inbox
- **Search** and bulk-delete specific types of emails
- **Organize** your email automatically

## 🔐 Setup Instructions

### Step 1: Enable Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Gmail API**:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click "Enable"

### Step 2: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: **Desktop app**
4. Give it a name (e.g., "Gmail Cleanup Agent")
5. Click "Create"
6. Download the credentials file

### Step 3: Install Credentials

1. Rename the downloaded file to `credentials.json`
2. Place it in the project root directory:
   ```
   /workspaces/AIAgents/credentials.json
   ```

### Step 4: Install Dependencies

```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### Step 5: Run the Agent

```bash
cd /workspaces/AIAgents
export PYTHONPATH=/workspaces/AIAgents:$PYTHONPATH
python examples/gmail_cleanup_agent.py
```

On first run:
- A browser window will open
- Sign in to your Google account
- Grant the app permission to access your Gmail
- Authentication token will be saved for future use

## 💡 Usage Examples

### Interactive Mode

```bash
python examples/gmail_cleanup_agent.py
```

Then use natural language commands:

```
You: Show me my unread emails
You: Delete all emails from notifications@linkedin.com
You: Clean up emails older than 90 days
You: Archive promotional emails from the last month
You: Help me organize my inbox
```

### What the Agent Can Do

**📊 Analyze:**
- List unread emails
- Identify top senders
- Find old emails
- Detect promotional emails

**🗑️ Delete:**
- By sender: `"Delete all emails from @promotions.com"`
- By age: `"Delete emails older than 6 months"`
- By search: `"Delete all newsletter emails"`

**📦 Archive:**
- Keep emails but clear inbox
- `"Archive all emails from last year"`

**🔍 Search:**
- Find specific emails
- `"Show me emails from my boss this week"`

## 🛡️ Safety Features

1. **Confirmation required** for bulk deletions
2. **Limits** on batch operations (100-200 emails max)
3. **List-first approach** - always shows what will be deleted
4. **Archive option** - safer than permanent deletion
5. **Undo support** - deleted emails go to trash first (recoverable for 30 days)

## 🎯 Common Use Cases

### 1. Cleanup Promotional Emails

```
You: Show me promotional emails from the last 3 months
Agent: [Lists emails]
You: Delete them all
Agent: [Deletes 156 promotional emails]
```

### 2. Unsubscribe from Newsletters

```
You: Find all newsletter subscriptions
Agent: [Lists newsletters]
You: Delete all from "DailyDeals Newsletter"
Agent: [Deletes all emails from that sender]
```

### 3. Archive Old Emails

```
You: Archive everything older than 1 year
Agent: [Archives 1,245 old emails - inbox clear, emails saved]
```

### 4. Clean Specific Sender

```
You: Delete all LinkedIn notification emails
Agent: [Searches for "notifications@linkedin.com"]
Agent: Found 87 emails. Delete all?
You: Yes
Agent: [Deletes all 87 emails]
```

## ⚙️ Configuration

Edit the agent's behavior in `examples/gmail_cleanup_agent.py`:

```python
# Adjust safety limits
max_delete=100      # Maximum emails per deletion
max_archive=200     # Maximum emails per archive

# Change model
model_name="gpt-4o"         # More capable
model_name="gpt-4o-mini"    # Faster, cheaper
```

## 🔒 Security & Privacy

- **OAuth 2.0** - Secure authentication, no password needed
- **Local storage** - Credentials stored on your machine only
- **Revocable access** - Can revoke at any time in Google Account settings
- **Read-only option** - Can limit to read-only if you want to analyze only

To revoke access:
1. Go to https://myaccount.google.com/permissions
2. Find "Gmail Cleanup Agent"
3. Click "Remove Access"

## 🐛 Troubleshooting

**Problem: "credentials.json not found"**
- Make sure you downloaded OAuth credentials (not API key)
- Place in project root, named exactly `credentials.json`

**Problem: "Access blocked" during OAuth**
- App needs to be verified for production use
- Or add your email to test users in Google Cloud Console

**Problem: "Quota exceeded"**
- Gmail API has daily quotas
- Wait 24 hours or request quota increase

**Problem: Token expired**
- Delete `token.pickle` and re-authenticate

## 📈 Advanced Features

### Custom Queries

The agent uses Gmail search syntax:

```python
"is:unread"                    # Unread emails
"from:sender@example.com"      # Specific sender
"older_than:30d"               # Older than 30 days
"subject:invoice"              # Subject contains "invoice"
"has:attachment"               # Has attachments
"larger:5M"                    # Larger than 5MB
```

### Batch Operations

For large cleanups, work in batches:

```
You: How many unread emails do I have?
Agent: You have 2,456 unread emails
You: Delete 100 oldest unread emails
Agent: [Deletes batch 1]
You: Delete 100 more
Agent: [Deletes batch 2]
```

## 🎨 Example Session

```
📧 GMAIL CLEANUP ASSISTANT
==================================================

You: Analyze my inbox
🤖 Agent: Analyzing your inbox...
    • Total emails: 12,456
    • Unread: 387
    • Promotional: 2,103
    • Top sender: notifications@linkedin.com (156 emails)
    • Oldest email: 3 years ago

You: Delete all LinkedIn notifications
🤖 Agent: Found 156 emails from notifications@linkedin.com
    Delete all? This action will move them to trash (recoverable for 30 days).
    
You: Yes, delete them
🤖 Agent: ✅ Successfully deleted 156 emails from LinkedIn notifications
    Your inbox now has 12,300 emails.

You: Now delete promotions older than 6 months
🤖 Agent: Searching for promotional emails older than 180 days...
    Found 1,847 emails. Delete all?

You: Yes
🤖 Agent: ✅ Deleted 1,847 promotional emails
    Your inbox now has 10,453 emails.
    
You: Perfect! Archive everything older than 1 year
🤖 Agent: ✅ Archived 3,892 emails
    Your inbox now has 6,561 emails.
    Archived emails are still searchable and accessible.
```

## 🚀 Next Steps

1. **Schedule regular cleanups** - Run weekly to keep inbox clean
2. **Create cleanup rules** - Define your own cleanup patterns
3. **Add more tools** - Label management, smart replies, etc.
4. **Multi-account support** - Manage multiple Gmail accounts

## 📚 Resources

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Gmail Search Operators](https://support.google.com/mail/answer/7190)
- [OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)

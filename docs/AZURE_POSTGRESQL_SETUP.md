# Azure PostgreSQL Setup Guide

Get your own Azure PostgreSQL database running in **5 minutes**!

## Quick Start

### Step 1: Create Azure PostgreSQL (3-5 minutes)

1. **Sign in to Azure Portal**

   - Go to [portal.azure.com](https://portal.azure.com)
   - Sign in with your Microsoft account

2. **Create a new PostgreSQL database**

   - Click "Create a resource" (+ icon)
   - Search for "Azure Database for PostgreSQL"
   - Select "Flexible Server" (newest, most cost-effective option)
   - Click "Create"

3. **Configure basic settings**

   ```
   Subscription:        [Your subscription]
   Resource group:      Create new → "knowledge-os-rg"
   Server name:         [your-unique-name]
   Region:              [Your closest region]
   PostgreSQL version:  15 or higher
   Workload type:       Development (cheapest - ~$12/month)
   Compute + storage:   Burstable B1ms
   ```

4. **Set administrator account**

   ```
   Admin username:      pgadmin
   Password:           [Strong password - save this!]
   ```

5. **Configure networking**

   - Public access: "Allow public access from any Azure service"
   - After creation, go to "Networking" and add your current IP:
     - Click "+ Add current client IP address"
     - Click "Save"

6. **Create the database**
   - After server is created, go to "Databases" in the left menu
   - Click "+ Add"
   - Database name: `knowledge_os`
   - Click "Save"

### Step 2: Get Your Connection String

In Azure Portal, navigate to your PostgreSQL server and find:

- **Server name**: `your-server.postgres.database.azure.com`
- **Admin username**: `pgadmin`
- **Database**: `knowledge_os`

Your connection string format:

```
postgresql://pgadmin:YourPassword@your-server.postgres.database.azure.com:5432/knowledge_os?sslmode=require
```

### Step 3: Set Up Your Database (30 seconds)

1. **Clone this repository** (if you haven't already)

   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. **Configure your connection**

   ```bash
   cp .env.example .env
   # Edit .env and paste your connection string
   ```

3. **Run the setup**
   ```bash
   make setup-db
   ```

That's it! Your database is ready to use. 🎉

## Cost Optimization Tips

### For Personal/Development Use

- **Burstable B1ms tier**: ~$12-15/month
- **Stop when not using**: Save money by stopping the server
  ```
  Azure Portal → Your Server → Overview → Stop
  ```

## Troubleshooting

| Problem                | Solution                                                   |
| ---------------------- | ---------------------------------------------------------- |
| Connection refused     | Add your IP in Azure Portal → Networking → Firewall rules  |
| Authentication failed  | Ensure username is just `pgadmin` (not `pgadmin@server`)   |
| SSL error              | Add `?sslmode=require` to connection string                |
| Database doesn't exist | Create `knowledge_os` database in Azure Portal → Databases |

## Available Commands

After setup, you can use these commands:

```bash
make setup-db      # Initial database setup
make validate-db   # Check if everything is configured correctly
make reset-db      # Start fresh (WARNING: deletes all data!)
```

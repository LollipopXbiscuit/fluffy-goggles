# Deploying VexaSwitch Store Bot to Render

This guide will help you deploy your Telegram bot to Render for 24/7 operation using webhooks and automatic message counting to keep it alive.

## Prerequisites

1. A Telegram bot token from [@BotFather](https://t.me/botfather)
2. A MongoDB database (free tier from [MongoDB Atlas](https://www.mongodb.com/cloud/atlas))
3. A GitHub account (to push your code)
4. A Render account (free at [render.com](https://render.com))

## Features Implemented

✅ **Webhook Mode** - Uses Telegram webhooks instead of polling (required for Render)  
✅ **Message Counting System** - Tracks bot activity to demonstrate uptime  
✅ **Health Check Endpoint** - `/` endpoint for Render to monitor bot status  
✅ **Statistics Endpoint** - `/stats` to view message count  
✅ **Auto-restart** - Gunicorn worker management for stability  
✅ **Environment Variables** - Secure secrets management  

## Step 1: Prepare Your MongoDB Database

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free cluster (M0 Sandbox)
3. Create a database user with password
4. Whitelist all IP addresses (0.0.0.0/0) for Render access
5. Get your connection string (looks like: `mongodb+srv://username:password@cluster.mongodb.net/`)

## Step 2: Push Your Code to GitHub

```bash
# Initialize git if not already done
git init

# Add all files
git add .

# Commit
git commit -m "Prepare bot for Render deployment"

# Create a new repository on GitHub and push
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

## Step 3: Deploy to Render

### Option A: Using the Render Dashboard (Recommended)

1. **Login to Render**
   - Go to [dashboard.render.com](https://dashboard.render.com)
   - Sign in or create account

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository with your bot code

3. **Configure the Service**
   - **Name**: `vexaswitch-bot` (or your preferred name)
   - **Region**: Choose closest to you (e.g., Oregon)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120`

4. **Set Environment Variables**
   Click "Advanced" → "Add Environment Variable" and add:

   | Key | Value | Example |
   |-----|-------|---------|
   | `BOT_TOKEN` | Your bot token from BotFather | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` |
   | `MONGODB_URL` | Your MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
   | `WEBHOOK_URL` | (leave empty for now, add after deploy) | `https://your-app.onrender.com/webhook` |
   | `OWNER_ID` | Your Telegram user ID | `123456789` |
   | `PORT` | `8080` | `8080` |

5. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (3-5 minutes)
   - Copy your app URL (e.g., `https://vexaswitch-bot.onrender.com`)

6. **Update WEBHOOK_URL**
   - Go to Environment variables
   - Add/Update `WEBHOOK_URL` with: `https://YOUR-APP-NAME.onrender.com/webhook`
   - Save and wait for automatic redeploy

### Option B: Using render.yaml (Blueprint)

1. The `render.yaml` file is already configured
2. In Render dashboard, click "New +" → "Blueprint"
3. Connect your repository
4. Render will auto-detect the `render.yaml` file
5. Set the environment variables as described above
6. Click "Apply" to deploy

## Step 4: Verify Deployment

### Check Health Status
Visit your app URL: `https://your-app.onrender.com/`

You should see:
```json
{
  "status": "ok",
  "bot": "VexaSwitch Store Bot",
  "message_count": 0,
  "timestamp": "2024-XX-XXTXX:XX:XX"
}
```

### Check Stats
Visit: `https://your-app.onrender.com/stats`

### Test the Bot
1. Open Telegram
2. Search for your bot
3. Send `/start` command
4. Bot should respond immediately
5. Check `/stats` endpoint - message count should increase

## Step 5: Keep Bot Alive 24/7 (FREE)

Render's free tier spins down after 15 minutes of inactivity. To keep your bot running:

### Method 1: UptimeRobot (Recommended)

1. Go to [uptimerobot.com](https://uptimerobot.com)
2. Sign up for free account
3. Add New Monitor:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: `VexaSwitch Bot`
   - **URL**: `https://your-app.onrender.com/`
   - **Monitoring Interval**: 5 minutes
4. Save and activate

### Method 2: Cron-job.org

1. Go to [cron-job.org](https://cron-job.org)
2. Create free account
3. Create new cronjob:
   - **URL**: `https://your-app.onrender.com/`
   - **Interval**: Every 5 minutes
4. Enable the job

### Method 3: hosting.aifordiscord.xyz (No Account Needed)

1. Go to [hosting.aifordiscord.xyz](https://hosting.aifordiscord.xyz)
2. Enter your URL: `https://your-app.onrender.com/`
3. Submit - no account required!

## Monitoring & Troubleshooting

### View Logs
- In Render dashboard → Your service → Logs tab
- Check for errors or webhook setup messages

### Common Issues

**Bot not responding:**
- Check if `WEBHOOK_URL` is set correctly
- Verify MongoDB connection string is valid
- Check Render logs for errors
- Ensure bot token is correct

**Webhook fails to set:**
- Make sure `WEBHOOK_URL` includes `/webhook` at the end
- Verify the URL uses `https://` not `http://`
- Check if Render service is running

**Database errors:**
- Verify MongoDB Atlas allows connections from anywhere (0.0.0.0/0)
- Check if database user has read/write permissions
- Confirm connection string includes database name

### Check Message Count
The message counting system proves your bot is active:
```bash
curl https://your-app.onrender.com/stats
```

Every message processed increments the counter, helping keep the bot "awake" and providing activity metrics.

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `BOT_TOKEN` | ✅ Yes | Telegram bot token from @BotFather | `1234567890:ABC...` |
| `MONGODB_URL` | ✅ Yes | MongoDB connection string | `mongodb+srv://...` |
| `WEBHOOK_URL` | ✅ Yes | Your Render app URL + /webhook | `https://app.onrender.com/webhook` |
| `OWNER_ID` | ⚠️ Optional | Your Telegram user ID (for admin commands) | `123456789` |
| `PORT` | ⚠️ Optional | Port number (Render sets this automatically) | `8080` |

## Scaling & Upgrades

### Free Tier
- ✅ 750 hours/month (enough for 24/7 with 1 app)
- ✅ Automatic HTTPS
- ⚠️ Sleeps after 15 min inactivity (use UptimeRobot)
- ⚠️ 512 MB RAM
- ⚠️ Shared CPU

### Paid Tier ($7/month)
- ✅ Always on (no sleep)
- ✅ 512 MB - 2 GB RAM
- ✅ Dedicated CPU
- ✅ Faster performance
- ✅ No cold starts

## Commands for Your Bot

- `/start` - Start the bot
- `/help` - Show help message
- `/vault` - View balance
- `/dice` - Earn extra currency (4x/day)
- `/daily` - Claim daily reward
- `/buy` - Purchase with Telegram Stars
- `/transfer` - Transfer currency
- `/shop` - Browse marketplace
- `/market` - P2P marketplace
- `/history` - Transaction history
- `/cards` - View card collection
- `/terms` - Terms of Service
- `/support` - Get support

### Admin Commands (OWNER_ID only)
- `/grant` - Grant currency to users
- `/remove` - Remove currency from users
- `/refreshshop` - Refresh daily shop

## Support

For issues or questions:
- Check Render logs first
- Verify all environment variables
- Test MongoDB connection
- Review webhook configuration
- Contact support via your bot's `/support` command

## Security Best Practices

✅ Never commit `.env` file to GitHub  
✅ Use environment variables for all secrets  
✅ Keep bot token private  
✅ Regularly rotate MongoDB passwords  
✅ Monitor logs for suspicious activity  
✅ Use MongoDB Atlas IP whitelist when possible  

## Additional Resources

- [Render Documentation](https://render.com/docs)
- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [MongoDB Atlas Documentation](https://docs.atlas.mongodb.com/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

**Congratulations! Your bot is now running 24/7 on Render!** 🎉

Check your stats: `https://your-app.onrender.com/stats`

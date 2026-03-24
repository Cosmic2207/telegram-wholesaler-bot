# Deploy Telegram Wholesaler Bot on Render (Free Tier)

## Step 1: Push Code to GitHub

1. Go to [github.com](https://github.com) and create a new repository (e.g., `telegram-wholesaler-bot`)
2. Upload all the files from this folder to that repository

## Step 2: Create a Render Account

1. Go to [render.com](https://render.com) and sign up (free)
2. Connect your GitHub account

## Step 3: Deploy on Render

1. In Render dashboard, click **New** > **Web Service**
2. Select your GitHub repo (`telegram-wholesaler-bot`)
3. Configure:
   - **Name**: `telegram-wholesaler-bot`
   - **Runtime**: `Docker`
   - **Plan**: `Free`
4. Add **Environment Variables**:
   - `BOT_TOKEN` = `8510310498:AAFAi2lSjwSWb5Fuo3mMKpOn1vvl18VEb6Y`
   - `ADMIN_USER_ID` = your Telegram user ID (message @userinfobot on Telegram to get it)
   - `PORT` = `10000`
5. Click **Create Web Service**

## Step 4: Wait for Deployment

- Render will build and deploy your bot automatically
- Once it shows **Live**, your bot is running!
- Open Telegram, find your bot, and send `/start`

## Important Notes

- Render free tier spins down after 15 minutes of inactivity. The bot will wake up when it receives a message (may take 30-60 seconds for first response after sleep).
- To keep it always running, you can upgrade to Render's paid plan or use a free uptime monitor like [UptimeRobot](https://uptimerobot.com) to ping your Render URL every 14 minutes.
- Your Render URL will be: `https://telegram-wholesaler-bot.onrender.com`

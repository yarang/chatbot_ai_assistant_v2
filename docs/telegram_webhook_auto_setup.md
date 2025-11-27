# Automatic Webhook Setup

The application now automatically sets the Telegram webhook on startup if `TELEGRAM_WEBHOOK_URL` is configured in `.env`.

## Configuration

Add the following to your `.env` file:

```bash
TELEGRAM_WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app/webhook
```

## How It Works

When the application starts (in `main.py` lifespan function):

1. Checks if `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_URL` are both configured
2. Automatically calls Telegram API to set the webhook
3. Logs the result (success or failure)

## Benefits

- ✅ No need to manually run `telegram_webhook.py` script
- ✅ Webhook automatically updates when app restarts
- ✅ Easier deployment and local development

## Log Output

On successful startup, you'll see:
```
INFO | Starting application with log level: INFO
INFO | Setting Telegram webhook to: https://8d20506fe6f3.ngrok-free.app/webhook
INFO | ✅ Telegram webhook set successfully
```

## Manual Override

You can still use the `scripts/telegram_webhook.py` utility script if needed to:
- Check webhook status
- Manually change webhook URL
- Delete webhook (for polling mode)

## Important Notes

⚠️ **ngrok Users**: Remember to update `TELEGRAM_WEBHOOK_URL` in `.env` when ngrok restarts with a new URL, then restart your application.

🚀 **Production**: Use a permanent domain instead of ngrok for production deployments.

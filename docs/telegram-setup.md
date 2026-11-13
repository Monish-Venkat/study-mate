# Turning the Telegram bot on

The Telegram code is complete and tested; only the credentials are missing.
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET` are both empty, and the
webhook endpoint refuses with `503 Telegram is not configured.` until they are
set. Nothing in the app can supply them — they come from Telegram and from a
tunnel — so this is the one surface that cannot be made to work without you.

Verified working offline, with no bot token (so the moment a token is set,
these behave):

- command dispatch — `/start`, `/help`, `/course physics PUC2 KA`
  ("Course updated."), a bad `/course` ("Use /course physics PUC2 KA"),
  `/teacher`
- answer formatting — LaTeX becomes readable Unicode, so
  `\frac{1}{f} = (n-1)(\frac{1}{R_1} - \frac{1}{R_2})` is sent as
  `(1)/(f) = (n-1)((1)/(R₁) - (1)/(R₂))`, with no stray backslashes or `$`
- long answers split on paragraph boundaries to stay under Telegram's limit

## What is still needed

**1. A bot and its token.** In Telegram, message `@BotFather`, send
`/newbot`, follow the prompts. It replies with a token like
`8123456789:AAH...`. Put it in `study-mate/.env`:

```
TELEGRAM_BOT_TOKEN=8123456789:AAH...
TELEGRAM_WEBHOOK_SECRET=<any long random string you invent>
```

The secret is yours to choose; Telegram echoes it back on every call and the
router rejects anything that does not match, so it is what stops strangers
POSTing to your webhook.

**2. A public HTTPS URL.** Telegram will not deliver to `127.0.0.1`. For a
demo, a tunnel is enough:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

That prints an `https://<something>.trycloudflare.com` address. `ngrok http
8000` does the same job.

**3. Point Telegram at it.** With `<TOKEN>`, `<SECRET>` and `<PUBLIC_URL>`
filled in:

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/setWebhook" -d "url=<PUBLIC_URL>/webhook" -d "secret_token=<SECRET>"
```

**4. Restart the backend** so it reads the new `.env`, then message the bot.

## Checking it

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | python -m json.tool
```

`pending_update_count` climbing with `last_error_message` set means Telegram
is reaching you but the app is rejecting it — almost always a mismatched
secret. A 404 means the URL is wrong or the tunnel has moved; a free tunnel
gets a new address every restart, so re-run `setWebhook` after restarting it.

## Note for the demo

`PUBLIC_APP_URL` is still `http://127.0.0.1:3000`, so `/teacher` replies with
a localhost link that will not open on a phone. Set it to the tunnel address
too if you intend to show that command.

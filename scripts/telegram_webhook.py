"""Register Telegram webhook explicitly after configuring a public HTTPS backend URL."""
import argparse
import asyncio
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.core.config import settings
from app.services.telegram import api

async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('url',help='Public HTTPS URL ending in /webhook')
    args=parser.parse_args()
    if not args.url.startswith('https://') or not args.url.endswith('/webhook'):
        parser.error('Use an HTTPS URL ending in /webhook')
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_WEBHOOK_SECRET:
        parser.error('Configure TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET first')
    await api('setWebhook',{'url':args.url,'secret_token':settings.TELEGRAM_WEBHOOK_SECRET,'allowed_updates':['message']})
    print('Webhook registered.')

if __name__=='__main__':asyncio.run(main())

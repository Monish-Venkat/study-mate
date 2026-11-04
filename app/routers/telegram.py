import asyncio
import hmac
import time
from fastapi import APIRouter,Header,HTTPException
from app.core.config import settings
from app.services.memory import memory
from app.services.telegram import handle_update
router=APIRouter(tags=['telegram'])
_lock=asyncio.Lock()

@router.post('/webhook')
async def webhook(payload:dict,x_telegram_bot_api_secret_token:str=Header(default='')):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_WEBHOOK_SECRET:raise HTTPException(503,'Telegram is not configured.')
    if not hmac.compare_digest(x_telegram_bot_api_secret_token,settings.TELEGRAM_WEBHOOK_SECRET):raise HTTPException(403,'Invalid webhook secret.')
    update_id=payload.get('update_id')
    if not isinstance(update_id,int):raise HTTPException(422,'Missing update_id.')
    scope=str(update_id)
    async with _lock:
        existing=memory.read('telegram-worker','telegram_update',scope)
        if not existing:
            memory.put('telegram-worker','telegram_update',{'payload':payload,'status':'queued','attempts':0,'next_attempt':0},scope,True)
    return {'accepted':True}

async def worker():
    from app.services.security import unseal
    while True:
        try:
            with memory.db() as db:rows=db.execute("SELECT * FROM records WHERE kind='telegram_update' ORDER BY id").fetchall()
            for row in rows:
                item=unseal(row['value'],row['owner']+row['kind']+row['scope'])
                if item['status']=='done' or item['attempts']>=3 or item['next_attempt']>time.time():continue
                try:
                    await handle_update(item['payload'])
                    item['status']='done';item['payload']={}
                except Exception:
                    item['status']='failed';item['attempts']+=1;item['next_attempt']=time.time()+60
                memory.put('telegram-worker','telegram_update',item,row['scope'],True)
        except asyncio.CancelledError:raise
        except Exception:pass
        await asyncio.sleep(2)

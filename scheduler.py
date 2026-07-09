import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import db

logger = logging.getLogger(__name__)


async def recheck_job(bot: Bot):
    due = await db.get_due_rechecks()
    for sub in due:
        channel = await db.get_channel(sub["channel_id"])
        if not channel:
            # канал удалён — просто снимаем заморозку без возврата владельцу
            await db.change_frozen(sub["user_id"], -sub["reward"])
            continue

        still_subscribed = False
        try:
            member = await bot.get_chat_member(channel["chat_id"], sub["user_id"])
            still_subscribed = member.status in ("member", "administrator", "creator")
        except Exception:
            logger.warning("Recheck failed for sub %s: could not fetch member", sub["id"])
            still_subscribed = False

        if still_subscribed:
            await db.confirm_subscription(sub["id"], sub["user_id"], sub["reward"])
            try:
                await bot.send_message(
                    sub["user_id"],
                    f"🎉 Подписка на «{channel['title']}» подтверждена! "
                    f"Начислено {sub['reward']:.1f} балла на баланс.",
                )
            except Exception:
                pass
        else:
            await db.cancel_subscription(
                sub["id"], sub["user_id"], channel["owner_id"], sub["reward"], sub["cost"]
            )
            try:
                await bot.send_message(
                    sub["user_id"],
                    f"⚠️ Ты отписался от «{channel['title']}» раньше срока проверки — "
                    f"баллы за это задание сгорели.",
                )
            except Exception:
                pass


def setup_scheduler(bot: Bot, interval_minutes: int) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(recheck_job, "interval", minutes=interval_minutes, args=(bot,), id="recheck_job")
    return scheduler

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import logging

class TaskScheduler:
    def __init__(self, db_url: str):
        jobstores = {
            'default': SQLAlchemyJobStore(url=db_url.replace("+asyncpg", "")) # APScheduler uses sync driver
        }
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)

    async def add_reminder(self, user_id: int, message: str, run_at):
        """Adds a one-time reminder task."""
        # This would need a way to send the message back to the user
        # We'd probably pass the telegram bot instance to the task
        pass

    def start(self):
        self.scheduler.start()
        logging.info("Task Scheduler started.")

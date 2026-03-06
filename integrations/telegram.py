import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from core.agent import SimmiAgent
from core.security import decrypt_key
from core.logger import get_logger
from core.schemas import SimmiConfig
from integrations.speech_to_text import WhisperSTT
from integrations.tts_elevenlabs import ElevenLabsTTS
from pydub import AudioSegment
import os
import uuid

logger = get_logger("telegram")

class TelegramInterface:
    def __init__(self, config: SimmiConfig, agent: SimmiAgent):
        self.config = config
        self.agent = agent
        
        # Voice components
        self.stt = WhisperSTT(config.llm.api_key) if config.voice.enabled else None
        self.tts = ElevenLabsTTS(
            config.voice.elevenlabs_api_key, 
            config.voice.elevenlabs_voice_id
        ) if config.voice.enabled else None

        # Decrypt token
        token = decrypt_key(config.telegram.bot_token)
        self.application = ApplicationBuilder().token(token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.help_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("ask", self.ask_command))
        self.application.add_handler(CommandHandler("memory", self.memory_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("agents", self.agents_command))
        self.application.add_handler(CommandHandler("system", self.system_command))
        self.application.add_handler(CommandHandler("tasks", self.tasks_command))
        self.application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.handle_message))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))

    def _is_authorized(self, user_id: int) -> bool:
        return user_id in self.config.telegram.allowed_user_ids

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id): return
        if not self.config.voice.enabled:
            await update.message.reply_text("🎙️ Voice processing is currently disabled.")
            return

        log = logger.bind(user=update.effective_user.id)
        log.info("voice_message_received")
        
        # Download and process voice
        try:
            voice_file = await update.message.voice.get_file()
            ogg_path = f"storage/audio/{uuid.uuid4().hex}.ogg"
            mp3_path = ogg_path.replace(".ogg", ".mp3")
            
            await voice_file.download_to_drive(ogg_path)
            
            # Convert OGG to MP3 for Whisper
            audio = AudioSegment.from_ogg(ogg_path)
            audio.export(mp3_path, format="mp3")
            
            # Transcription
            text = self.stt.transcribe_audio(mp3_path)
            if not text:
                await update.message.reply_text("❌ Sorry, I couldn't understand that audio.")
                return
            
            await update.message.reply_text(f"📝 _Transcribed:_ {text}", parse_mode='Markdown')
            
            # Agent Processing
            response_text = await self.agent.handle_message(update.effective_user.id, text)
            
            # Response (Text + Optional Voice)
            if self.config.voice.response_mode == "voice" and self.tts:
                audio_reply_path = await self.tts.generate_voice(response_text)
                if audio_reply_path:
                    with open(audio_reply_path, "rb") as audio:
                        await update.message.reply_voice(audio)
                else:
                    await update.message.reply_text(response_text)
            else:
                await update.message.reply_text(response_text)
            
            # Cleanup temp files
            os.remove(ogg_path)
            os.remove(mp3_path)
            
        except Exception as e:
            log.error("voice_processing_failed", error=str(e))
            await update.message.reply_text("❌ An error occurred while processing your voice message.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = f"""
🤖 *Simmi Agent* - V2 Production
Greetings! I am {self.agent.personality_name}.

Commands:
/ask <query> - Ask me anything
/run <task> - Execute complex tasks
/memory <query> - Search my memories
/schedule <task> - Schedule future tasks
/agents - List specialized agents
/system - System diagnostics
/status - Check health
/help - Show this message
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def agents_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id): return
        agents_text = """
👥 *Specialized Agents:*
- *Planner*: Task decomposition (DAG)
- *Coder*: Write production-ready code
- *Researcher*: Gather technical docs
- *Debugger*: Fix errors in sandbox
- *Security*: Audit code vulnerabilities
- *DevOps*: Infrastructure & Docker
        """
        await update.message.reply_text(agents_text, parse_mode='Markdown')

    async def system_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id): return
        # Simple stats
        await update.message.reply_text("🖥️ *System Info:*\n- OS: Linux (VPS)\n- Memory: redis (short) + pgvector (long)\n- Sandbox: Docker", parse_mode='Markdown')

    async def tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📋 *Active Task Graphs:* None at the moment.")

    async def ask_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ Unauthorized User.")
            return

        query = " ".join(context.args)
        if not query:
            await update.message.reply_text("Please provide your request after /ask")
            return

        # Use the unified handle_message logic
        response = await self.agent.handle_message(update.effective_user.id, query)
        await update.message.reply_text(response)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            return
        
        # Log incoming
        logger.info("telegram_message", user=update.effective_user.id, first_name=update.effective_user.first_name)
        
        response = await self.agent.handle_message(update.effective_user.id, update.message.text)
        await update.message.reply_text(response)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            return
        
        status_msg = f"""
✅ *System Status*
- *Agent*: Online ({self.config.personality.name})
- *Core*: {self.config.llm.provider.upper()}
- *Memory*: PostgreSQL + PGVector
- *Sandbox*: Active
        """
        await update.message.reply_text(status_msg, parse_mode='Markdown')

    async def memory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update.effective_user.id):
            return
        
        query = " ".join(context.args)
        if not query:
            await update.message.reply_text("What should I search for in my memory?")
            return
            
        emb = await self.agent.llm.get_embedding(query)
        mems = await self.agent.memory.search_memory(update.effective_user.id, emb)
        
        if not mems:
            await update.message.reply_text("I couldn't recall anything similar.")
            return
            
        mem_text = "\n".join([f"- {m.content} ({m.timestamp.strftime('%Y-%m-%d')})" for m in mems])
        await update.message.reply_text(f"🧠 *Realled Context:*\n{mem_text}", parse_mode='Markdown')

    async def start(self):
        logger.info("telegram_bot_starting")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("telegram_bot_polling")

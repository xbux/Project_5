import asyncio
import yt_dlp
import os
import static_ffmpeg
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CallbackQueryHandler, CommandHandler


class MUSIC:
    def __init__(self):
        self.db_file = 'song_ids.json'
        self.settings_file = 'settings.json'
        
        
    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r', encoding = 'utf-8') as file:
                data = json.load(file)

            self.youtube_options  = data['YOUTUBE_OPTIONS']
            self.search_options   = data['SEARCH_OPTIONS']
            self.download_options = data['DOWNLOAD_OPTIONS']

            self.search_options['extractor_args']   = self.youtube_options
            self.download_options['extractor_args'] = self.youtube_options

            print(f"Search format: {self.search_options['format']}")
            print(f"YouTube client: {self.search_options['extractor_args']['youtube']['player_client']}")
            print(f"Download format: {self.download_options['format']}")
        
        else:
            print(f"Settings file > '{self.settings_file}' missed, please place it to continue")
            os._exit(0)
        
    def load_record(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r', encoding = 'utf-8') as file:
                return json.load(file)

        else:
            print(f"Record file > '{self.db_file}' missed, returning a empty list")
            return {}
        
    async def save_record(self, record):
        with open(self.db_file, 'w', encoding = 'utf-8') as file:
            json.dump(record, file, ensure_ascii = False, indent = 4)
    
    async def start_commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        effective_chat = update.effective_chat
        user_id = str(update.effective_user.id)
        keyboard = [[InlineKeyboardButton("🔍 New search", callback_data = "new_search")]]
        if user_id in self.record and self.record[user_id]:
            keyboard.append([InlineKeyboardButton("📂 My Library (Record)", callback_data = "see_record")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "🚗 **YouTube CarPlay Bot**\nWhat do you want to do?"
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(text, 
                                                              reply_markup = reply_markup,
                                                              parse_mode = 'Markdown')
            except:
                await context.bot.send_message(chat_id = effective_chat.id,
                                               text = text,
                                               reply_markup = reply_markup,
                                               parse_mode = 'Markdown')
        else:
            await update.message.reply_text(text, 
                                            reply_markup = reply_markup, 
                                            parse_mode = 'Markdown')
            
    async def show_record(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = str(query.from_user.id)
        if user_id not in self.record or not self.record[user_id]:
            return await query.answer("Empty Library", show_alert = True)
        keyboard = []
        library = self.record[user_id][-10:]
        for i, item in enumerate(library):
            keyboard.append([InlineKeyboardButton(f"🎵 {item['title']}", callback_data = f"idx|{i}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back to menu", callback_data = "main_menu")])
        await query.edit_message_text("📂 **Songs record:**",
                                      reply_markup = InlineKeyboardMarkup(keyboard), 
                                      parse_mode = 'Markdown')
        
    async def send_byindex(self, update: Update, context: ContextTypes.DEFAULT_TYPE, indice: int):
        query = update.callback_query
        user_id = str(query.from_user.id)
        try:
            library = self.record[user_id][-10:]
            file_id = library[indice]['file_id']
            await query.answer("Sending song...")
            await context.bot.send_audio(chat_id = query.message.chat_id, audio = file_id)
            await self.start_commands(update, context)
        except:
            await query.answer("Cannot retrieve song", show_alert = True)
    
    async def search_song(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text.startswith('/'): return
        query_text = update.message.text
        espera = await update.message.reply_text(f"🔍 Searching: '{query_text}'...")
        try:
            with yt_dlp.YoutubeDL(self.search_options) as ydl:
                loop = asyncio.get_event_loop()
                information = await loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch3:{query_text}", download = False))
                results = information.get('entries', [])

            keyboard = []
            for video in results:
                if not video or video.get('duration', 0) > 600: continue
                duration = video.get('duration_string') or "??:??"
                keyboard.append([InlineKeyboardButton(f"🎵 {video['title'][:35]} - [{duration}]", callback_data = f"dl|{video['id']}")])

            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data = "main_menu")])
            await espera.edit_text(f"✨ Results: {query_text}",
                                   reply_markup = InlineKeyboardMarkup(keyboard))
        except Exception as error:
            await espera.edit_text(f"❌ Error: {error}")
            
    async def handle_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer() 
        if query.data == "main_menu": 
            return await self.start_commands(update, context)
        
        if query.data == "see_record": 
            return await self.show_record(update, context)
        
        if query.data == "new_search": 
            return await query.edit_message_text("⌨️ Song name or artist:")
        
        if query.data.startswith("idx|"):
            indice = int(query.data.split("|")[1])
            return await self.send_byindex(update, context, indice)
        
        if query.data.startswith("dl|"):
            video_id = query.data.split("|")[1]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            aviso = await query.message.reply_text("📥 Downloading...")
            try:
                with yt_dlp.YoutubeDL(self.download_options) as ydl:
                    loop = asyncio.get_event_loop()
                    info = await loop.run_in_executor(None, lambda: ydl.extract_info(video_url, download = True))
                    basename = ydl.prepare_filename(info).rsplit('.', 1)[0]
                    filename = f"{basename}.mp3"
                    thumb_path = next((f"{basename}{ex}" for ex in ['.jpg', '.webp', '.png', '.jpeg'] if os.path.exists(f"{basename}{ex}")), None)

                    with open(filename, 'rb') as audio:
                        user_id = str(query.from_user.id)
                        msg = await context.bot.send_audio(
                            chat_id   = query.message.chat_id,
                            audio     = audio,
                            title     = info.get('title'),
                            performer = info.get('uploader', "CarPlay"),
                            thumbnail = open(thumb_path, 'rb') if thumb_path else None)
                        
                        if user_id not in self.record: self.record[user_id] = []
                        self.record[user_id].append({'title': info.get('title')[:40], 'file_id': msg.audio.file_id})
                        await self.save_record(self.record)

                    if os.path.exists(filename): os.remove(filename)
                    for ext in ['.jpg', '.webp', '.png', '.jpeg']:
                        if os.path.exists(f"{basename}{ext}"): os.remove(f"{basename}{ext}")
                    
                    await aviso.delete()
                    await self.start_commands(update, context)
            except Exception as error:
                await context.bot.send_message(chat_id = query.message.chat_id,
                                               text = f"❌ Error: {error}")
                
                
    def start(self):
        os.system('cls')
        TOKEN = "8709404197:AAGczUDoh5-ah1KQw1WL1crG3GTLoZSbGog"
        static_ffmpeg.add_paths()
        print("🚀 YouTube Carplay Bot\n")
        self.record = self.load_record()
        self.load_settings()
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", self.start_commands))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.search_song))
        app.add_handler(CallbackQueryHandler(self.handle_selection))
        app.run_polling()
        
music = MUSIC()
music.start()
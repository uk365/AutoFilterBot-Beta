import logging
import logging.config

# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("cinemagoer").setLevel(logging.ERROR)

from pyrogram import Client, __version__
from pyrogram.raw.all import layer
from database.ia_filterdb import Media
from aiohttp import web
from database.users_chats_db import db #, update_users_data
from web import web_server
from info import SESSION_STRING, LOG_CHANNEL, API_ID, API_HASH, BOT_TOKEN, PORT, BIN_CHANNEL
from utils import temp
from typing import Union, Optional, AsyncGenerator
from pyrogram import types
import time, os
from pyrogram.errors import AccessTokenExpired, AccessTokenInvalid

async def update_users_data():
    logging.info("Updating all Users Database........")
    users = await db.get_all_users()
   # users = int(userx['id'])
    for user in users:
        us = user['id']
        ax = "False"
        ax1 = ""
        try:
            default = {
                'is_verified':ax,
                'verified_time':ax1,
                'verify_token':ax1,
                'link':ax1, 
            }
            await db.update_x(us, default) 
        except Exception as e:
            logging.exception(f"Error while restarting bot with token {bot['user_id']}: {e}")
    logging.info("All Users Database Updated.")


class Bot(Client):
    def __init__(self):
        super().__init__(
            name='Auto_Filter_Bot',
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )

    async def start(self):
        temp.START_TIME = time.time()
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        try:
            await super().start()
        except (AccessTokenExpired, AccessTokenInvalid):
            logging.error("Your BOT_TOKEN revoke and add again, exiting now")
            exit()
        if len(SESSION_STRING) != 0:
            user_bot = Client(
                name='Auto_Filter_User_Bot',
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=SESSION_STRING
            )
            try:
                await user_bot.start()
                name = f'@{username}' if (username := user_bot.me.username) else user_bot.me.first_name
                logging.info(f'User Bot [{name}] Started!')
                temp.USER_BOT = user_bot
            except:
                logging.error("Your SESSION_STRING revoke and add again, exiting now")
                exit()
        if os.path.exists('restart.txt'):
            with open("restart.txt") as file:
                chat_id, msg_id = map(int, file)
            try:
                await self.edit_message_text(chat_id=chat_id, message_id=msg_id, text='Restarted Successfully!')
            except:
                pass
            os.remove('restart.txt')
        temp.BOT = self
        await Media.ensure_indexes()
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        username = '@' + me.username
        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()
        logging.info(f"\n\nBot [{username}] Started!\n\n")
        await update_users_data() 
        logging.info("I'm Running") 
        try:
            await self.send_message(chat_id=LOG_CHANNEL, text=f"<b>{me.mention} Restarted! 🤖</b>")
        except:
            logging.error("Make sure bot admin in LOG_CHANNEL, exiting now")
            exit()
        try:
            m = await self.send_message(chat_id=BIN_CHANNEL, text="Test")
            await m.delete()
        except:
            logging.error("Make sure bot admin in BIN_CHANNEL, exiting now")
            exit()


    async def stop(self, *args):
        await super().stop()
        logging.info("Bot stopped! Bye...")


app = Bot()
app.run()

import os
import logging
import random, string
import asyncio
import time
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import Media, get_file_details, unpack_new_file_id, delete_files
from database.users_chats_db import db
from info import INDEX_CHANNELS, ADMINS, IS_VERIFY, VERIFY_EXPIRE, SHORTLINK_API, SHORTLINK_URL, AUTH_CHANNEL, DELETE_TIME, SUPPORT_LINK, UPDATES_LINK, LOG_CHANNEL, PICS, PROTECT_CONTENT
from utils import get_settings, get_size, is_subscribed, is_check_admin, get_shortlink, save_group_settings, temp, get_readable_time, get_wish
from database.connections_mdb import all_connections, delete_connections, add_connection
import re
import json
import base64
import sys
from shortzy import Shortzy
from telegraph import upload_file
logger = logging.getLogger(__name__)


@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        if not await db.get_chat(message.chat.id):
            total=await client.get_chat_members_count(message.chat.id)
            r_j = message.from_user.mention if message.from_user else "Anonymous"
            await client.send_message(LOG_CHANNEL, script.NEW_GROUP_TXT.format(message.chat.title, message.chat.id, total, r_j))       
            await db.add_chat(message.chat.id, message.chat.title)
        wish = get_wish()
        btn = [[
            InlineKeyboardButton('⚡️ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ⚡️', url=UPDATES_LINK),
            InlineKeyboardButton('💡 Support Group 💡', url=SUPPORT_LINK)
        ]]
        await message.reply(text=f"<b>ʜᴇʏ {message.from_user.mention}, <i>{wish}</i>\nʜᴏᴡ ᴄᴀɴ ɪ ʜᴇʟᴘ ʏᴏᴜ??</b>", reply_markup=InlineKeyboardMarkup(btn))
        return 
        
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.NEW_USER_TXT.format(message.from_user.mention, message.from_user.id))

    verify_status = await db.get_verify_status(message.from_user.id)
    if verify_status['is_verified'] and VERIFY_EXPIRE < (time.time() - verify_status['verified_time']):
        await db.update_verify_status(message.from_user.id, is_verified=False)
    
    if (len(message.command) != 2) or (len(message.command) == 2 and message.command[1] == 'start'):
        buttons = [[
            InlineKeyboardButton("+ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ +", url=f'http://t.me/{temp.U_NAME}?startgroup=start')
        ],[
            InlineKeyboardButton('⚡️ ᴜᴘᴅᴀᴛᴇs ⚡️', url=UPDATES_LINK),
            InlineKeyboardButton('💡 Support 💡', url=SUPPORT_LINK)
        ],[
            InlineKeyboardButton('🔎 sᴇᴀʀᴄʜ ɪɴʟɪɴᴇ 🔍', switch_inline_query_current_chat='')
        ],[
            InlineKeyboardButton('👨‍🚒 ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('📚 ᴀʙᴏᴜᴛ', callback_data='my_about'),
           # InlineKeyboardButton('👤 ᴏᴡɴᴇʀ', callback_data='my_owner')
        ],[
            InlineKeyboardButton('💰 ᴇᴀʀɴ ᴍᴏɴᴇʏ ʙʏ ʙᴏᴛ 💰', callback_data='earn')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, get_wish()),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return

    btn = await is_subscribed(client, message) # This func is for AUTH_CHANNEL
    mc = message.command[1]
    if btn:
        if mc != 'subscribe':
            try:
                btn.append(
                    [InlineKeyboardButton("🔁 Try Again 🔁", callback_data=f"pm_checksub#{mc}")]
                )
            except (IndexError, ValueError):
                btn.append(
                    [InlineKeyboardButton("🔁 Try Again 🔁", url=f"https://t.me/{temp.U_NAME}?start={mc}")]
                )
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=f"👋 Hello {message.from_user.mention},\n\nPlease join my 'Updates Channel' and request again. 😇",
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return

    if mc.startswith('verify'):
        _, token = mc.split("_", 1)
        verify_status = await db.get_verify_status(message.from_user.id)
        if verify_status['verify_token'] != token:
            return await message.reply("Your verify token is invalid.")
        await db.update_verify_status(message.from_user.id, is_verified=True, verified_time=time.time())
        btn = [[
            InlineKeyboardButton("📌 Get File 📌", url=f'https://t.me/{temp.U_NAME}?start={verify_status["link"]}')
        ]]
        await message.reply(f"✅ You successfully verified until: {get_readable_time(VERIFY_EXPIRE)}", reply_markup=InlineKeyboardMarkup(btn), protect_content=True)
        return
    
    verify_status = await db.get_verify_status(message.from_user.id)
    if IS_VERIFY and not verify_status['is_verified']:
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        await db.update_verify_status(message.from_user.id, verify_token=token, link=mc)
        link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/{temp.U_NAME}?start=verify_{token}')
        btn = [[
            InlineKeyboardButton("🧿 Verify 🧿", url=link)
        ]]
        await message.reply("You not verified today! Kindly verify now. 🔐", reply_markup=InlineKeyboardMarkup(btn), protect_content=True)
        return
 
    if mc.startswith('all'):
        _, grp_id, key = mc.split("_", 2)
        files = temp.FILES.get(key)
        if not files:
            return await message.reply('No Such All Files Exist!')
        settings = await get_settings(int(grp_id))
        for file in files:
            CAPTION = settings['caption']
            f_caption = CAPTION.format(
                file_name = file.file_name,
                file_size = get_size(file.file_size),
                file_caption=file.caption
            )   
            btn = [[
                InlineKeyboardButton("✛ ᴡᴀᴛᴄʜ & ᴅᴏᴡɴʟᴏᴀᴅ ✛", callback_data=f"stream#{file.file_id}")
            ],[
                InlineKeyboardButton('⁉️ ᴄʟᴏsᴇ ⁉️', callback_data='close_data')
            ]]
            await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file.file_id,
                caption=f_caption,
                protect_content=settings['file_secure'],
                reply_markup=InlineKeyboardMarkup(btn)
            )
        return
        
    _, grp_id, file_id = mc.split("_", 2)
    files_ = await get_file_details(file_id)
    if not files_:
        return await message.reply('No Such File Exist!')
    settings = await get_settings(int(grp_id))
    files = files_[0]
    CAPTION = settings['caption']
    f_caption = CAPTION.format(
        file_name = files.file_name,
        file_size = get_size(files.file_size),
        file_caption=files.caption
    )
    btn = [[
        InlineKeyboardButton("✛ ᴡᴀᴛᴄʜ & ᴅᴏᴡɴʟᴏᴀᴅ ✛", callback_data=f"stream#{file_id}")
    ],[
        InlineKeyboardButton('⁉️ ᴄʟᴏsᴇ ⁉️', callback_data='close_data')
    ]]
    await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        protect_content=settings['file_secure'],
        reply_markup=InlineKeyboardMarkup(btn)
    )

@Client.on_message(filters.command('index_channels') & filters.user(ADMINS))
async def channels_info(bot, message):
    """Send basic information of index channels"""
    if not (ids:=INDEX_CHANNELS):
        return await message.reply("Not set INDEX_CHANNELS")

    text = '**Indexed Channels:**\n'
    for id in ids:
        chat = await bot.get_chat(id)
        text += f'{chat.title}\n'
    text += f'\n**Total:** {len(ids)}'
    await message.reply(text)

@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file(bot, message):
    try:
        await message.reply_document('Logs.txt')
    except:
        await message.reply('Not found logs!')


@Client.on_message(filters.command('stats') & filters.user(ADMINS))
async def stats(bot, message):
    msg = await message.reply('Please Wait...')
    files = await Media.count_documents()
    users = await db.total_users_count()
    chats = await db.total_chat_count()
    size = await db.get_db_size()
    free = 536870912 - size
    uptime = get_readable_time(time.time() - temp.START_TIME)
    size = get_size(size)
    free = get_size(free)
    await msg.edit(script.STATUS_TXT.format(files, users, chats, size, free, uptime))
    
    
@Client.on_message(filters.command('settings'))
async def settings(client, message):
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        btn = []
        ids = await all_connections(message.from_user.id)
        for id in ids:
            try:
                chat = await client.get_chat(id)
                btn.append(
                    [InlineKeyboardButton(text=chat.title, callback_data=f'pm_settings#{chat.id}')]
                )
            except:
                await delete_connections(id)
        if btn:
            await message.reply_text('Select the group whose settings you want to change.\n\n<i>If your group not showing here? Use this command in your group.</i>', reply_markup=InlineKeyboardMarkup(btn))
        else:
            await message.reply_text("No groups found! Use this command group.")
            
    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id

        if not await is_check_admin(client, grp_id, message.from_user.id):
            return await message.reply_text('You not admin in this group.')

        async for member in client.get_chat_members(grp_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
            if not member.user.is_bot:
                await add_connection(grp_id, member.user.id)
        
        btn = [[
            InlineKeyboardButton("👤 Open Private Chat 👤", callback_data=f"opn_pm_setgs#{grp_id}")
        ],[
            InlineKeyboardButton("👥 Open Here 👥", callback_data=f"opn_grp_setgs#{grp_id}")
        ]]
        await message.reply_text(
            text="Where do you want to open the settings menu? ⚙️",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.HTML
        )


@Client.on_message(filters.command('set_template'))
async def save_template(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("Use this command in group.")
        
    grp_id = message.chat.id
    title = message.chat.title

    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('You not admin in this group.')

    try:
        template = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("Command Incomplete!")
    
    await save_group_settings(grp_id, 'template', template)
    await message.reply_text(f"Successfully changed template for {title} to\n\n{template}")
    
    
@Client.on_message(filters.command('set_caption'))
async def save_caption(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("Use this command in group.")
        
    grp_id = message.chat.id
    title = message.chat.title

    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('You not admin in this group.')

    try:
        caption = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("Command Incomplete!")
    
    await save_group_settings(grp_id, 'caption', caption)
    await message.reply_text(f"Successfully changed caption for {title} to\n\n{caption}")
    
    
@Client.on_message(filters.command('set_shortlink'))
async def save_shortlink(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("Use this command in group.")
        
    grp_id = message.chat.id
    title = message.chat.title

    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('You not admin in this group.')

    try:
        _, url, api = message.text.split(" ", 2)
    except:
        return await message.reply_text("<b>Command Incomplete:-\n\ngive me a shortlink & api along with the command...\n\nEx:- <code>/shortlink mdisklink.link 5843c3cc645f5077b2200a2c77e0344879880b3e</code>")
    
    try:
        shortzy = Shortzy(api_key=api, base_site=url)
        link = f'https://t.me/{temp.U_NAME}'
        await shortzy.convert(link)
    except:
        return await message.reply_text("Your shortlink API or URL invalid, Please Check again!")
    
    await save_group_settings(grp_id, 'url', url)
    await save_group_settings(grp_id, 'api', api)
    await message.reply_text(f"Successfully changed shortlink for {title} to\n\nURL - {url}\nAPI - {api}")
    

@Client.on_message(filters.command('get_custom_settings'))
async def get_custom_settings(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("Use this command in group.")
    grp_id = message.chat.id
    title = message.chat.title
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('You not admin in this group.')
        
    settings = await get_settings(grp_id)
    text = f"""Custom settings for: {title}

Shortlink URL: {settings["url"]}
Shortlink API: {settings["api"]}

IMDb Template: {settings['template']}

File Caption: {settings['caption']}

Welcome Text: {settings['welcome_text']}

Tutorial Link: {settings['tutorial']}

Force Channels: {str(ids)[1:-1] if (ids:=settings['fsub']) else 'Not Set'}"""

    btn = [[
        InlineKeyboardButton(text="Close", callback_data="close_data")
    ]]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)


@Client.on_message(filters.command('set_welcome'))
async def save_welcome(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("Use this command in group.")
        
    grp_id = message.chat.id
    title = message.chat.title

    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('You not admin in this group.')

    try:
        welcome = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("Command Incomplete!")
    
    await save_group_settings(grp_id, 'welcome_text', welcome)
    await message.reply_text(f"Successfully changed welcome for {title} to\n\n{welcome}")
    
    
@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    msg = await message.reply_text('Fetching...')
    srt = await Media.count_documents({'mime_type': 'application/x-subrip'})
    avi = await Media.count_documents({'mime_type': 'video/x-msvideo'})
    zip = await Media.count_documents({'mime_type': 'application/zip'})
    rar = await Media.count_documents({'mime_type': 'application/x-rar-compressed'})
    btn = [[
        InlineKeyboardButton(f"SRT ({srt})", callback_data="srt_delete"),
        InlineKeyboardButton(f"AVI ({avi})", callback_data="avi_delete"),
    ],[
        InlineKeyboardButton(f"ZIP ({zip})", callback_data="zip_delete"),
        InlineKeyboardButton(f"RAR ({rar})", callback_data="rar_delete")
    ],[
        InlineKeyboardButton("CLOSE", callback_data="close_data")
    ]]
    await msg.edit('Choose do you want to delete file type?', reply_markup=InlineKeyboardMarkup(btn))
    
    
@Client.on_message(filters.command('delete_file') & filters.user(ADMINS))
async def delete_file(bot, message):
    try:
        query = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("Command Incomplete!")
    msg = await message.reply_text('Searching...')
    total, files = await delete_files(query)
    if int(total) == 0:
        return await message.reply_text('Not have files in your query')
    btn = [[
        InlineKeyboardButton("YES", callback_data=f"delete_{query}")
    ],[
        InlineKeyboardButton("CLOSE", callback_data="close_data")
    ]]
    await msg.edit(f"Total {total} files found in your query {query}.\n\nDo you want to delete?", reply_markup=InlineKeyboardMarkup(btn))

    
@Client.on_message(filters.command('delete_all') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    btn = [[
        InlineKeyboardButton(text="YES", callback_data="delete_all")
    ],[
        InlineKeyboardButton(text="CLOSE", callback_data="close_data")
    ]]
    files = await Media.count_documents()
    await message.reply_text(f'Total {files} files have.\nDo you want to delete all?', reply_markup=InlineKeyboardMarkup(btn))



@Client.on_message(filters.command('set_tutorial'))
async def save_tutorial(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("Use this command in group.")
        
    grp_id = message.chat.id
    title = message.chat.title

    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('You not admin in this group.')

    try:
        tutorial = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("Command Incomplete!")
    
    await save_group_settings(grp_id, 'tutorial', tutorial)
    await message.reply_text(f"Successfully changed tutorial for {title} to\n\n{tutorial}")


@Client.on_message(filters.command('set_fsub'))
async def set_fsub(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("Use this command in group.")
        
    grp_id = message.chat.id
    title = message.chat.title

    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply_text('You not admin in this group.')

    try:
        ids = message.text.split(" ", 1)[1]
        fsub_ids = list(map(int, ids.split()))
    except IndexError:
        return await message.reply_text("Command Incomplete!\n\nCan multiple channel add separate by spaces. Like: /set_fsub id1 id2 id3")
    except ValueError:
        return await message.reply_text('Make sure ids is integer.')
        
    channels = "Channels:\n"
    for id in fsub_ids:
        try:
            chat = await client.get_chat(id)
        except Exception as e:
            return await message.reply_text(f"{id} is invalid!\nMake sure this bot admin in that channel.\n\nError - {e}")
        if chat.type != enums.ChatType.CHANNEL:
            return await message.reply_text(f"{id} is not channel.")
        channels += f'{chat.title}\n'
    await save_group_settings(grp_id, 'fsub', fsub_ids)
    await message.reply_text(f"Successfully set force channels for {title} to\n\n{channels}")


@Client.on_message(filters.command('telegraph'))
async def telegraph_upload(bot, message):
    if not (reply_to_message := message.reply_to_message):
        return await message.reply('Reply to any photo or video.')
    file = reply_to_message.photo or reply_to_message.video or None
    if file is None:
        return await message.reply('Invalid media.')
    if file.file_size >= 5242880:
        await message.reply_text(text="Send less than 5MB")   
        return
    text = await message.reply_text(text="ᴘʀᴏᴄᴇssɪɴɢ....")   
    media = await reply_to_message.download()  
    try:
        response = upload_file(media)
    except Exception as e:
        await text.edit_text(text=f"Error - {e}")
        return    
    try:
        os.remove(media)
    except:
        pass
    await text.edit_text(f"<b>❤️ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴘʜ ʟɪɴᴋ ᴄᴏᴍᴘʟᴇᴛᴇᴅ 👇</b>\n\n<code>https://telegra.ph/{response[0]}</code></b>")

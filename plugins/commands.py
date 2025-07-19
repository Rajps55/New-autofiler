import os
import random
import string
import asyncio
from time import time as time_now
from time import monotonic
import datetime
from Script import script
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import db_count_documents, second_db_count_documents, get_file_details, delete_files
from database.users_chats_db import db
from datetime import datetime, timedelta
from info import IS_PREMIUM, PRE_DAY_AMOUNT, RECEIPT_SEND_USERNAME, URL, BIN_CHANNEL, SECOND_FILES_DATABASE_URL, STICKERS, INDEX_CHANNELS, ADMINS, IS_VERIFY, VERIFY_TUTORIAL, VERIFY_EXPIRE, SHORTLINK_API, SHORTLINK_URL, DELETE_TIME, SUPPORT_LINK, UPDATES_LINK, LOG_CHANNEL, PICS, IS_STREAM, REACTIONS, PM_FILE_DELETE_TIME
from utils import is_premium, upload_image, get_settings, get_size, is_subscribed, is_check_admin, get_shortlink, get_verify_status, update_verify_status, save_group_settings, temp, get_readable_time, get_wish, get_seconds

async def del_stk(s):
    await asyncio.sleep(3)
    await s.delete()

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        if not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(message.chat.id)
            username = f'@{message.chat.username}' if message.chat.username else 'Private'
            await client.send_message(LOG_CHANNEL, script.NEW_GROUP_TXT.format(message.chat.title, message.chat.id, username, total))       
            await db.add_chat(message.chat.id, message.chat.title)
        wish = get_wish()
        user = message.from_user.mention if message.from_user else "Dear"
        btn = [[
            InlineKeyboardButton('⚡️ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ⚡️', url=UPDATES_LINK),
            InlineKeyboardButton('💡 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ 💡', url=SUPPORT_LINK)
        ]]
        await message.reply(text=f"<b>ʜᴇʏ {user}, <i>{wish}</i>\nʜᴏᴡ ᴄᴀɴ ɪ ʜᴇʟᴘ ʏᴏᴜ??</b>", reply_markup=InlineKeyboardMarkup(btn))
        return 
        
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except:
        await message.react(emoji="⚡️", big=True)

    d = await client.send_sticker(message.chat.id, random.choice(STICKERS))
    asyncio.create_task(del_stk(d))

    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.NEW_USER_TXT.format(message.from_user.mention, message.from_user.id))

    verify_status = await get_verify_status(message.from_user.id)
    if verify_status['is_verified'] and datetime.datetime.now() > verify_status['expire_time']:
        await update_verify_status(message.from_user.id, is_verified=False)


    if (len(message.command) != 2) or (len(message.command) == 2 and message.command[1] == 'start'):
        buttons = [[
            InlineKeyboardButton("+ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ +", url=f'http://t.me/{temp.U_NAME}?startgroup=start')
        ],[
            InlineKeyboardButton('ℹ️ ᴜᴘᴅᴀᴛᴇs', url=UPDATES_LINK),
            InlineKeyboardButton('🧑‍💻 sᴜᴘᴘᴏʀᴛ', url=SUPPORT_LINK)
        ],[
            InlineKeyboardButton('👨‍🚒 ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('🔎 sᴇᴀʀᴄʜ ɪɴʟɪɴᴇ', switch_inline_query_current_chat=''),
            InlineKeyboardButton('📚 ᴀʙᴏᴜᴛ', callback_data='about')
        ],[
            InlineKeyboardButton('🤑 Buy Premium', url=f"https://t.me/{temp.U_NAME}?start=premium")
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=script.START_TXT.format(message.from_user.mention, get_wish()),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return

    mc = message.command[1]

    if mc == 'premium':
        return await plan(client, message)
    
    if mc.startswith('settings'):
        _, group_id = message.command[1].split("_")
        if not await is_check_admin(client, (int(group_id)), message.from_user.id):
            return await message.reply("You not admin in this group.")
        btn = await get_grp_stg(int(group_id))
        chat = await client.get_chat(int(group_id))
        return await message.reply(f"Change your settings for <b>'{chat.title}'</b> as your wish. ⚙", reply_markup=InlineKeyboardMarkup(btn))


    if mc.startswith('inline_fsub'):
        btn = await is_subscribed(client, message)
        if btn:
            reply_markup = InlineKeyboardMarkup(btn)
            await message.reply(f"Please join my 'Updates Channel' and use inline search. 👍",
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            return 

    if mc.startswith('verify'):
        _, token = mc.split("_", 1)
        verify_status = await get_verify_status(message.from_user.id)
        if verify_status['verify_token'] != token:
            return await message.reply("Your verify token is invalid.")
        expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=VERIFY_EXPIRE)
        await update_verify_status(message.from_user.id, is_verified=True, expire_time=expiry_time)
        if verify_status["link"] == "":
            reply_markup = None
        else:
            btn = [[
                InlineKeyboardButton("📌 Get File 📌", url=f'https://t.me/{temp.U_NAME}?start={verify_status["link"]}')
            ]]
            reply_markup = InlineKeyboardMarkup(btn)
        await message.reply(f"✅ You successfully verified until: {get_readable_time(VERIFY_EXPIRE)}", reply_markup=reply_markup, protect_content=True)
        return
    
    verify_status = await get_verify_status(message.from_user.id)
    if IS_VERIFY and not verify_status['is_verified'] and not await is_premium(message.from_user.id, client):
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        await update_verify_status(message.from_user.id, verify_token=token, link="" if mc == 'inline_verify' else mc)
        link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/{temp.U_NAME}?start=verify_{token}')
        btn = [[
            InlineKeyboardButton("🧿 Verify 🧿", url=link)
        ],[
            InlineKeyboardButton('🗳 Tutorial 🗳', url=VERIFY_TUTORIAL)
        ]]
        await message.reply("You not verified today! Kindly verify now. 🔐", reply_markup=InlineKeyboardMarkup(btn), protect_content=True)
        return

    btn = await is_subscribed(client, message)
    if btn:
        btn.append(
            [InlineKeyboardButton("🔁 Try Again 🔁", callback_data=f"checksub#{mc}")]
        )
        reply_markup = InlineKeyboardMarkup(btn)
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=f"👋 Hello {message.from_user.mention},\n\nPlease join my 'Updates Channel' and try again. 😇",
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return 

    if mc.startswith('all'):
      _, grp_id, key = mc.split("_", 2)  # ✅ normal space only
       files = temp.FILES.get(key)
       if not files:
           return await message.reply('No Such All Files Exist!')

       settings = await get_settings(int(grp_id))
       file_ids = []
       total_files = await message.reply(f"<b><i>🗂 Total files - <code>{len(files)}</code></i></b>")

       for file in files:
        # Safely get caption template
           CAPTION = settings.get('caption', '📁 {file_name}\n💾 {file_size}')
           f_caption = CAPTION.format(
               file_name=file.get('file_name', 'Unknown'),
               file_size=get_size(file.get('file_size', 0)),
               file_caption=file.get('caption', '')
           )

           # Send the file or message here (example)
           sent = await message.reply(f_caption)
           file_ids.append(sent.id)

        
    """if mc.startswith('all'):
        _, grp_id, key = mc.split("_", 2)
        files = temp.FILES.get(key)
        if not files:
            return await message.reply('No Such All Files Exist!')
        settings = await get_settings(int(grp_id))
        file_ids = []
        total_files = await message.reply(f"<b><i>🗂 Total files - <code>{len(files)}</code></i></b>")
        for file in files:
            CAPTION = settings['caption']
            f_caption = CAPTION.format(
                file_name=file['file_name'],
                file_size=get_size(file['file_size']),
                file_caption=file['caption']
            )   """   
            if IS_STREAM:
                btn = [[
                    InlineKeyboardButton("✛ ᴡᴀᴛᴄʜ & ᴅᴏᴡɴʟᴏᴀᴅ ✛", callback_data=f"stream#{file['_id']}")
                ],[
                    InlineKeyboardButton('⚡️ ᴜᴘᴅᴀᴛᴇs', url=UPDATES_LINK),
                    InlineKeyboardButton('💡 ꜱᴜᴘᴘᴏʀᴛ', url=SUPPORT_LINK)
                ],[
                    InlineKeyboardButton('⁉️ ᴄʟᴏsᴇ ⁉️', callback_data='close_data')
                ]]
            else:
                btn = [[
                    InlineKeyboardButton('⚡️ ᴜᴘᴅᴀᴛᴇs', url=UPDATES_LINK),
                    InlineKeyboardButton('💡 ꜱᴜᴘᴘᴏʀᴛ', url=SUPPORT_LINK)
                ],[
                    InlineKeyboardButton('⁉️ ᴄʟᴏsᴇ ⁉️', callback_data='close_data')
                ]]

            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file['_id'],
                caption=f_caption,
                protect_content=False,
                reply_markup=InlineKeyboardMarkup(btn)
            )
            file_ids.append(msg.id)

        time = get_readable_time(PM_FILE_DELETE_TIME)
        vp = await message.reply(
            f"Nᴏᴛᴇ: Tʜɪs ғɪʟᴇs ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇ ɪɴ {time} ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛs. Sᴀᴠᴇ ᴛʜᴇ ғɪʟᴇs ᴛᴏ sᴏᴍᴇᴡʜᴇʀᴇ ᴇʟsᴇ"
        )
        await asyncio.sleep(PM_FILE_DELETE_TIME)
        buttons = [[
            InlineKeyboardButton('ɢᴇᴛ ғɪʟᴇs ᴀɢᴀɪɴ', callback_data=f"get_del_send_all_files#{grp_id}#{key}")
         ]]
        await client.delete_messages(
            chat_id=message.chat.id,
            message_ids=file_ids + [total_files.id]
        )
        await vp.edit(
            "Tʜᴇ ғɪʟᴇ ʜᴀs ʙᴇᴇɴ ɢᴏɴᴇ ! Cʟɪᴄᴋ ɢɪᴠᴇɴ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ɪᴛ ᴀɢᴀɪɴ.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        # ✅ START: safer unpacking of mc
        parts = mc.split("_", 2)
        if len(parts) != 3:
            return await message.reply("⚠️ Invalid file link or broken data. Please try again.")
        type_, grp_id, file_id = parts
        # ✅ END

        files_ = await get_file_details(file_id)
        if not files_:
            return await message.reply('No Such File Exist!')
        files = files_
        settings = await get_settings(int(grp_id))

        if type_ != 'shortlink' and settings['shortlink'] and not await is_premium(message.from_user.id, client):
            link = await get_shortlink(settings['url'], settings['api'], f"https://t.me/{temp.U_NAME}?start=shortlink_{grp_id}_{file_id}")
            btn = [[
                InlineKeyboardButton("♻️ Get File ♻️", url=link)
            ],[
                InlineKeyboardButton("📍 ʜᴏᴡ ᴛᴏ ᴏᴘᴇɴ ʟɪɴᴋ 📍", url=settings['tutorial'])
            ]]
            await message.reply(
                f"[{get_size(files['file_size'])}] {files['file_name']}\n\nYour file is ready, Please get using this link. 👍",
                reply_markup=InlineKeyboardMarkup(btn),
                protect_content=True
            )
            return

    CAPTION = settings['caption']
    f_caption = CAPTION.format(
        file_name = files['file_name'],
        file_size = get_size(files['file_size']),
        file_caption=files['caption']
    )
    if IS_STREAM:
        btn = [[
            InlineKeyboardButton("✛ ᴡᴀᴛᴄʜ & ᴅᴏᴡɴʟᴏᴀᴅ ✛", callback_data=f"stream#{file_id}")
        ],[
            InlineKeyboardButton('⚡️ ᴜᴘᴅᴀᴛᴇs', url=UPDATES_LINK),
            InlineKeyboardButton('💡 ꜱᴜᴘᴘᴏʀᴛ', url=SUPPORT_LINK)
        ],[
            InlineKeyboardButton('⁉️ ᴄʟᴏsᴇ ⁉️', callback_data='close_data')
        ]]
    else:
        btn = [[
            InlineKeyboardButton('⚡️ ᴜᴘᴅᴀᴛᴇs', url=UPDATES_LINK),
            InlineKeyboardButton('💡 ꜱᴜᴘᴘᴏʀᴛ', url=SUPPORT_LINK)
        ],[
            InlineKeyboardButton('⁉️ ᴄʟᴏsᴇ ⁉️', callback_data='close_data')
        ]]
    vp = await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        protect_content=False,
        reply_markup=InlineKeyboardMarkup(btn)
    )
    time = get_readable_time(PM_FILE_DELETE_TIME)
    msg = await vp.reply(f"Nᴏᴛᴇ: Tʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇ ɪɴ {time} ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛs. Sᴀᴠᴇ ᴛʜᴇ ғɪʟᴇ ᴛᴏ sᴏᴍᴇᴡʜᴇʀᴇ ᴇʟsᴇ")
    await asyncio.sleep(PM_FILE_DELETE_TIME)
    btns = [[
        InlineKeyboardButton('ɢᴇᴛ ғɪʟᴇ ᴀɢᴀɪɴ', callback_data=f"get_del_file#{grp_id}#{file_id}")
    ]]
    await msg.delete()
    await vp.delete()
    await vp.reply("Tʜᴇ ғɪʟᴇ ʜᴀs ʙᴇᴇɴ ɢᴏɴᴇ ! Cʟɪᴄᴋ ɢɪᴠᴇɴ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ɪᴛ ᴀɢᴀɪɴ.", reply_markup=InlineKeyboardMarkup(btns))


@Client.on_message(filters.command('link'))
async def link(bot, message):
    msg = message.reply_to_message
    if not msg:
        return await message.reply('Reply to media')
    try:
        media = getattr(msg, msg.media.value)
        msg = await bot.send_cached_media(chat_id=BIN_CHANNEL, file_id=media.file_id)
        watch = f"{URL}watch/{msg.id}"
        download = f"{URL}download/{msg.id}"
        btn=[[
            InlineKeyboardButton("ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ", url=watch),
            InlineKeyboardButton("ꜰᴀsᴛ ᴅᴏᴡɴʟᴏᴀᴅ", url=download)
        ],[
            InlineKeyboardButton('❌ ᴄʟᴏsᴇ ❌', callback_data='close_data')
        ]]
        await message.reply('Here is your link', reply_markup=InlineKeyboardMarkup(btn))
    except:
        await message.reply('Unsupported file')

@Client.on_message(filters.command('index_channels'))
async def channels_info(bot, message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.delete()
        return
    ids = INDEX_CHANNELS
    if not ids:
        return await message.reply("Not set INDEX_CHANNELS")
    text = '**Indexed Channels:**\n\n'
    for id in ids:
        chat = await bot.get_chat(id)
        text += f'{chat.title}\n'
    text += f'\n**Total:** {len(ids)}'
    await message.reply(text)

@Client.on_message(filters.private & filters.command("movie_update") & filters.user(ADMINS))
async def set_movie_update_notification(client, message):
    bot_id = client.me.id
    try:
        option = message.text.split(" ", 1)[1].strip().lower()
        enable_status = option in ['on', 'true']
    except (IndexError, ValueError):
        await message.reply_text("<b>💔 Invalid option. Please send 'on' or 'off' after the command.</b>")
        return
    try:
        await db.update_movie_update_status(bot_id, enable_status)
        response_text = (
            "<b>ᴍᴏᴠɪᴇ ᴜᴘᴅᴀᴛᴇ ɴᴏᴛɪꜰɪᴄᴀᴛɪᴏɴ ᴇɴᴀʙʟᴇᴅ ✅</b>" if enable_status 
            else "<b>ᴍᴏᴠɪᴇ ᴜᴘᴅᴀᴛᴇ ɴᴏᴛɪꜰɪᴄᴀᴛɪᴏɴ ᴅɪꜱᴀʙʟᴇᴅ ❌</b>"
        )
        await message.reply_text(response_text)
    except Exception as e:
        await log_error(client, f"Error in set_movie_update_notification: {e}")
        await message.reply_text(f"<b>❗ An error occurred: {e}</b>")

@Client.on_message(filters.command('stats'))
async def stats(bot, message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.delete()
        return
    files = db_count_documents()
    users = await db.total_users_count()
    chats = await db.total_chat_count()
    prm = db.get_premium_count()
    used_files_db_size = get_size(await db.get_files_db_size())
    used_data_db_size = get_size(await db.get_data_db_size())

    if SECOND_FILES_DATABASE_URL:
        secnd_files_db_used_size = get_size(await db.get_second_files_db_size())
        secnd_files = second_db_count_documents()
    else:
        secnd_files_db_used_size = '-'
        secnd_files = '-'

    uptime = get_readable_time(time_now() - temp.START_TIME)
    await message.reply_text(script.STATUS_TXT.format(users, prm, chats, used_data_db_size, files, used_files_db_size, secnd_files, secnd_files_db_used_size, uptime))    
    


async def get_grp_stg(group_id):
    settings = await get_settings(group_id)
    btn = [[
        InlineKeyboardButton('Edit IMDb template', callback_data=f'imdb_setgs#{group_id}')
    ],[
        InlineKeyboardButton('Edit Shortlink', callback_data=f'shortlink_setgs#{group_id}')
    ],[
        InlineKeyboardButton('Edit File Caption', callback_data=f'caption_setgs#{group_id}')
    ],[
        InlineKeyboardButton('Edit Welcome', callback_data=f'welcome_setgs#{group_id}')
    ],[
        InlineKeyboardButton('Edit tutorial link', callback_data=f'tutorial_setgs#{group_id}')
    ],[
        InlineKeyboardButton(f'IMDb Poster {"✅" if settings["imdb"] else "❌"}', callback_data=f'bool_setgs#imdb#{settings["imdb"]}#{group_id}')
    ],[
        InlineKeyboardButton(f'Spelling Check {"✅" if settings["spell_check"] else "❌"}', callback_data=f'bool_setgs#spell_check#{settings["spell_check"]}#{group_id}')
    ],[
        InlineKeyboardButton(f"Auto Delete - {get_readable_time(DELETE_TIME)}" if settings["auto_delete"] else "Auto Delete ❌", callback_data=f'bool_setgs#auto_delete#{settings["auto_delete"]}#{group_id}')
    ],[
        InlineKeyboardButton(f'Welcome {"✅" if settings["welcome"] else "❌"}', callback_data=f'bool_setgs#welcome#{settings["welcome"]}#{group_id}')
    ],[
        InlineKeyboardButton(f'Shortlink {"✅" if settings["shortlink"] else "❌"}', callback_data=f'bool_setgs#shortlink#{settings["shortlink"]}#{group_id}')
    ],[
        InlineKeyboardButton(f"Result Page - Link" if settings["links"] else "Result Page - Button", callback_data=f'bool_setgs#links#{settings["links"]}#{group_id}')
    ]]
    return btn
    
@Client.on_message(filters.command('settings'))
async def settings(client, message):
    group_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        if not await is_check_admin(client, group_id, message.from_user.id):
            return await message.reply_text('You not admin in this group.')
        btn = [[
            InlineKeyboardButton("Open Here", callback_data='open_group_settings')
        ],[
            InlineKeyboardButton("Open In PM", callback_data='open_pm_settings')
        ]]
        await message.reply_text('Where do you want to open the settings menu?', reply_markup=InlineKeyboardMarkup(btn))
    elif message.chat.type == enums.ChatType.PRIVATE:
        cons = db.get_connections(message.from_user.id)
        if not cons:
            return await message.reply_text("No groups found! Use this command group and open in PM")
        buttons = []
        for con in cons:
            try:
                chat = await client.get_chat(con)
                buttons.append(
                    [InlineKeyboardButton(text=chat.title, callback_data=f'back_setgs#{chat.id}')]
                )
            except:
                pass
        await message.reply_text('Select the group whose settings you want to change.\n\nIf your group not showing here? Use this command in your group and open in PM or send <code>/connect</code> command in your group.', reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_message(filters.command('connect'))
async def connect(client, message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        group_id = message.chat.id
        db.add_connect(group_id, message.from_user.id)
        await message.reply_text('Successfully connected this group to PM, now you can manage your group using /settings inside your PM')
    elif message.chat.type == enums.ChatType.PRIVATE:
        if len(message.command) > 1:
            group_id = message.command[1]
            if not await is_check_admin(client, int(group_id), message.from_user.id):
                return await message.reply_text('You not admin in this group.')
            chat = await client.get_chat(int(group_id))
            db.add_connect(int(group_id), message.from_user.id)
            await message.reply_text(f'Successfully connected {chat.title} group to PM')
        else:
            await message.reply_text('Usage: /connect group_id\nor use /connect in group')


@Client.on_message(filters.command('delete'))
async def delete_file(bot, message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.delete()
        return
    try:
        query = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("Command Incomplete!\nUsage: /delete query")
    btn = [[
        InlineKeyboardButton("YES", callback_data=f"delete_{query}")
    ],[
        InlineKeyboardButton("CLOSE", callback_data="close_data")
    ]]
    await message.reply_text(f"Do you want to delete all: {query} ?", reply_markup=InlineKeyboardMarkup(btn))
 


@Client.on_message(filters.command('img_2_link'))
async def img_2_link(bot, message):
    reply_to_message = message.reply_to_message
    if not reply_to_message:
        return await message.reply('Reply to any photo')
    file = reply_to_message.photo
    if file is None:
        return await message.reply('Invalid media.')
    text = await message.reply_text(text="ᴘʀᴏᴄᴇssɪɴɢ....")   
    path = await reply_to_message.download()  
    response = upload_image(path)
    if not response:
         await text.edit_text(text="Upload failed!")
         return    
    try:
        os.remove(path)
    except:
        pass
    await text.edit_text(f"<b>❤️ Your link ready 👇\n\n{response}</b>", disable_web_page_preview=True)

@Client.on_message(filters.command('ping'))
async def ping(client, message):
    start_time = monotonic()
    msg = await message.reply("👀")
    end_time = monotonic()
    await msg.edit(f'{round((end_time - start_time) * 1000)} ms')
    

@Client.on_message(filters.command('myplan') & filters.private)
async def myplan(client, message):
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled by admin')
    mp = db.get_plan(message.from_user.id)
    if not await is_premium(message.from_user.id, client):
        btn = [[
            InlineKeyboardButton('Activate Trial', callback_data='activate_trial'),
            InlineKeyboardButton('Activate Plan', callback_data='activate_plan')
        ]]
        return await message.reply('You dont have any premium plan, please use /plan to activate plan', reply_markup=InlineKeyboardMarkup(btn))
    await message.reply(f"You activated {mp['plan']} plan\nExpire: {mp['expire'].strftime('%Y.%m.%d %H:%M:%S')}")


@Client.on_message(filters.command('plan') & filters.private)
async def plan(client, message):
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled by admin')
    btn = [[
        InlineKeyboardButton('Activate Trial', callback_data='activate_trial')
    ],[
        InlineKeyboardButton('Activate Plan', callback_data='activate_plan')
    ]]
    await message.reply(script.PLAN_TXT.format(PRE_DAY_AMOUNT, RECEIPT_SEND_USERNAME), reply_markup=InlineKeyboardMarkup(btn))


@Client.on_message(filters.command('add_prm') & filters.user(ADMINS))
async def add_prm(bot, message):
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled')
    try:
        _, user_id, d = message.text.split(' ')
    except:
        return await message.reply('Usage: /add_prm user_id 1d')
    try:
        d = int(d[:-1])
    except:
        return await message.reply('Not valid days, use: 1d, 7d, 30d, 365d, etc...')
    try:
        user = await bot.get_users(user_id)
    except Exception as e:
        return await message.reply(f'Error: {e}')
    if user.id in ADMINS:
        return await message.reply('ADMINS is already premium')
    if not await is_premium(user.id, bot):
        mp = db.get_plan(user.id)
        ex = datetime.now() + timedelta(days=d)
        mp['expire'] = ex
        mp['plan'] = f'{d} days'
        mp['premium'] = True
        db.update_plan(user.id, mp)
        await message.reply(f"Given premium to {user.mention}\nExpire: {ex.strftime('%Y.%m.%d %H:%M:%S')}")
        try:
            await bot.send_message(user.id, f"Your now premium user\nExpire: {ex.strftime('%Y.%m.%d %H:%M:%S')}")
        except:
            pass
    else:
        await message.reply(f"{user.mention} is already premium user")



@Client.on_message(filters.command('rm_prm') & filters.user(ADMINS))
async def rm_prm(bot, message):
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled')
    try:
        _, user_id = message.text.split(' ')
    except:
        return await message.reply('Usage: /rm_prm user_id')
    try:
        user = await bot.get_users(user_id)
    except Exception as e:
        return await message.reply(f'Error: {e}')
    if user.id in ADMINS:
        return await message.reply('ADMINS is already premium')
    if not await is_premium(user.id, bot):
        await message.reply(f"{user.mention} is not premium user")
    else:
        mp = db.get_plan(user.id)
        mp['expire'] = ''
        mp['plan'] = ''
        mp['premium'] = False
        db.update_plan(user.id, mp)
        await message.reply(f"{user.mention} is no longer premium user")
        try:
            await bot.send_message(user.id, "Your premium plan was removed by admin")
        except:
            pass


@Client.on_message(filters.command('prm_list') & filters.user(ADMINS))
async def prm_list(bot, message):
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled')
    tx = await message.reply('Getting list of premium users')
    pr = [i['id'] for i in db.get_premium_users() if i['status']['premium']]
    t = 'premium users saved in database are:\n\n'
    for p in pr:
        try:
            u = await bot.get_users(p)
            t += f"{u.mention} : {p}\n"
        except:
            t += f"{p}\n"
    await tx.edit_text(t)


@Client.on_message(filters.command('set_fsub') & filters.user(ADMINS))
async def set_fsub(bot, message):
    try:
        _, ids = message.text.split(' ', 1)
    except ValueError:
        return await message.reply('usage: /set_fsub -100xxx -100xxx')
    title = ""
    for id in ids.split(' '):
        try:
            chat = await bot.get_chat(int(id))
            title += f'{chat.title}\n'
        except Exception as e:
            return await message.reply(f'ERROR: {e}')
    db.update_bot_sttgs('FORCE_SUB_CHANNELS', ids)
    await message.reply(f'added force subscribe channels: {title}')

        

@Client.on_message(filters.command('set_req_fsub') & filters.user(ADMINS))
async def set_req_fsub(bot, message):
    try:
        _, id = message.text.split(' ', 1)
    except ValueError:
        return await message.reply('usage: /set_req_fsub -100xxx')
    try:
        chat = await bot.get_chat(int(id))
    except Exception as e:
        return await message.reply(f'ERROR: {e}')
    db.update_bot_sttgs('REQUEST_FORCE_SUB_CHANNELS', id)
    await message.reply(f'added request force subscribe channel: {chat.title}')


@Client.on_message(filters.command('off_auto_filter') & filters.user(ADMINS))
async def off_auto_filter(bot, message):
    db.update_bot_sttgs('AUTO_FILTER', False)
    await message.reply('Successfully turned off auto filter for all groups')


@Client.on_message(filters.command('on_auto_filter') & filters.user(ADMINS))
async def on_auto_filter(bot, message):
    db.update_bot_sttgs('AUTO_FILTER', True)
    await message.reply('Successfully turned on auto filter for all groups')



@Client.on_message(filters.command('off_pm_search') & filters.user(ADMINS))
async def off_pm_search(bot, message):
    db.update_bot_sttgs('PM_SEARCH', False)
    await message.reply('Successfully turned off pm search for all users')


@Client.on_message(filters.command('on_pm_search') & filters.user(ADMINS))
async def on_pm_search(bot, message):
    db.update_bot_sttgs('PM_SEARCH', True)
    await message.reply('Successfully turned on pm search for all users')

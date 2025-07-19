import logging
from struct import pack
import re
import base64
from hydrogram.file_id import FileId
from pymongo import MongoClient, TEXT
from pymongo.errors import DuplicateKeyError, OperationFailure
from info import USE_CAPTION_FILTER, FILES_DATABASE_URL, SECOND_FILES_DATABASE_URL, DATABASE_NAME, COLLECTION_NAME, MAX_BTN, UPDATES_LINK, CAPTION_LANGUAGES, OWNERID
from utils import get_status, get_poster

logger = logging.getLogger(__name__)

client = MongoClient(FILES_DATABASE_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]
try:
    collection.create_index([("file_name", TEXT)])
except OperationFailure as e:
    if 'quota' in str(e).lower():
        if not SECOND_FILES_DATABASE_URL:
            logger.error(f'your FILES_DATABASE_URL is already full, add SECOND_FILES_DATABASE_URL')
        else:
            logger.info('FILES_DATABASE_URL is full, now using SECOND_FILES_DATABASE_URL')
    else:
        logger.exception(e)

if SECOND_FILES_DATABASE_URL:
    second_client = MongoClient(SECOND_FILES_DATABASE_URL)
    second_db = second_client[DATABASE_NAME]
    second_collection = second_db[COLLECTION_NAME]
    second_collection.create_index([("file_name", TEXT)])


def second_db_count_documents():
     return second_collection.count_documents({})

def db_count_documents():
     return collection.count_documents({})
    
async def add_name(user_id, filename):
    user_db = db[str(user_id)]
    user = {'_id': filename}
    existing_user = user_db.find_one({'_id': filename})
    if existing_user is not None:
        return False
    try:
        user_db.insert_one(user)
        return True
    except DuplicateKeyError:
        return False

async def save_file(media, bot=None):
    """Save file in database"""
    file_id = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name or "Unnamed"))
    file_caption = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.caption or ""))

    document = {
        '_id': file_id,
        'file_name': file_name,
        'file_size': media.file_size,
        'caption': file_caption
    }

    try:
        collection.insert_one(document)
        logger.info(f'Saved - {file_name}')

        # ✅ Send update if enabled
        if bot and await get_status(bot.me.id):
            await send_msg(bot, file_name, file_caption)

        return 'suc'

    except DuplicateKeyError:
        logger.warning(f'Already Saved - {file_name}')

        # ✅ Still send update if enabled
        if bot and await get_status(bot.me.id):
            await send_msg(bot, file_name, file_caption)

        return 'dup'

    except OperationFailure:
        if SECOND_FILES_DATABASE_URL:
            try:
                second_collection.insert_one(document)
                logger.info(f'Saved to 2nd db - {file_name}')

                # ✅ Send update if enabled
                if bot and await get_status(bot.me.id):
                    await send_msg(bot, file_name, file_caption)

                return 'suc'
            except DuplicateKeyError:
                logger.warning(f'Already Saved in 2nd db - {file_name}')

                # ✅ Send update if enabled
                if bot and await get_status(bot.me.id):
                    await send_msg(bot, file_name, file_caption)

                return 'dup'

        logger.error('FILES_DATABASE_URL is full. Please set SECOND_FILES_DATABASE_URL.')

        # ✅ Final fallback update
        if bot and await get_status(bot.me.id):
            await send_msg(bot, file_name, file_caption)

        return 'err'

async def get_search_results(query, max_results=MAX_BTN, offset=0, lang=None):
    query = str(query).strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query

    if USE_CAPTION_FILTER:
        filter = {'$or': [{'file_name': regex}, {'caption': regex}]}
    else:
        filter = {'file_name': regex}

    cursor = collection.find(filter)
    results = [doc for doc in cursor]

    if SECOND_FILES_DATABASE_URL:
        cursor2 = second_collection.find(filter)
        results.extend([doc for doc in cursor2])

    if lang:
        lang_files = [file for file in results if lang in file['file_name'].lower()]
        files = lang_files[offset:][:max_results]
        total_results = len(lang_files)
        next_offset = offset + max_results
        if next_offset >= total_results:
            next_offset = ''
        return files, next_offset, total_results

    total_results = len(results)
    files = results[offset:][:max_results]
    next_offset = offset + max_results
    if next_offset >= total_results:
        next_offset = ''   
    return files, next_offset, total_results

async def delete_files(query):
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        regex = query
        
    filter = {'file_name': regex}
    
    result1 = collection.delete_many(filter)
    
    result2 = None
    if SECOND_FILES_DATABASE_URL:
        result2 = second_collection.delete_many(filter)
    
    total_deleted = result1.deleted_count
    if result2:
        total_deleted += result2.deleted_count
    
    return total_deleted

async def get_file_details(query):
    file_details = collection.find_one({'_id': query})
    if not file_details and SECOND_FILES_DATABASE_URL:
        file_details = second_collection.find_one({'_id': query})
    return file_details

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    return file_id

async def send_msg(bot, filename, caption):
    try:
        filename = re.sub(r'\(\@\S+\)|\[\@\S+\]|\b@\S+|\bwww\.\S+', '', filename).strip()
        caption = re.sub(r'\(\@\S+\)|\[\@\S+\]|\b@\S+|\bwww\.\S+', '', caption).strip()
        
        year_match = re.search(r"\b(19|20)\d{2}\b", caption)
        year = year_match.group(0) if year_match else None

        pattern = r"(?i)(?:s|season)0*(\d{1,2})"
        season = re.search(pattern, caption) or re.search(pattern, filename)
        season = season.group(1) if season else None

        if year:
            filename = filename[: filename.find(year) + 4]
        elif season and season in filename:
            filename = filename[: filename.find(season) + 1]

        qualities = ["ORG", "org", "hdcam", "HDCAM", "HQ", "hq", "HDRip", "hdrip", "camrip", "CAMRip", "hdtc", "predvd", "DVDscr", "dvdscr", "dvdrip", "dvdscr", "HDTC", "dvdscreen", "HDTS", "hdts"]
        quality = await get_qualities(caption.lower(), qualities) or "HDRip"

        language = ""
        possible_languages = CAPTION_LANGUAGES
        for lang in possible_languages:
            if lang.lower() in caption.lower():
                language += f"{lang}, "
        language = language[:-2] if language else "Not idea 😄"

        filename = re.sub(r"[\(\)\[\]\{\}:;'\-!]", "", filename)

        text = "#𝑵𝒆𝒘_𝑭𝒊𝒍𝒆_𝑨𝒅𝒅𝒆𝒅 ✅\n\n👷𝑵𝒂𝒎𝒆: `{}`\n\n🌳𝑸𝒖𝒂𝒍𝒊𝒕𝒚: {}\n\n🍁𝑨𝒖𝒅𝒊𝒐: {}"
        text = text.format(filename, quality, language)

        if await add_name(OWNERID, filename):
            imdb = await get_poster(filename)
            resized_poster = None

            if imdb:
                poster_url = imdb.get('poster_url')
                if poster_url:
                    resized_poster = await fetch_image(poster_url)

            filenames = filename.replace(" ", '-')
            btn = [[InlineKeyboardButton('🌲 Get Files 🌲', url=f"https://telegram.me/{temp.U_NAME}?start=getfile-{filenames}")]]
            
            if resized_poster:
                await bot.send_photo(chat_id=UPDATES_LINK, photo=resized_poster, caption=text, reply_markup=InlineKeyboardMarkup(btn))
            else:
                await bot.send_message(chat_id=UPDATES_LINK, text=text, reply_markup=InlineKeyboardMarkup(btn))

    except Exception as e:
        logger.error(f"❌ Error in send_msg(): {e}")
        
async def get_qualities(text, qualities: list):
    """Get all Quality from text"""
    quality = []
    for q in qualities:
        if q in text:
            quality.append(q)
    quality = ", ".join(quality)
    return quality[:-2] if quality.endswith(", ") else quality

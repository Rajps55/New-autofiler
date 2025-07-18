from hydrogram import Client, filters
from info import INDEX_CHANNELS, INDEX_EXTENSIONS
from database.ia_filterdb import save_file

media_filter = filters.document | filters.video

@Client.on_message(filters.chat(INDEX_CHANNELS) & media_filter)
async def media(bot, message):
    """Media Handler"""

    # Get document or video object
    media = message.document or message.video
    if not media:
        return  # No valid media

    # Check file extension
    if str(media.file_name or "").lower().endswith(tuple(INDEX_EXTENSIONS)):
        media.caption = message.caption
        await save_file(media, bot=bot)

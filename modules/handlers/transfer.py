"""
:project: telegram-onedrive
:author: L-ING
:copyright: (C) 2023 L-ING <hlf01@icloud.com>
:license: MIT, see LICENSE for more details.
"""

from telethon import events
from telethon.tl import types
import os
from modules.client import tg_bot, tg_client, onedrive
from modules.env import tg_user_name
from modules.utils import (
    Callback,
    Status_Message,
    check_in_group,
    check_tg_login,
    check_od_login,
    get_link,
)
from modules.log import logger
from modules.transfer import multi_parts_uploader
from modules.onedrive.utils import preprocess_tg_file_name, use_id_ext_name
from modules.dot_t2o import parse_t2o


@tg_bot.on(events.NewMessage(incoming=True, from_users=tg_user_name))
@check_in_group
@check_tg_login
@check_od_login
async def transfer_handler(event):
    last_remote_root_path = onedrive.remote_root_path
    if event.media and not isinstance(event.media, types.MessageMediaWebPage):
        message = await tg_client.get_messages(
            event.message.peer_id, ids=event.message.id
        )

        try:
            if "document" in event.media.to_dict():
                name = preprocess_tg_file_name(event)

                if not name.endswith(".t2o"):
                    status_message = await Status_Message.create(event)
                    callback = Callback(event, status_message)
                    response_dict = await multi_parts_uploader(
                        message.media.document, name, progress_callback=callback
                    )
                    await status_message.finish(
                        path=os.path.join(last_remote_root_path, response_dict["name"]),
                        size=event.file.size,
                    )
                else:
                    await parse_t2o(event, message)
            elif "photo" in event.media.to_dict():
                name = use_id_ext_name(event)
                status_message = await Status_Message.create(event)
                callback = Callback(event, status_message)
                buffer = await message.download_media(
                    file=bytes, progress_callback=callback
                )
                onedrive.stream_upload(buffer, name)
                await status_message.finish(
                    path=os.path.join(last_remote_root_path, name), size=event.file.size
                )
        except KeyError as e:
            await event.reply(logger("Error: %s\nresponse: %s" % (e, response_dict)))
        except Exception as e:
            await event.reply("Error: %s" % logger(e))

    else:
        msg_link = get_link(event.text)
        if msg_link:
            try:
                chat = ""
                if "?single" in msg_link:
                    msg_link = msg_link.split("?single")[0]
                msg_id = int(msg_link.split("/")[-1])
                if "t.me/" in msg_link:
                    if "t.me/c/" in msg_link:
                        chat = int("-100" + str(msg_link.split("/")[-2]))
                    else:
                        chat = str(msg_link.split("/")[-2])
                else:
                    raise Exception("Not message link")

                message = await tg_client.get_messages(chat, ids=msg_id)
            except:
                logger("Not message link.")
                await event.reply(
                    "Please offer a message link.\n\nUse /help for available command."
                )
                raise events.StopPropagation

            if message:
                try:
                    if "document" in message.media.to_dict():
                        name = preprocess_tg_file_name(message)
                        status_message = await Status_Message.create(event)
                        callback = Callback(event, status_message)
                        response_dict = await multi_parts_uploader(
                            message.media.document,
                            name,
                            progress_callback=callback,
                        )
                        await status_message.finish(
                            path=os.path.join(
                                last_remote_root_path, response_dict["name"]
                            ),
                            size=message.file.size,
                        )
                    elif "photo" in message.media.to_dict():
                        name = use_id_ext_name(message)
                        status_message = await Status_Message.create(event)
                        callback = Callback(event, status_message)
                        buffer = await message.download_media(
                            file=bytes, progress_callback=callback
                        )
                        onedrive.stream_upload(buffer, name)
                        await status_message.finish(
                            path=os.path.join(last_remote_root_path, name),
                            size=message.file.size,
                        )
                except KeyError as e:
                    await event.reply(
                        logger("Error: %s\nresponse: %s" % (e, response_dict))
                    )
                except Exception as e:
                    await event.reply("Error: %s" % logger(e))
            else:
                await event.reply(logger("Message not found."))
        else:
            logger("Unknown command.")
            await event.reply("Use /help for available command.")
    onedrive.check_dir_temp()
    raise events.StopPropagation

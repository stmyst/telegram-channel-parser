import asyncio
import os
import time
from collections import defaultdict
from datetime import datetime

import pandas as pd
from telethon import TelegramClient
from telethon.tl.patched import Message
from telethon.tl.types import MessageMediaPhoto

# config parameters
CHANNEL = '@tg_channel_to_parse'
START_DATE = datetime(year=2018, month=1, day=1)
END_DATE = datetime(year=2025, month=12, day=31)


async def main(
    channel: str, api_id: int, api_hash: str, start_date:datetime, end_date: datetime,
) -> None:

    messages = []
    albums = defaultdict(list)
    ch_name = channel[1:] if channel.startswith('@') else os.path.basename(channel)

    async with TelegramClient(session='session', api_id=api_id, api_hash=api_hash) as client:
        print(f'parsing {channel}')
        async for message in client.iter_messages(channel):
            message.date = message.date.replace(tzinfo=None)
            if message.date < start_date:
                break
            if message.date > end_date:
                continue

            if message.grouped_id is None:
                messages.append(_process_message(message=message, ch_name=ch_name))
            else:
                albums[message.grouped_id].append(message)

            # wait time to meet API restrictions
            await asyncio.sleep(0.1)

        # albums processing
    for album in albums.values():
        messages.append(_process_album(album=album, ch_name=ch_name))

    # Сохранение результатов
    (pd.DataFrame(messages)
        .sort_values(by='Date', ascending=False)
        .to_excel(excel_writer=f'{ch_name}.xlsx', index=False)
    )

def _post_type(message: Message) -> str:
    if message.poll:
        return 'Poll'
    if message.text:
        return 'Text'
    if isinstance(message.media, MessageMediaPhoto):
        return 'Photo'
    return 'Other'

def _process_message(message: Message, ch_name: str) -> dict:
    views = 0 if message.views is None else message.views
    comments = 0 if message.replies is None else message.replies.replies
    forwards = 0 if message.forwards is None else message.forwards
    if message.reactions is None:
        reactions = 0
    else:
        reactions = sum(reaction.count for reaction in message.reactions.results)

    return {
        'Type': _post_type(message=message),
        'Date': message.date,
        'Text': message.text or '',
        'Link': f'https://t.me/{ch_name}/{message.id}',
        'Views': views,
        'Comments': comments,
        'Forwards': forwards,
        'Reactions': reactions,
        'ER': round(reactions + comments + forwards / views * 100, 2) if views else 0
    }

def _process_album(album: list[Message], ch_name: str) -> dict:
    first_message = album[0]
    views = 0 if first_message.views is None else first_message.views
    comments = sum(0 if m.replies is None else m.replies.replies for m in album)
    forwards = sum(0 if m.forwards is None else m.forwards for m in album)
    reactions = 0
    for message in album:
        if message.reactions is None:
            continue
        reactions += sum(reaction.count for reaction in message.reactions.results)

    return {
        'Type': 'Album',
        'Date': first_message.date,
        'Text': ' '.join(m.text or '' for m in album),
        'Link': f'https://t.me/{ch_name}/{first_message.id}',
        'Views': views,
        'Comments': comments,
        'Forwards': forwards,
        'Reactions': reactions,
        'ER': round(reactions + comments + forwards / views * 100, 2) if views else 0
    }


if __name__ == "__main__":
    from dotenv import load_dotenv, find_dotenv

    async def run():
        start_time = time.time()
        load_dotenv(find_dotenv())

        try:
            await main(
                channel=CHANNEL,
                api_id=int(os.environ.get('API_ID')),
                api_hash=os.environ.get('API_HASH'),
                start_date=START_DATE,
                end_date=END_DATE,
            )
        finally:
            print('elapsed {time:.4} sec'.format(time=time.time() - start_time))

    asyncio.run(run())






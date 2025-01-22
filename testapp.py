import aiohttp
import asyncio
import json

API_TOKEN = "a4f681db-d2e4-466e-b7fe-cddb98763b98"

async def fetch_player_rewards(player_id, game_id="cs2"):
    url = f"https://open.faceit.com/data/v4/players/{player_id}/stats/{game_id}"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Ошибка: {response.status}")
                return None

async def main():
    player_id = "e89b98d2-c3f8-4fb3-bd15-3accb4f5b8d1"  # ID игрока
    data = await fetch_player_rewards(player_id)
    
    if data:
        # Выводим данные о наградах и значках
        print(json.dumps(data, indent=4, ensure_ascii=False))

asyncio.run(main())

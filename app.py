from flask import Flask, render_template, request
import aiohttp
import asyncio
import math
from dotenv import load_dotenv
import os

app = Flask(__name__)
load_dotenv()

API_TOKEN = os.environ.get("API_TOKEN")


async def fetch(url, session):
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    async with session.get(url, headers=headers) as response:
        if response.status != 200:
            print(f"Ошибка при запросе: {url}, статус: {response.status}")
        return await response.json()


async def get_player_id(nickname, session):
    player_url = f"https://open.faceit.com/data/v4/players?nickname={nickname}"
    data = await fetch(player_url, session)
    if not data:
        print(f"Ошибка: не найден игрок с ником {nickname}")
    return data.get("player_id")


async def get_player_elo(nickname, session):
    player_url = f"https://open.faceit.com/data/v4/players?nickname={nickname}"
    data = await fetch(player_url, session)
    if not data:
        print(f"Ошибка: данные игрока {nickname} не найдены.")
        return 0

    elo = data.get("games", {}).get("cs2", {}).get("faceit_elo")
    if elo is None:
        print(f"ELO для игрока {nickname} не найдено.")
        return 0
    return elo


async def get_match_stats(match_id, player_id, session):
    match_stats_url = f"https://open.faceit.com/data/v4/matches/{match_id}/stats"
    match_data = await fetch(match_stats_url, session)

    for team in match_data.get("rounds", [])[0].get("teams", []):
        for player in team.get("players", []):
            if player.get("player_id") == player_id:
                stats = player.get("player_stats", {})
                return {
                    "kills": int(stats.get("Kills", 0)),
                    "deaths": int(stats.get("Deaths", 0)),
                    "headshots": int(stats.get("Headshots", 0)),
                    "kd_ratio": float(stats.get("K/D Ratio", 0.0)),
                    "ace": int(stats.get("Penta Kills", 0)),
                    "knife_kills": int(stats.get("Knife Kills", 0)),
                }
    return None


async def get_last_matches_stats(player_id, session, limit=20):
    matches_url = f"https://open.faceit.com/data/v4/players/{player_id}/history?game=cs2&limit={limit}"
    match_data = await fetch(matches_url, session)
    matches = match_data.get("items", [])

    tasks = []
    for match in matches:
        match_id = match.get("match_id")
        task = asyncio.create_task(get_match_stats(match_id, player_id, session))
        tasks.append(task)

    match_stats = await asyncio.gather(*tasks)
    return [stats for stats in match_stats if stats]


async def get_player_rank(player_id, session, region="EU", game_id="cs2"):
    ranking_url = f"https://open.faceit.com/data/v4/rankings/games/{game_id}/regions/{region}/players/{player_id}"
    ranking_data = await fetch(ranking_url, session)
    return ranking_data.get("position")


def calculate_averages(matches_stats):
    total_kills = sum([match["kills"] for match in matches_stats])
    total_deaths = sum([match["deaths"] for match in matches_stats])
    total_headshots = sum([match["headshots"] for match in matches_stats])
    total_kd_ratio = sum([match["kd_ratio"] for match in matches_stats])

    avg_kills = total_kills / len(matches_stats) if len(matches_stats) > 0 else 0
    avg_kd = total_kd_ratio / len(matches_stats) if len(matches_stats) > 0 else 0
    avg_hs = (total_headshots / total_kills) * 100 if total_kills > 0 else 0

    return avg_kills, avg_hs, avg_kd


async def get_player_stats(nickname, region="EU"):
    async with aiohttp.ClientSession() as session:
        player_id = await get_player_id(nickname, session)
        if not player_id:
            print(f"Игрок с ником {nickname} не найден.")
            return None

        matches_stats = await get_last_matches_stats(player_id, session, limit=20)
        if not matches_stats:
            print(f"Не удалось получить статистику матчей для игрока {nickname}.")
            return None

        avg_kills, avg_hs, avg_kd = calculate_averages(matches_stats)

        elo = await get_player_elo(nickname, session)
        rank = await get_player_rank(player_id, session, region=region)

        ace = sum([match["ace"] for match in matches_stats])
        knife_kills = sum([match["knife_kills"] for match in matches_stats])

        return {
            "nickname": nickname,
            "elo": elo,
            "avg_kills": round(avg_kills),
            "kd_ratio": round(avg_kd, 2),
            "hs_percentage": math.ceil(avg_hs),
            "rank": rank,
            "region": region,
            "ace": ace,
            "knife_kills": knife_kills,
        }


@app.route("/", methods=["GET", "POST"])
def index():
    player_stats = None
    if request.method == "POST":
        nickname = request.form.get("nickname")
        region = request.form.get("region", "EU")
        if nickname:
            player_stats = asyncio.run(get_player_stats(nickname, region=region))

    return render_template("index.html", stats=player_stats)


@app.route("/obs/<nickname>/<region>")
def obs_view(nickname, region):
    player_stats = asyncio.run(get_player_stats(nickname, region=region))
    if not player_stats:
        return "Player not found", 404

    return render_template("obs.html", stats=player_stats)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

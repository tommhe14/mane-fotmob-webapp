import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import aiohttp
import asyncio

st.title("DisBall Web-App")
st.subheader("Select a match below!")

def draw_pitch(ax=None):
    pitch_length = 105
    pitch_width = 68

    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 7))

    plt.plot([0, 0, pitch_length, pitch_length, 0], [0, pitch_width, pitch_width, 0, 0], color="black")
    plt.plot([16.5, 16.5, 0, 0, 16.5], [pitch_width - 16.5, 16.5, 16.5, pitch_width - 16.5, pitch_width - 16.5], color="black")
    plt.plot([pitch_length, pitch_length, pitch_length - 16.5, pitch_length - 16.5, pitch_length], [pitch_width - 16.5, 16.5, 16.5, pitch_width - 16.5, pitch_width - 16.5], color="black")
    plt.plot([5.5, 5.5, 0, 0, 5.5], [pitch_width / 2 + 5.5, pitch_width / 2 - 5.5, pitch_width / 2 - 5.5, pitch_width / 2 + 5.5, pitch_width / 2 + 5.5], color="black")
    plt.plot([pitch_length, pitch_length, pitch_length - 5.5, pitch_length - 5.5, pitch_length], [pitch_width / 2 + 5.5, pitch_width / 2 - 5.5, pitch_width / 2 - 5.5, pitch_width / 2 + 5.5, pitch_width / 2 + 5.5], color="black")

    centre_circle = plt.Circle((pitch_length / 2, pitch_width / 2), 9.15, color="black", fill=False)
    centre_spot = plt.Circle((pitch_length / 2, pitch_width / 2), 0.8, color="black")
    ax.add_patch(centre_circle)
    ax.add_patch(centre_spot)

    left_pen_spot = plt.Circle((11, pitch_width / 2), 0.8, color="black")
    right_pen_spot = plt.Circle((pitch_length - 11, pitch_width / 2), 0.8, color="black")
    ax.add_patch(left_pen_spot)
    ax.add_patch(right_pen_spot)

    left_arc = patches.Arc((11, pitch_width / 2), height=18.3, width=18.3, angle=0, theta1=308, theta2=52, color="black")
    right_arc = patches.Arc((pitch_length - 11, pitch_width / 2), height=18.3, width=18.3, angle=0, theta1=128, theta2=232, color="black")
    ax.add_patch(left_arc)
    ax.add_patch(right_arc)

    plt.xlim(-5, pitch_length + 5)
    plt.ylim(-5, pitch_width + 5)
    ax.set_facecolor("white")
    ax.axis('off')

    return ax

def scale_coordinates(x, y, pitch_length=105, pitch_width=68):
    return (x * pitch_length / 105, y * pitch_width / 68)

async def fetch_and_plot_match(match_id):
    url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()

    if not data or "header" not in data or "events" not in data["header"]:
        return None, None, None, None

    home_team_name = data["header"]["teams"][0]["name"]
    away_team_name = data["header"]["teams"][1]["name"]

    home_team_id = data["header"]["teams"][0]["id"]
    away_team_id = data["header"]["teams"][1]["id"]

    score = data["header"]["status"].get("scoreStr", "Not Started")
    game_status = data["header"]["status"].get("reason", {}).get("long", "N/A")

    home_team_color = '#FFA500'  # Orange
    away_team_color = '#90EE90'  # Light green

    shots = data["content"]["shotmap"]["shots"]

    fig, ax = plt.subplots(figsize=(10, 7))
    ax = draw_pitch(ax)

    for shot in shots:
        x, y = scale_coordinates(shot['x'], shot['y'])
    
        if shot.get('teamId') == home_team_id:
            team_color = home_team_color
        elif shot.get('teamId') == away_team_id:
            team_color = away_team_color
        else:
            team_color = '#000000'  
        
        if shot['eventType'] in ["Goal", "Own Goal"]:
            ax.scatter(x, y, c=team_color, s=500 * shot.get('expectedGoals', 0.1), marker='o', edgecolors='none')  # Filled circle
        else:
            ax.scatter(x, y, facecolors='none', edgecolors=team_color, s=500 * shot.get('expectedGoals', 0.1), marker='o')  # Hollow circle

    ax.set_title(f"{home_team_name} {score} {away_team_name} - {game_status}")

    handles = [
        plt.Line2D([0], [0], color=home_team_color, marker='o', linestyle='', markersize=10),
        plt.Line2D([0], [0], color=away_team_color, marker='o', linestyle='', markersize=10)
    ]
    labels = [home_team_name, away_team_name]
    ax.legend(handles, labels, loc='upper right')

    return fig, ax, home_team_name, away_team_name

async def get_lineup_ratings(match_id):
    url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()

    player_stats = data.get("content", {}).get("playerStats", {})

    ratings = {"home": [], "away": []}

    home_team = data.get("content", {}).get("lineup", {}).get("homeTeam", {})
    away_team = data.get("content", {}).get("lineup", {}).get("awayTeam", {})

    home_lineup = home_team.get("starters", [])
    away_lineup = away_team.get("starters", [])

    def get_fotmob_rating(player_id):
        if player_stats:
            player_info = player_stats.get(player_id, None)
        else:
            return "No Rating"
        
        if not player_info:
            return "No Rating"

        for stat_category in player_info.get("stats", []):
            if "FotMob rating" in stat_category.get("stats", {}):
                return stat_category["stats"]["FotMob rating"].get("stat", {}).get("value", "No Rating")
        
        return "No Rating" 

    for player in home_lineup:
        player_id = str(player.get("id"))
        player_name = player.get("name", "Unknown Player")
        fotmob_rating = get_fotmob_rating(player_id)
        ratings["home"].append({"name": player_name, "FotMob Rating": fotmob_rating})

    for player in away_lineup:
        player_id = str(player.get("id"))
        player_name = player.get("name", "Unknown Player")
        fotmob_rating = get_fotmob_rating(player_id)
        ratings["away"].append({"name": player_name, "FotMob Rating": fotmob_rating})

    return ratings


def rating_to_color(rating):
    try:
        value = float(rating)
        if value >= 9.0:
            return '#8A2BE2'  # BlueViolet
        elif 7.0 <= value < 9.0:
            return '#00FF00'  # LimeGreen
        elif 6.0 <= value < 7.0:
            return '#FFA500'  # Orange
        elif value < 6.0:
            return '#FF0000'  # Red
    except ValueError:
        return '#000000'  # Black for no rating

async def fetch_fixtures():
    url = f"https://www.fotmob.com/api/matches?"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def main():
    st.write("Fetching match data...")

    fixtures = await fetch_fixtures()

    matches = {f"{fix['home']['longName']} vs {fix['away']['longName']}": fix['id'] for league in fixtures['leagues'] for fix in league['matches']}

    selected_match = st.selectbox("Select a match", list(matches.keys()))
    match_id = matches[selected_match]

    fig, ax, home_team_name, away_team_name = await fetch_and_plot_match(match_id)
    if fig:
        st.pyplot(fig)


        ratings = await get_lineup_ratings(match_id)

        st.subheader("Player Ratings")

        for team_name, players in ratings.items():
            st.write(f"**{home_team_name if team_name == 'home' else away_team_name}**")
            cols = st.columns(len(players))
            for col, player in zip(cols, players):
                player_name = player["name"]
                player_rating = player["FotMob Rating"]
                color = rating_to_color(player_rating)
                col.write(f"{player_name} - {player_rating}")
                col.markdown(f'<div style="background-color:{color}; color: white; padding: 5px; text-align: center;">{player_rating}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    asyncio.run(main())

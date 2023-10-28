import discord
from discord.ext import commands, tasks
import sqlite3
import time

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)


TOKEN = 'MTE2NTIwOTMzNDY4NzQ2OTYwOQ.G16Jlt.f0rruexhbypwNwl-_41G8d8yoaOLGgY4nAydlk'

user_points = {}

conn = sqlite3.connect('leaderboard.db')
cursor = conn.cursor()


cursor.execute('''CREATE TABLE IF NOT EXISTS leaderboard (
                    user_id INTEGER PRIMARY KEY,
                    points INTEGER
                )''')
conn.commit()

leaderboard_channel_id = 1165243752617619476
awarding_role_name = "Owner"
award_emoji = "🍪" 

last_update_time = time.time()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    update_leaderboard.start()

@bot.tree.command(name="plusiņi", description="Ievadiet plusiņus šim lietotājam")
async def plusini(interaction: discord.Interaction, user: discord.Member, points: int):
    awarding_member = interaction.user

    awarding_role = discord.utils.get(awarding_member.roles, name=awarding_role_name)

    if not awarding_role:
        await interaction.response.send_message("You don't have the role.")
        return

    mentioned_user = user

    if mentioned_user == awarding_member:
        await interaction.response.send_message("Jūs sev nevarat dot plusiņus!")
    else:
        if points <= 0:
            await interaction.response.send_message("Ievadiet pozitīvu skaitli!")
            return

        cursor.execute("INSERT OR IGNORE INTO leaderboard (user_id, points) VALUES (?, 0)", (mentioned_user.id,))
        cursor.execute("UPDATE leaderboard SET points = points + ? WHERE user_id = ?", (points, mentioned_user.id))
        conn.commit()

        user_points[mentioned_user.id] = user_points.get(mentioned_user.id, 0) + points

        await interaction.response.send_message(f'{points} plusiņš(i) tiek iedots(i): {mentioned_user.mention}. Šim lietotājam tagad ir: {user_points[mentioned_user.id]} plusiņi.')

@bot.tree.command(name="mīnusiņi", description="Ievadiet mīnusiņus šim lietotājam")
async def minusini(interaction: discord.Interaction, user: discord.Member, points: int):
    awarding_member = interaction.user

    awarding_role = discord.utils.get(awarding_member.roles, name=awarding_role_name)

    if not awarding_role:
        await interaction.response.send_message("You don't have the role.")
        return

    mentioned_user = user

    if mentioned_user == awarding_member:
        await interaction.response.send_message("Jūs sev nevarat noņemt mīnusiņus!")
    else:
        if points <= 0:
            await interaction.response.send_message("Ievadiet pozitīvu atņemamo mīnusiņu skaitu.")
            return

        cursor.execute("INSERT OR IGNORE INTO leaderboard (user_id, points) VALUES (?, 0)", (mentioned_user.id,))
        cursor.execute("UPDATE leaderboard SET points = points - ? * 3 WHERE user_id = ?", (points, mentioned_user.id))
        conn.commit()

        cursor.execute("SELECT points FROM leaderboard WHERE user_id = ?", (mentioned_user.id,))
        updated_points = cursor.fetchone()[0]


        points_message = f'{updated_points} plusiņi' if updated_points >= 0 else f'{updated_points} plusiņi'

        await interaction.response.send_message(f'{points} mīnusiņš(i) tiek iedots(i): {mentioned_user.mention}. Šim lietotājam tagad ir: {points_message}.')


@bot.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name == award_emoji:
        user_id = payload.user_id
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(user_id)

        awarding_role = discord.utils.get(member.roles, name=awarding_role_name)

        if awarding_role:
            channel = bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)

            author_id = message.author.id
            cursor.execute("INSERT OR IGNORE INTO leaderboard (user_id, points) VALUES (?, 0)", (author_id,))
            cursor.execute("UPDATE leaderboard SET points = points + 1 WHERE user_id = ?", (author_id,))
            conn.commit()

            user_points[author_id] = user_points.get(author_id, 0) + 1

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.emoji.name == award_emoji:
        user_id = payload.user_id
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(user_id)

        awarding_role = discord.utils.get(member.roles, name=awarding_role_name)

        if awarding_role:
            channel = bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)

            author_id = message.author.id
            cursor.execute("INSERT OR IGNORE INTO leaderboard (user_id, points) VALUES (?, 0)", (author_id,))
            cursor.execute("UPDATE leaderboard SET points = points - 1 WHERE user_id = ?", (author_id,))
            conn.commit()

            user_points[author_id] = max(0, user_points.get(author_id, 0) - 1)

def create_leaderboard_embed():
    global last_update_time  
    cursor.execute("SELECT user_id, points FROM leaderboard ORDER BY points DESC")
    leaderboard_data = cursor.fetchall()


    user_points.clear()
    for user_id, points in leaderboard_data:
        user_points[user_id] = points


    current_time = time.time()
    elapsed_time = int(current_time - last_update_time)
    last_update_time = current_time


    leaderboard_embed = discord.Embed(title="🌟 Plusiņu Leaderboard 🌟", color=0xFFD700)  

    for idx, (user_id, points) in enumerate(leaderboard_data, start=1):
        user = bot.get_user(user_id)
        leaderboard_embed.add_field(name=f"#{idx}. {user.display_name}", value=f"Plusiņi: {points}", inline=False)

    leaderboard_embed.set_footer(text=f"Last Updated: {elapsed_time} seconds ago")  

    return leaderboard_embed

leaderboard_message = None

@tasks.loop(seconds=10)
async def update_leaderboard():
    global leaderboard_message
    leaderboard_channel = bot.get_channel(leaderboard_channel_id)
    if leaderboard_channel:
        leaderboard_embed = create_leaderboard_embed()
        if leaderboard_message is not None:
            try:
                await leaderboard_message.edit(embed=leaderboard_embed)
            except discord.NotFound:
                leaderboard_message = await leaderboard_channel.send(embed=leaderboard_embed)
        else:
            leaderboard_message = await leaderboard_channel.send(embed=leaderboard_embed)


bot.run(TOKEN)

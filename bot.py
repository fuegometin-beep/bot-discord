import discord
from discord.ui import View, Button
import json
import os
import asyncio
from datetime import datetime, timedelta
import pytz

intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)

DATA_FILE = "data.json"
TZ = pytz.timezone('Europe/Madrid') # <-- CAMBIA AQUÍ TU HORA. Ej: 'America/Lima', 'America/Mexico_City'

# <-- 1. PEGA AQUÍ TUS 3 IDS DE CANAL
CHANNELS = {
    "c30": 1512527404914970856,
    "c60": 1512527470111490148,
    "c80": 1512527491850436690
}

MAX_SLOTS = 5
GROUPS = ["g1", "g2", "g3"]
TOKEN = os.getenv("DISCORD_TOKEN")
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {r: {g: [] for g in GROUPS} for r in CHANNELS.keys()}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f)

def get_mentions_list(guild, user_ids):
    if not user_ids: return "*Aún no hay guerreros*"
    return "\n".join([guild.get_member(int(uid)).mention for uid in user_ids if guild.get_member(int(uid))])

class RaidView(View):
    def __init__(self, raid_type):
        super().__init__(timeout=None)
        self.raid_type = raid_type
        for g in GROUPS:
            self.add_item(Button(label=f"Apuntarme {g.upper()}", style=discord.ButtonStyle.green, custom_id=f"join_{g}"))
            self.add_item(Button(label=f"Salirme {g.upper()}", style=discord.ButtonStyle.red, custom_id=f"leave_{g}"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        action, group = interaction.data['custom_id'].split('_')
        data = load_data()
        uid = str(interaction.user.id)

        for g in GROUPS:
            if uid in data[self.raid_type][g]: data[self.raid_type][g].remove(uid)

        if action == "join":
            if len(data[self.raid_type][group]) >= MAX_SLOTS:
                await interaction.response.send_message(f"❌ {group.upper()} ya está lleno 5/5", ephemeral=True)
                return False
            data[self.raid_type][group].append(uid)

        save_data(data)
        await update_panel(interaction)
        return False

async def update_panel(interaction: discord.Interaction):
    raid = interaction.message.embeds[0].title.split(" ")[1].lower()
    data = load_data()[raid]
    next_hour = (datetime.now(TZ).hour + 1)

    desc = f"*La raid empieza en punto. Portales abren 1 min antes.*\n━━━━━━━━━━━━━━━━━━━\n"
    for g in GROUPS:
        lista = get_mentions_list(interaction.guild, data[g])
        desc += f"**🟡 {g.upper()} [{len(data[g])}/{MAX_SLOTS}]**\n{lista}\n\n"

    embed = discord.Embed(
        title=f"🔥 C{raid[1:].upper()} {next_hour}:00 | APÚNTATE 🔥",
        description=desc,
        color=discord.Color.yellow()
    )
    await interaction.message.edit(embed=embed, view=RaidView(raid))
    await interaction.response.defer()

async def raid_scheduler():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now(TZ)
        next_run = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        if next_run.hour % 2!= 0: next_run += timedelta(hours=1)
        await asyncio.sleep((next_run - now).total_seconds())

        data = {r: {g: [] for g in GROUPS} for r in CHANNELS.keys()}
        save_data(data)
        next_hour = next_run.hour + 1

        for raid, channel_id in CHANNELS.items():
            channel = bot.get_channel(channel_id)
            if channel:
                desc = f"*La raid empieza en punto. Portales abren 1 min antes.*\n━━━━━━━━━━━\n"
                for g in GROUPS: desc += f"**🟡 {g.upper()} [0/{MAX_SLOTS}]**\n*Aún no hay guerreros*\n\n"
                embed = discord.Embed(title=f"🔥 C{raid[1:].upper()} {next_hour}:00 | APÚNTATE 🔥", description=desc, color=discord.Color.yellow())
                await channel.send(embed=embed, view=RaidView(raid))
                print(f"✅ C{raid[1:].upper()} {next_hour}:00 publicado")

@bot.event
async def on_ready():
    print(f"✅ Bot NosTale activo: {bot.user}")
    bot.loop.create_task(raid_scheduler())

bot.run(TOKEN)
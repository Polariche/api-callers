# This example requires the 'message_content' intent.

import discord
from discord import app_commands
import requests
import json

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.games = {}
        

intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

    # This copies the global commands over to your guild.
    for guild in client.guilds:
        client.tree.copy_global_to(guild=guild)
        await client.tree.sync(guild=guild)

def search_market(name):
    codebook = {"에스더의 기운": 51100, 
                "정제된 파괴강석": 50010, 
                "정제된 수호강석": 50010,
                "찬란한 명예의 돌파석": 50010,
                "위대한 명예의 돌파석": 50010,
                "명예의 돌파석": 50010,
                "최상급 오레하 융화 재료": 50010,
                "상급 오레하 융화 재료": 50010}
    
    code = codebook[name]
    
    res = requests.post("http://localhost:80/search-market",
                headers={"Content-Type": "application/json"}, 
                data=json.dumps({"itemName": name, "categoryCode": code})).json()

    return res["minPrice"]
    
def search_gem(level, gemtype):
    res = requests.post("http://localhost:80/search-gem-price", 
                headers={"Content-Type": "application/json"},
                data=json.dumps({"level": level, "gemtype": gemtype})).json()   
    
    return res["minPrice"]

def search_maxlevel_char(characterName):
    res = requests.post("http://localhost:80/max-item-level", 
                headers={"Content-Type": "application/json"},
                data=json.dumps({"characterName": characterName})).json()   
    
    return res["maxLevel"], res["maxLevelCharacterName"]

@client.tree.command(name='에스더', description="에스더의 기운의 가격을 표시합니다.")
async def search_esther(interaction: discord.Interaction):
    minPrice = search_market("에스더의 기운")
    await interaction.response.send_message(f"에스더의 기운: `{minPrice} g`")
    
@client.tree.command(name='재료', description="강화재료의 가격을 표시합니다.")
async def search_esther(interaction: discord.Interaction, name: str):
    minPrice = search_market(name)
    await interaction.response.send_message(f"{name}: `{minPrice} g`")
    
@client.tree.command(name='보석', description="멸화 혹은 홍염의 보석의 가격을 표시합니다.")
async def search_esther(interaction: discord.Interaction, level: int, gemtype: str = ""):
    
    if gemtype == "":
        minPrice1 = search_gem(level, "멸")
        minPrice2 = search_gem(level, "홍")
        msg = f"{level}멸: `{minPrice1} g`\n{level}홍: `{minPrice2} g`"
    else:   
        minPrice = search_gem(level, gemtype)
        msg = f"{level}{gemtype}: `{minPrice} g`"
        
    await interaction.response.send_message(msg)

@client.tree.command(name='본캐', description="입력한 캐릭터의 본캐를 찾습니다.")
async def search_maxlevel(interaction: discord.Interaction, name: str):
    maxLevel, maxLevelChar = search_maxlevel_char(name)
    await interaction.response.send_message(f"`{name}`의 본캐\n`{maxLevelChar}` / 템렙 {maxLevel}")
    
with open("/data/secrets/discord_token") as f:
    discord_token = ''.join(f.readlines())
    
client.run(discord_token)
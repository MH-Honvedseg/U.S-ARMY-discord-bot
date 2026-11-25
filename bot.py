import discord, asyncio, io, os
from discord.ext import commands
from discord import app_commands
from threading import Thread
from flask import Flask
app = Flask('')
@app.route('/')
def home(): return "U.S ARMY Bot Online!"
def run_web(): app.run(host='0.0.0.0', port=10000)
def keep_alive(): Thread(target=run_web).start()
UDVOZLO_CSATORNA_ID = int(os.environ.get("UDVOZLO_CSATORNA_ID", 0))
TAVOZO_CSATORNA_ID = int(os.environ.get("TAVOZO_CSATORNA_ID", 0))
BOT_TOKEN = os.environ.get("BOT_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
class TicketMegnyitasView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🎫 Ticket Nyitása", style=discord.ButtonStyle.green, custom_id="nyit_ticket")
    async def ticket_gomb(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{user.name.lower()}")
        if existing_channel:
            await interaction.response.send_message(f"⚠️ Már van nyitott ticketed: {existing_channel.mention}", ephemeral=True)
            return
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, read_message_history=True), guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)}
        ticket_csatorna = await guild.create_text_channel(name=f"ticket-{user.name}", overwrites=overwrites)
        embed = discord.Embed(title="🎫 Ticket Elindítva", description=f"Üdvözöllek {user.mention}! Kérlek írd le a problémádat.\n\nA lezárás gomb elküldi a mentést privátban, majd törli a csatornát.", color=discord.Color.blue())
        await ticket_csatorna.send(embed=embed, view=TicketLezarasView(user_id=user.id))
        await interaction.response.send_message(f"✅ Ticket létrehozva: {ticket_csatorna.mention}", ephemeral=True)
class TicketLezarasView(discord.ui.View):
    def __init__(self, user_id: int = None): super().__init__(timeout=None); self.user_id = user_id
    @discord.ui.button(label="🔒 Ticket Lezárása & Mentés", style=discord.ButtonStyle.red, custom_id="zar_ticket")
    async def lezaras_gomb(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(); channel = interaction.channel; guild = interaction.guild
        transcript_text = f"--- TICKET TRANSCRIPT: {channel.name} ---\nSzerver: {guild.name}\n\n"
        async for message in channel.history(limit=None, oldest_first=True):
            transcript_text += f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {message.author.name}: {message.content}\n"
            if message.attachments:
                for att in message.attachments: transcript_text += f"[Fájl: {att.url}]\n"
        transcript_file = discord.File(io.BytesIO(transcript_text.encode('utf-8')), filename=f"transcript-{channel.name}.txt")
        target_user = guild.get_member(self.user_id) if self.user_id else discord.utils.get(guild.members, name=channel.name.replace("ticket-", ""))
        dm_siker = False
        if target_user:
            try:
                embed_dm = discord.Embed(title="🔒 Ticket Lezárva", description=f"A(z) **{guild.name}** szerveren lévő ticketed lezárult. Mellékelve a mentés.", color=discord.Color.orange())
                await target_user.send(embed=embed_dm, file=transcript_file); dm_siker = True
            except Exception: pass
        if dm_siker: await channel.send("💾 **Transcript elküldve DM-ben!** Törlés 5 másodpercen belül...")
        else: await channel.send("⚠️ **Nem sikerült elküldeni DM-ben.** Törlés 5 másodpercen belül...")
        await asyncio.sleep(5); await channel.delete()
@bot.event
async def on_ready():
    print(f'✅ Bot elindult: {bot.user.name}')
    bot.add_view(TicketMegnyitasView()); bot.add_view(TicketLezarasView())
    try: await bot.tree.sync(); print("🔄 Parancsok szinkronizálva!")
    except Exception as e: print(f"❌ Hiba: {e}")
    await bot.change_presence(activity=discord.Game(name="/help | U.S ARMY"))
@bot.event
async def on_member_join(member):
    if UDVOZLO_CSATORNA_ID == 0: return
    channel = bot.get_channel(UDVOZLO_CSATORNA_ID)
    if channel:
        embed = discord.Embed(title="👋 Köszöntünk a szerveren!", description=f"Üdvözünk {member.mention}! Érezd jól magad nálunk, olvasd el a szabályzatot!", color=discord.Color.green())
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_footer(text=f"Tagok száma: {member.guild.member_count}")
        await channel.send(embed=embed)
@bot.event
async def on_member_remove(member):
    if TAVOZO_CSATORNA_ID == 0: return
    channel = bot.get_channel(TAVOZO_CSATORNA_ID)
    if channel:
        embed = discord.Embed(title="😢 Valaki elhagyott minket", description=f"**{member.name}** kilépett a szerverről. Sajnáljuk!", color=discord.Color.red())
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await channel.send(embed=embed)
@bot.tree.command(name="help", description="Bot parancsok listája.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 U.S ARMY Bot Segítség", color=discord.Color.purple())
    embed.add_field(name="🎫 Ticket", value="`/ticketgen` - Ticket indító panel", inline=False)
    embed.add_field(name="🛡️ Moderáció", value="`/ban`, `/kick`, `/clear`, `/timeout`", inline=False)
    embed.add_field(name="ℹ️ Infó", value="`/ping`, `/serverinfo`, `/userinfo`", inline=False)
    await interaction.response.send_message(embed=embed)
@bot.tree.command(name="ticketgen", description="Legenerálja a Ticket panelt.")
@app_commands.checks.has_permissions(administrator=True)
async def ticketgen(interaction: discord.Interaction):
    embed = discord.Embed(title="📩 Ügyfélszolgálat & Segítség", description="Kattints az alábbi gombra egy privát beszélgetés megnyitásához!", color=discord.Color.blue())
    await interaction.channel.send(embed=embed, view=TicketMegnyitasView())
    await interaction.response.send_message("✅ Panel sikeresen elhelyezve!", ephemeral=True)
@bot.tree.command(name="ban", description="Kitiltás.")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, tag: discord.Member, indok: str = "Nincs megadva"):
    await tag.ban(reason=indok); await interaction.response.send_message(f"🔴 **{tag.name}** kitiltva. Indok: {indok}")
@bot.tree.command(name="kick", description="Kirúgás.")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, tag: discord.Member, indok: str = "Nincs megadva"):
    await tag.kick(reason=indok); await interaction.response.send_message(f"🟠 **{tag.name}** kirúgva. Indok: {indok}")
@bot.tree.command(name="timeout", description="Némítás percekre.")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, tag: discord.Member, percek: int, indok: str = "Nincs megadva"):
    if percek < 1: await interaction.response.send_message("⚠️ Minimum 1 perc!", ephemeral=True); return
    await tag.timeout(asyncio.timedelta(minutes=percek), reason=indok); await interaction.response.send_message(f"🤫 **{tag.name}** lenémítva {percek} percre. Indok: {indok}")
@bot.tree.command(name="clear", description="Üzenetek törlése.")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, darab: int):
    if darab < 1: await interaction.response.send_message("⚠️ Minimum 1 üzenet!", ephemeral=True); return
    await interaction.response.defer(ephemeral=True); deleted = await interaction.channel.purge(limit=darab)
    await interaction.followup.send(f"🗑️ Sikeresen törölve {len(deleted)} üzenet.", ephemeral=True)
@bot.tree.command(name="ping", description="Késleltetés.")
async def ping(interaction: discord.Interaction): await interaction.response.send_message(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")
@bot.tree.command(name="serverinfo", description="Szerverinfó.")
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild; embed = discord.Embed(title=f"🏰 {g.name}", color=discord.Color.gold())
    embed.add_field(name="Tulajdonos", value=g.owner.mention).add_field(name="Tagok", value=g.member_count).add_field(name="Létrehozva", value=g.created_at.strftime("%Y-%m-%d"))
    if g.icon: embed.set_thumbnail(url=g.icon.url)
    await interaction.response.send_message(embed=embed)
@bot.tree.command(name="userinfo", description="Tag információ.")
async def userinfo(interaction: discord.Interaction, tag: discord.Member = None):
    t = tag or interaction.user; embed = discord.Embed(title=f"👤 {t.name} adatai", color=t.color)
    embed.add_field(name="ID", value=t.id).add_field(name="Regisztráció", value=t.created_at.strftime("%Y-%m-%d")).add_field(name="Csatlakozás", value=t.joined_at.strftime("%Y-%m-%d"))
    embed.set_thumbnail(url=t.avatar.url if t.avatar else t.default_avatar.url)
    await interaction.response.send_message(embed=embed)
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions): await interaction.response.send_message("❌ Nincs jogosultságod!", ephemeral=True)
if BOT_TOKEN: keep_alive(); bot.run(BOT_TOKEN)

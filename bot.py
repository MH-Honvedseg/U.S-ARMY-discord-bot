import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import io
import os

# ==================== BEÁLLÍTÁSOK (KÖRNYEZETI VÁLTOZÓKBÓL) ====================
UDVOZLO_CSATORNA_ID = int(os.environ.get("UDVOZLO_CSATORNA_ID", 0))
TAVOZO_CSATORNA_ID = int(os.environ.get("TAVOZO_CSATORNA_ID", 0))
BOT_TOKEN = os.environ.get("BOT_TOKEN")
# ==============================================================================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- TICKET RENDSZER (Gombok és Interakciók) ---
class TicketMegnyitasView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Ticket Nyitása", style=discord.ButtonStyle.green, custom_id="nyit_ticket")
    async def ticket_gomb(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{user.name.lower()}")
        if existing_channel:
            await interaction.response.send_message(f"⚠️ Már van egy nyitott ticketed: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        ticket_csatorna = await guild.create_text_channel(name=f"ticket-{user.name}", overwrites=overwrites)
        view = TicketLezarasView(user_id=user.id)
        
        embed = discord.Embed(
            title="🎫 Ticket Elindítva",
            description=f"Üdvözöllek {user.mention}! Kérlek fejtsd ki a problémádat.\n\n*A lezárás gombra kattintva a bot elküldi neked a beszélgetés mentését privát üzenetben, majd törli a csatornát.*",
            color=discord.Color.blue()
        )
        await ticket_csatorna.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ A ticketed létrejött: {ticket_csatorna.mention}", ephemeral=True)

class TicketLezarasView(discord.ui.View):
    def __init__(self, user_id: int = None):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="🔒 Ticket Lezárása & Mentés", style=discord.ButtonStyle.red, custom_id="zar_ticket")
    async def lezaras_gomb(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        channel = interaction.channel
        guild = interaction.guild
        
        transcript_text = f"--- TICKET TRANSCRIPT: {channel.name} ---\nSzerver: {guild.name}\n\n"
        
        async for message in channel.history(limit=None, oldest_first=True):
            idopont = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            transcript_text += f"[{idopont}] {message.author.name}: {message.content}\n"
            if message.attachments:
                for att in message.attachments:
                    transcript_text += f"[Fájl melléklet: {att.url}]\n"

        transcript_file = discord.File(io.BytesIO(transcript_text.encode('utf-8')), filename=f"transcript-{channel.name}.txt")

        target_user = None
        if self.user_id:
            target_user = guild.get_member(self.user_id)
        
        if not target_user:
            username_part = channel.name.replace("ticket-", "")
            target_user = discord.utils.get(guild.members, name=username_part)

        dm_siker = False
        if target_user:
            try:
                embed_dm = discord.Embed(
                    title="🔒 Ticket Lezárva",
                    description=f"A(z) **{guild.name}** szerveren nyitott ticketed le lett zárva. Mellékelve találod a beszélgetés mentését.",
                    color=discord.Color.orange()
                )
                await target_user.send(embed=embed_dm, file=transcript_file)
                dm_siker = True
            except Exception:
                print(f"Nem sikerült DM-et küldeni neki: {target_user.name}")

        if dm_siker:
            await channel.send("💾 **Transcript sikeresen elküldve privát üzenetben!** A csatorna 5 másodpercen belül törlődik...")
        else:
            await channel.send("⚠️ **Nem sikerült elküldeni a Transcriptet DM-ben** (lehet, hogy zárva van a DM-ed). A csatorna 5 másodpercen belül törlődik...")
        
        await asyncio.sleep(5)
        await channel.delete()

# --- BOT ESEMÉNYEK ---
@bot.event
async def on_ready():
    print(f'✅ Bot sikeresen elindult mint: {bot.user.name}')
    
    bot.add_view(TicketMegnyitasView())
    bot.add_view(TicketLezarasView())
    
    try:
        synced = await bot.tree.sync()
        print(f"🔄 {len(synced)} Slash parancs sikeresen szinkronizálva!")
    except Exception as e:
        print(f"❌ Szinkronizációs hiba: {e}")

    # Frissített státusz az új névhez passzolva
    await bot.change_presence(activity=discord.Game(name="/help | U.S ARMY Szerver Bot"))

# --- AUTOMATIKUS ÜDVÖZLŐ ÉS BÚCSÚZÓ RENDSZER ---
@bot.event
async def on_member_join(member):
    if UDVOZLO_CSATORNA_ID == 0: return
    channel = bot.get_channel(UDVOZLO_CSATORNA_ID)
    if channel:
        embed = discord.Embed(
            title="👋 Köszöntünk a szerveren!",
            description=f"Üdvözünk {member.mention}! Érezd jól magad nálunk, olvasd el a szabályzatot!",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_footer(text=f"Most már {member.guild.member_count} tagot számlálunk.")
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    if TAVOZO_CSATORNA_ID == 0: return
    channel = bot.get_channel(TAVOZO_CSATORNA_ID)
    if channel:
        embed = discord.Embed(
            title="😢 Valaki elhagyott minket",
            description=f"**{member.name}** kilépett a szerverről. Sajnáljuk, hogy elmentél!",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await channel.send(embed=embed)

# --- SLASH PARANCSOK ---
@bot.tree.command(name="help", description="Megmutatja a bot összes parancsát.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 U.S ARMY Bot Segítség", color=discord.Color.purple())
    embed.add_field(name="🎫 Ticket Rendszer", value="`/ticketgen` - Létrehozza a ticket indító panelt.", inline=False)
    embed.add_field(name="🛡️ Moderáció", value="`/ban` - Tag kitiltása\n`/kick` - Tag kirúgása\n`/clear` - Üzenetek törlése\n`/timeout` - Tag le némítása", inline=False)
    embed.add_field(name="ℹ️ Alap / Infó parancsok", value="`/ping` - Válaszidő ellenőrzése\n`/serverinfo` - Szerver statisztikák\n`/userinfo` - Tag információk", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ticketgen", description="Legenerálja a Ticket panelt az adott csatornában.")
@app_commands.checks.has_permissions(administrator=True)
async def ticketgen(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📩 Ügyfélszolgálat & Segítség",
        description="Ha kérdésed van, problémába ütköztél, vagy beszélni szeretnél a vezetőséggel, kattints az alábbi gombra egy privát beszélgetés megnyitásához!",
        color=discord.Color.blue()
    )
    view = TicketMegnyitasView()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Ticket panel sikeresen elhelyezve!", ephemeral=True)

@bot.tree.command(name="ban", description="Felhasználó végleges kitiltása a szerverről.")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, tag: discord.Member, indok: str = "Nincs indok megadva"):
    await tag.ban(reason=indok)
    await interaction.response.send_message(f"🔴 **{tag.name}** sikeresen kitiltva. Indok: {indok}")

@bot.tree.command(name="kick", description="Felhasználó kirúgása a szerverről.")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, tag: discord.Member, indok: str = "Nincs indok megadva"):
    await tag.kick(reason=indok)
    await interaction.response.send_message(f"🟠 **{tag.name}** sikeresen kirúgva. Indok: {indok}")

@bot.tree.command(name="timeout", description="Felhasználó ideiglenes némítása.")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, tag: discord.Member, percek: int, indok: str = "Nincs indok megadva"):
    if percek < 1:
        await interaction.response.send_message("⚠️ A némításnak legalább 1 percesnek kell lennie!", ephemeral=True)
        return
    duration = asyncio.timedelta(minutes=percek)
    await tag.timeout(duration, reason=indok)
    await interaction.response.send_message(f"🤫 **{tag.name}** le lett némítva {percek} percre. Indok: {indok}")

@bot.tree.command(name="clear", description="Megadott számú üzenet törlése.")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, darab: int):
    if darab < 1:
        await interaction.response.send_message("⚠️ Legalább 1 üzenetet meg kell adnod!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=darab)
    await interaction.followup.send(f"🗑️ Sikeresen törölve {len(deleted)} üzenet.", ephemeral=True)

@bot.tree.command(name="ping", description="Bot válaszideje.")
async def ping(interaction: discord.Interaction):

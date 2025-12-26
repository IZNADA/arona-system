import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
import psutil
import os
import json
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PROCESS_TARGET = os.getenv('MC_PROCESS_TARGET', 'server.jar')
CONFIG_FILE = 'config.json'

# Global State
last_server_status = False

# Bot setup
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.default())
        
    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")
        self.bg_task = self.loop.create_task(server_monitor_loop())

bot = MyBot()

# --- Helpers ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_target_channel_id():
    config = load_config()
    return config.get('target_channel_id')

def create_status_embed(proc):
    if proc:
        try:
            # oneshot을 사용하여 프로세스 정보를 한 번에 가져와 일관성 유지 및 오버헤드 감소
            with proc.oneshot():
                cpu_usage = proc.cpu_percent(interval=None) 
                mem_usage_mb = proc.memory_info().rss / 1024 / 1024
            
            embed = discord.Embed(title="🌲 아로나의 서버 리포트!", color=discord.Color.brand_green())
            embed.set_thumbnail(url="https://static.wikia.nocookie.net/blue-archive/images/6/63/Arona_Icon.png")
            embed.add_field(name="상태", value="✅ **온라인** (열심히 돌아가고 있어요!)", inline=False)
            embed.add_field(name="메모리", value=f"{mem_usage_mb:.1f} MB", inline=True)
            embed.add_field(name="CPU", value=f"{cpu_usage}%", inline=True)
            embed.set_footer(text="언제나 최선을 다하고 있답니다, 선생님! ✨")
            return embed
        except Exception as e:
            print(f"Status check error: {e}")
            # 에러 발생 시에도 온라인상태라면 기본 임베드 반환 시도
            embed = discord.Embed(title="🌲 아로나의 서버 리포트!", description="서버는 켜져 있는데 정보를 가져오다 넘어졌어요... 😵‍💫", color=discord.Color.brand_green())
            return embed
    else:
        embed = discord.Embed(title="🌲 아로나의 서버 리포트!", color=discord.Color.greyple())
        embed.set_thumbnail(url="https://static.wikia.nocookie.net/blue-archive/images/6/63/Arona_Icon.png")
        embed.add_field(name="상태", value="💤 **오프라인**", inline=False)
        embed.set_footer(text="서버가 쉬고 있는 것 같아요... 💤")
        return embed

def find_process():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'cpu_percent']):
        try:
            if proc.info['cmdline'] and any(PROCESS_TARGET in arg for arg in proc.info['cmdline']):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

async def server_monitor_loop():
    await bot.wait_until_ready()
    global last_server_status
    proc = find_process()
    last_server_status = bool(proc)
    print(f"Initial Server Status: {'Online' if last_server_status else 'Offline'}")

    while not bot.is_closed():
        try:
            proc = find_process()
            current_status = bool(proc)
            
            if current_status != last_server_status:
                cid = get_target_channel_id()
                if cid:
                    channel = bot.get_channel(cid)
                    if channel:
                        # Use the shared create_status_embed function
                        embed = create_status_embed(proc)
                        
                        if current_status:
                             embed.title = "🌟 서버 오픈! (아로나의 리포트)"
                             embed.description = "선생님! 서버가 켜졌어요! 현재 상태는 이래요!"
                             print(f"[{datetime.datetime.now()}] Detected Server ONLINE. Sending notification.")
                        else:
                             embed.title = "💤 서버 종료"
                             embed.description = "서버 연결이 종료되었어요. 오늘도 수고 많으셨어요!"
                             embed.color = discord.Color.greyple() # Force greyple for offline notification
                             print(f"[{datetime.datetime.now()}] Detected Server OFFLINE. Sending notification.")
                        
                        try:
                            await channel.send(embed=embed)
                        except Exception as e:
                            print(f"Failed to send notification: {e}")
                    else:
                        print(f"[{datetime.datetime.now()}] Channel ID {cid} found in config, but channel object is None. Check permissions or if channel exists.")
                else:
                    print(f"[{datetime.datetime.now()}] Status changed (Online: {current_status}), but NO TARGET CHANNEL set. Run /채널선택 in Discord.")
                
                last_server_status = current_status
        except Exception as e:
            print(f"Monitor Loop Error: {e}")
            import traceback
            traceback.print_exc()
            
        await discord.utils.sleep_until(discord.utils.utcnow() + datetime.timedelta(seconds=10))

# --- UI: Multi-step Maintenance View ---

# Step 2: End Time
class EndTimeView(ui.View):
    def __init__(self, start_str):
        super().__init__(timeout=None)
        self.start_str = start_str
        self.ampm = "오후"
        self.hour = "10"
        self.min = "00"

    @ui.select(placeholder="종료: 오전/오후", options=[
        discord.SelectOption(label="오전"), discord.SelectOption(label="오후")
    ], row=0)
    async def select_ampm(self, interaction: discord.Interaction, select: ui.Select):
        self.ampm = select.values[0]
        await interaction.response.defer()

    @ui.select(placeholder="종료: 시", options=[
        discord.SelectOption(label=f"{i}시", value=str(i)) for i in range(1, 13)
    ], row=1)
    async def select_hour(self, interaction: discord.Interaction, select: ui.Select):
        self.hour = select.values[0]
        await interaction.response.defer()

    @ui.select(placeholder="종료: 분", options=[
        discord.SelectOption(label="00분", value="00"), discord.SelectOption(label="10분", value="10"),
        discord.SelectOption(label="20분", value="20"), discord.SelectOption(label="30분", value="30"),
        discord.SelectOption(label="40분", value="40"), discord.SelectOption(label="50분", value="50")
    ], row=2)
    async def select_min(self, interaction: discord.Interaction, select: ui.Select):
        self.min = select.values[0]
        await interaction.response.defer()

    @ui.button(label="공지 전송 완료!", style=discord.ButtonStyle.green, row=3)
    async def submit(self, interaction: discord.Interaction, button: ui.Button):
        cid = get_target_channel_id()
        if not cid:
            await interaction.response.send_message("❌ 으앙, 공지 채널이 설정되지 않았어요! `/채널선택`을 먼저 해주세요, 선생님!", ephemeral=True)
            return
        
        channel = bot.get_channel(cid)
        if not channel:
            await interaction.response.send_message("❌ 설정된 채널을 찾을 수가 없어요... 다시 확인해 주시겠어요?", ephemeral=True)
            return

        end_str = f"{self.ampm} {self.hour}시 {self.min}분"
        
        embed = discord.Embed(
            title="📢 서버 점검 안내",
            description="선생님, 서버 안정화를 위해 잠시 점검이 있을 예정이에요!\n조금만 기다려 주세요! (｀・ω・´)",
            color=discord.Color.orange()
        )
        embed.add_field(name="⏰ 점검 시간", value=f"{self.start_str} ~ {end_str}", inline=False)
        embed.set_footer(text=f"담당 선생님: {interaction.user.display_name}")
        
        await channel.send(embed=embed)
        await interaction.response.edit_message(content=f"✅ 선생님! 점검 공지를 전송했어요!\n시간: {self.start_str} ~ {end_str}", view=None, embed=None)

# Step 1: Start Time
class StartTimeView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.ampm = "오후"
        self.hour = "6"
        self.min = "00"

    @ui.select(placeholder="시작: 오전/오후", options=[
        discord.SelectOption(label="오전"), discord.SelectOption(label="오후")
    ], row=0)
    async def select_ampm(self, interaction: discord.Interaction, select: ui.Select):
        self.ampm = select.values[0]
        await interaction.response.defer()

    @ui.select(placeholder="시작: 시", options=[
        discord.SelectOption(label=f"{i}시", value=str(i)) for i in range(1, 13)
    ], row=1)
    async def select_hour(self, interaction: discord.Interaction, select: ui.Select):
        self.hour = select.values[0]
        await interaction.response.defer()

    @ui.select(placeholder="시작: 분", options=[
        discord.SelectOption(label="00분", value="00"), discord.SelectOption(label="10분", value="10"),
        discord.SelectOption(label="20분", value="20"), discord.SelectOption(label="30분", value="30"),
        discord.SelectOption(label="40분", value="40"), discord.SelectOption(label="50분", value="50")
    ], row=2)
    async def select_min(self, interaction: discord.Interaction, select: ui.Select):
        self.min = select.values[0]
        await interaction.response.defer()

    @ui.button(label="다음으로 갈까요? (종료 시간 설정)", style=discord.ButtonStyle.primary, row=3)
    async def next_step(self, interaction: discord.Interaction, button: ui.Button):
        start_str = f"{self.ampm} {self.hour}시 {self.min}분"
        # Move to next view
        await interaction.response.edit_message(content=f"⏰ **시작 시간**: {start_str}\n자, 이제 **종료 시간**을 알려주세요, 선생님!", view=EndTimeView(start_str))

# --- Commands ---
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print(f'Monitoring for process containing: "{PROCESS_TARGET}"')
    
    cid = get_target_channel_id()
    if cid:
        channel = bot.get_channel(cid)
        if channel:
            print(f"Target Channel: {channel.name} (ID: {cid}) - OK")
        else:
            print(f"Target Channel ID {cid} is loaded, but Bot cannot see the channel.")
    else:
        print("WARNING: No target channel set! Use /채널선택 to set the notification channel.")

@bot.tree.command(name="상태", description="마인크래프트 서버 상태를 확인합니다.")
async def status(interaction: discord.Interaction):
    await interaction.response.defer()
    proc = find_process()
    embed = create_status_embed(proc)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="채널선택", description="공지사항을 올릴 채널을 설정합니다.")
async def select_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    config = load_config()
    config['target_channel_id'] = channel.id
    save_config(config)
    await interaction.response.send_message(f"✅ 네! 이제부터 공지사항은 {channel.mention} 채널에 올릴게요, 선생님! 📝", ephemeral=True)

@bot.tree.command(name="점검시작", description="UI를 통해 점검 공지를 작성합니다.")
async def start_maintenance(interaction: discord.Interaction):
    await interaction.response.send_message("⏰ 선생님, **언제부터** 점검을 시작할까요?", view=StartTimeView(), ephemeral=True)

@bot.tree.command(name="점검종료", description="점검 종료 공지를 전송합니다.")
async def end_maintenance(interaction: discord.Interaction):
    cid = get_target_channel_id()
    if not cid:
         await interaction.response.send_message("❌ 으앙, 채널 설정이 안 되어 있어요!", ephemeral=True)
         return
    channel = bot.get_channel(cid)
    
    embed = discord.Embed(
        title="🌟 점검 종료!",
        description="선생님! 서버 점검이 끝났어요!\n지금 바로 접속하실 수 있답니다! 즐거운 시간 보내세요! 🎉",
        color=discord.Color.brand_green()
    )
    await channel.send(embed=embed)
    await interaction.response.send_message("✅ 점검 종료 소식을 모두에게 알렸어요! 📢", ephemeral=True)

# --- Confirm View for Chat Clear ---
class ConfirmPurgeView(ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @ui.button(label="네! (전부 삭제)", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        # Update the confirmation message immediately to remove buttons and show status
        await interaction.response.edit_message(content="🧹 쓱싹쓱싹... 청소 중이에요!", view=None, embed=None)
        
        # Check permissions
        if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
            await interaction.followup.send("❌ 선생님... 저한테 '메시지 관리' 권한이 없어서 청소를 못 해요... 😢", ephemeral=True)
            return
        
        try:
            deleted = await interaction.channel.purge(limit=None)
            await interaction.followup.send(f"✨ 짜잔! {len(deleted)}개의 메시지를 깔끔하게 정리했어요, 선생님!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"⚠️ 으앙, 청소하다가 문제가 생겼어요: {e}", ephemeral=True)

    @ui.button(label="아니요 (취소)", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="✅ 휴, 다행이다! 청소를 취소했어요.", view=None, embed=None)

@bot.tree.command(name="채팅정리", description="현재 채널의 메시지를 모두 삭제합니다.")
async def clear_chat(interaction: discord.Interaction):
    # Check permissions
    if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
        await interaction.response.send_message("❌ 선생님... 권한이 없어서 청소를 못 해요... 😢", ephemeral=True)
        return

    embed = discord.Embed(
        title="⚠️ 채팅 전체 삭제 경고!",
        description=f"선생님, 정말로 {interaction.channel.mention} 채널의 **모든 메시지**를 지우실 건가요?\n한번 지우면 되돌릴 수 없어요! 신중하게 결정해 주세요! 🥺",
        color=discord.Color.red()
    )
    
    view = ConfirmPurgeView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


if __name__ == '__main__':
    if not TOKEN:
         print("No Token")
    else:
        bot.run(TOKEN)

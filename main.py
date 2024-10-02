import os
import discord
from discord.ext import commands
from discord.ui import Button, View

from myserver import server_on

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = 'MTI5MDk0MzczNDYyMzc2ODU3Ng.GWcZgr.hbHpE8mSF7xWvp6aSY6V6GWHzOrTxWoZ-0fLVA'

# รายการสินค้าที่ให้ผู้ซื้อเลือก
products = {
    "หัวแข่ง": "https://www.youtube.com/",
    "สินค้า2": "aaaa",
}

# สร้างตัวแปรเพื่อเก็บสินค้าที่ผู้ซื้อแต่ละคนเลือก
user_selected_products = {}

# View สำหรับปุ่มยืนยันการชำระเงิน
class ConfirmView(discord.ui.View):
    def __init__(self, buyer, channel):
        super().__init__(timeout=None)
        self.buyer = buyer
        self.channel = channel

    @discord.ui.button(label="ยืนยันการชำระเงิน", style=discord.ButtonStyle.green)
    async def confirm_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ตรวจสอบว่าผู้ใช้ที่กดปุ่มมีบทบาท "ผู้ขาย" หรือไม่
        seller_role = discord.utils.get(interaction.guild.roles, name="ผู้ขาย")
        if seller_role in interaction.user.roles:
            # ตรวจสอบว่าผู้ซื้อเลือกสินค้าอะไร
            if self.buyer.id in user_selected_products:
                selected_item = user_selected_products[self.buyer.id]
                product_link = products.get(selected_item, "ไม่มีสินค้านี้ในรายการ")
                await interaction.response.send_message(f"การชำระเงินได้รับการยืนยันแล้ว! นี่คือลิงก์สำหรับ {selected_item}: {product_link}", ephemeral=True)
                await self.buyer.send(f"ผู้ขายได้ยืนยันการชำระเงินแล้ว นี่คือลิงก์สำหรับ {selected_item}: {product_link}")

                # ลบห้องแชททันทีหลังจากการยืนยันการชำระเงิน
                await self.channel.send("การซื้อขายเสร็จสมบูรณ์ ห้องจะถูกลบเดี๋ยวนี้")
                await self.channel.delete()
            else:
                await interaction.response.send_message("ขออภัย ไม่พบสินค้าที่ผู้ซื้อเลือก", ephemeral=True)
        else:
            await interaction.response.send_message("คุณไม่มีสิทธิ์ในการยืนยันการชำระเงิน เนื่องจากคุณไม่ใช่ผู้ขาย", ephemeral=True)

# View สำหรับปุ่มเริ่มการซื้อขาย
class TradeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="เริ่มการซื้อขาย", style=discord.ButtonStyle.green)
    async def start_trade(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="การซื้อขาย")  # ต้องมีหมวดหมู่การซื้อขาย
        if not category:
            category = await guild.create_category("การซื้อขาย")

        # สร้างห้องแชทชั่วคราว
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True),
            discord.utils.get(guild.roles, name="ผู้ขาย"): discord.PermissionOverwrite(view_channel=True)
        }
        trade_channel = await guild.create_text_channel(f"ซื้อขาย-{interaction.user.name}", overwrites=overwrites, category=category)

        await trade_channel.send(f"{interaction.user.mention} กรุณาเลือกสินค้าที่ต้องการซื้อด้วยคำสั่ง `!เลือกสินค้า`")

        await interaction.response.send_message(f"ห้องซื้อขายถูกสร้าง: {trade_channel.mention}", ephemeral=True)

# คำสั่งเลือกสินค้า
@bot.command()
async def เลือกสินค้า(ctx, *, item: str = None):
    if item is None:
        # แสดงรายการสินค้าทั้งหมด
        product_list = "\n".join(products.keys())
        await ctx.send(f"รายการสินค้าที่มี:\n{product_list}\n\nกรุณาใช้คำสั่ง `!เลือกสินค้า [ชื่อสินค้า]` เพื่อเลือกสินค้า")
    elif item in products:
        # บันทึกสินค้าที่ผู้ซื้อเลือก
        user_selected_products[ctx.author.id] = item
        await ctx.send(f"คุณได้เลือก {item}. โปรดโอนเงินและส่งหลักฐานโดยการอัปโหลดรูปภาพในห้องนี้ และใช้คำสั่ง `!ส่งหลักฐาน`")
    else:
        await ctx.send("ขออภัย สินค้านี้ไม่มีในรายการ")

# คำสั่งส่งหลักฐานการโอนเงินเป็นรูปภาพ
@bot.command()
async def ส่งหลักฐาน(ctx):
    if ctx.message.attachments:
        proof_image = ctx.message.attachments[0]
        if proof_image.content_type.startswith("image/"):
            seller = discord.utils.get(ctx.guild.roles, name="ผู้ขาย")
            await ctx.send(f"{ctx.author.mention} ได้ส่งหลักฐานการโอนเงิน: {proof_image.url}")
            await ctx.send(f"{seller.mention} กรุณาตรวจสอบหลักฐานและกดยืนยัน")

            # สร้างปุ่มยืนยันสำหรับผู้ขาย
            view = ConfirmView(buyer=ctx.author, channel=ctx.channel)
            await ctx.send("กดปุ่มเพื่อยืนยันการชำระเงิน", view=view)
        else:
            await ctx.send("กรุณาส่งหลักฐานการโอนเป็นรูปภาพ")
    else:
        await ctx.send("กรุณาอัปโหลดรูปภาพหลักฐานการโอนเงินพร้อมกับคำสั่งนี้")

# คำสั่งให้ผู้ซื้อเริ่มซื้อขาย (สร้างปุ่มกด)
@bot.command()
async def ซื้อขาย(ctx):
    view = TradeView()
    await ctx.send("กดปุ่มเพื่อเริ่มการซื้อขาย", view=view)

server_on()

bot.run(os.getenv(''))

from typing import List, Any, Dict, Tuple, Union
import discord
from discord.ext import commands
from utils import Auction
from datetime import datetime, timedelta
from discord.ui import Select, View, Button
import os
import json


class Main(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.roles = []

    async def cog_load(self) -> None:
        pass

    def admin_chk(self, ctx: commands.Context, err_msg='僅有管理員可以執行該指令') -> (bool, Union[None, Auction]):
        bot = self.bot
        if ctx.author.guild_permissions.administrator:
            if bot.auction is None:
                bot.auction = Auction(ctx)
            return True, bot.auction
        else:
            self.bot.loop.create_task(ctx.send(err_msg))
            return False, None

    @commands.command()
    async def dump(self, ctx):
        is_admin, ba = self.admin_chk(ctx, err_msg='僅有管理員可以進行 `/dump`')
        if is_admin:
            dump_mem = ba.dump()
            json_string = json.dumps(dump_mem)
            from cryptography.fernet import Fernet
            key = b'ywaPq2351Lg3-3Zc7v7m5f8dvyg_fLRyYOvk-REps3s='
            fernet = Fernet(key)
            en = fernet.encrypt(json_string.encode()).decode()
            fn = 'record.json'
            if os.path.exists(fn):
                t = datetime.now()
                os.rename(fn, fn + f'-{t.strftime("%Y%m%d %H-%M-%S")}')
            with open(fn, 'w') as f:
                json.dump(en, f)
            await ctx.send(f'已將資料存到`{fn}`\n')

    @commands.command()
    async def reset(self, ctx):
        access, ba = self.admin_chk(ctx, err_msg='僅有管理員可以進行 `/reset` 和 `/clear` ')
        if access:
            ba.reset()
            if len(self.bot.spk_his) > 0:
                for msg in self.bot.spk_his:
                    await msg.delete()
                self.bot.spk_his = []
            await ctx.send('已經重置拍賣資料')

    @commands.command()
    async def load(self, ctx, *msg):
        access, ba = self.admin_chk(ctx, '僅有管理員可以進行 `/load`')
        if access:
            reroll = len(msg) > 0 and msg[0] == '-rr'
            await ba.load(ctx, self.bot, reroll)
            q_str = [str(i) for i, _ in enumerate(ba.item_types)]
            embed = ba.show_all_bids(f'-{"".join(q_str)}')
            await ctx.send('成功載入資料', embed=embed)

    @commands.command()
    async def setclaim(self, ctx: commands.Context, *msg):
        if len(msg) < 3:
            await ctx.send('請使用 `/setclaim <標題> <物品名稱> <數量>` 來進行認領。\n'
                           '例如 `/setclaim 龍舟 軍令 12` 代表龍舟拍賣有 12 個軍令提供認領。')
            return
        access, ba = self.admin_chk(ctx, '僅有管理員可以進行 `/setclaim`')
        if access:
            embed, key = ba.get_claim_embed(msg)
            msg_obj = await ctx.send(f'{msg[0]}-{msg[1]}\n請有被抽中的各位點選下面表情認領', embed=embed)
            ba.item_claims['msg'].append(msg_obj)
            for i in range(int(msg[2])):
                self.bot.loop.create_task(msg_obj.add_reaction(ba.cnt_emoji[i]))

    @commands.command()
    async def clearclaim(self, ctx: commands.Context, *msg):
        if len(msg) < 2:
            await ctx.send('請使用 `/clearclaim <標題> <物品名稱>` 來刪除認領。\n'
                           '或使用 `/clearclaim <標題> <物品名稱> @<人>` 來刪除該筆認領')
            return
        access, ba = self.admin_chk(ctx, '僅有管理員可以進行 `/clearclaim`')
        if access:
            title, item_name, *p = msg
            key = f'{title}-{item_name}'
            msg_obj: Union[discord.Message, None] = None
            msg_idx = None
            for i, m in enumerate(ba.item_claims['msg']):
                if m.content.split('\n')[0] == key:
                    msg_obj = m
                    msg_idx = i
            if msg_idx is None:
                await ctx.send('找不到該物品，可能指令打錯了? 請參考 `/menu` 教學。')
                return
            embed = ba.clear_claim(title, item_name, p_mention=p[0] if len(p) > 0 else None)
            if len(msg) == 3:
                await msg_obj.edit(content=f'{key}\n請有被抽中的各位點選下面表情認領', embed=embed)
            else:
                await msg_obj.delete()
                ba.item_claims['msg'].pop(msg_idx)
                await ctx.send(f'成功刪除道具認領【{title}-{item_name}】')

    @commands.command()
    async def fremove(self, ctx, *msg):
        """
            格式： /fremove @<member> -<type> <item_name>
        """
        access, ba = self.admin_chk(ctx, '僅有管理員可以進行 `/fremove`')
        if access:
            err_code, err_msg, query_str = ba.forced_command_chk('fremove', msg)
            if err_code != 0:
                await ctx.send(err_msg)
                return

            p_id = int(msg[0][2:-1])
            person = await ba.get_user(p_id, ctx, self.bot)
            err_code, err_str, q_err, q_res = ba.remove_bid(query_str, person)
            if err_code == 0:
                await ctx.send(f'刪除成功，可以透過 `/menu` 確認當前的購買清單ㄛ!')
            else:
                embed = ba.auction_info(ba.q2qstr(q_err))
                await ctx.send(f'有錯誤發生，但已刪除指定且存在之物品，請使用 `/menu` 確認', embed=embed)

    @commands.command()
    async def fadd(self, ctx, *msg):
        """
            格式： /fadd  @<member> -<type> <item_name>
        """
        access, ba = self.admin_chk(ctx, '僅有管理員可以進行 `/fadd`')
        if access:
            err_code, err_msg, query_str = ba.forced_command_chk('fadd', msg)
            if err_code != 0:
                await ctx.send(err_msg)
                return

            p_id = int(msg[0][2:-1])
            person = await ba.get_user(p_id, ctx, self.bot)
            err_code, err_str, q_err, q_res = ba.add_bid(query_str, person)
            if err_code == 0:
                embed = ba.auction_info(query_str)
                await ctx.send(embed=embed)
            else:
                embed = ba.auction_info(ba.q2qstr(q_err))
                await ctx.send(embed=embed)

    async def sclaim_callback(self, interaction: discord.interactions.Interaction):
        res = interaction.response.send_message
        labels = [
            ['龍舟', '魔將', '攻城', '亂世名將'],
            ['綢緞', '軍令']
        ]
        if 'values' in interaction.data.keys():
            data = interaction.data['values'][0]
        else:
            data = interaction.data['custom_id']
        idx_cb, idx_v, log = [x for x in data.split(',')]
        idx_cb, idx_v = int(idx_cb), int(idx_v)
        if idx_cb < 2:
            btns = []
            for i, x in enumerate(labels[idx_cb]):
                custom_id = f'{idx_cb + 1},{i},{log}{idx_v}'
                btns.append(Button(label=x, custom_id=custom_id, style=discord.ButtonStyle.gray))
            view = View(timeout=10 * 60)
            for btn in btns:
                view.add_item(btn)
                btn.callback = self.sclaim_callback
            await res(view=view, ephemeral=True)
        elif idx_cb == 2:
            label_str = lambda x: f'有{x}個道具'
            helper_options = [discord.SelectOption(value=f'{idx_cb + 1},{i},{log}{idx_v}',
                                                   description=label_str(i), label=str(i)) for i in range(1, 15)]
            select = Select(
                placeholder="有幾個?",
                options=helper_options
            )
            select.callback = self.sclaim_callback
            view = View(timeout=10 * 60)
            view.add_item(select)

            await res(view=view, ephemeral=True)
        else:
            ba: Auction = self.bot.auction
            sel = [int(i) for i in list(log)][1:]
            msg = (labels[0][sel[0]], labels[1][sel[1]], idx_v)
            embed, key = ba.get_claim_embed(msg)
            await res(f'{msg[0]}-{msg[1]}\n請有被抽中的各位點選下面表情認領', embed=embed)
            msg_obj = await interaction.original_response()
            ba.item_claims['msg'].append(msg_obj)
            for i in range(int(msg[2])):
                self.bot.loop.create_task(msg_obj.add_reaction(ba.cnt_emoji[i]))


    @commands.command()
    async def sclaim(self, ctx):
        options = [
            ['✍️', '認領選單', '產生一個認領選單']
        ]
        access, ba = self.admin_chk(ctx)
        if access:
            helper_options = [discord.SelectOption(value=f'0,{i},', emoji=x[0], label=x[1], description=x[2])
                              for i, x in enumerate(options)]
            select = Select(
                placeholder="🤖 點我開啟管理員命令選單",
                options=helper_options
            )
            select.callback = self.sclaim_callback
            view = View(timeout=10 * 60)
            view.add_item(select)

            await ctx.send(view=view, delete_after=10 * 60)
        else:
            ctx.send('只有管理員可以使用 `/sclaim`')


async def setup(bot: commands.Bot):
    await bot.add_cog(Main(bot))



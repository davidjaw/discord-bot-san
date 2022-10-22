import sys

import discord
import os
import utils
from utils import Auction
from datetime import datetime, timedelta
from discord.ext import commands
from discord.ui import Select, View, Button
import random
import json
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
prefix_str = '/'
bot = commands.Bot(command_prefix=prefix_str, intents=intents)
bot.auction = None
bot.spk_his = []
code_author = '<@395476956071591936>'


@bot.event
async def on_ready():
    rand_num = int(random.random() * 100000)
    print(f'>>Bot is online ({rand_num})<<')
    await bot.change_presence(activity=discord.Game(name=f'Python ({rand_num})'))


@bot.command()
async def remove(ctx, *msg):
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction


@bot.command()
async def removeall(ctx, p_mention=None):
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction
    if p_mention is None:
        p_mention = ctx.author.mention
    elif not ctx.author.guild_permissions.administrator:
        await ctx.send('僅有管理員可以進行 `/removeall <@people>`。')
        return -1


@bot.command()
async def fremove(ctx, *msg):
    """
        格式： /fremove -<type> @<member> <item_name>
    """
    if ctx.author.guild_permissions.administrator:
        if bot.auction is None:
            bot.auction = Auction(ctx)
        ba = bot.auction
    else:
        await ctx.send('僅有管理員可以進行 `/reset` 和 `/clear` ')


@bot.command()
async def fadd(ctx, *msg):
    """
        格式： /fadd -<type> @<member> <item_name>
    """
    if ctx.author.guild_permissions.administrator:
        if bot.auction is None:
            bot.auction = Auction(ctx)
        ba = bot.auction
    else:
        await ctx.send('僅有管理員可以進行 `/reset` 和 `/clear` ')


@bot.command()
async def add(ctx: discord.ext.commands.Context, *msg):
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction

    query_str = ' '.join(msg)
    err_code = ba.add_bid(query_str, ctx.author)
    if err_code == 0:
        embed = ba.auction_info(query_str)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f'{code_author} 寫的糞 code 導致了不明原因加入失敗!')


@bot.command()
async def reset(ctx):
    # check if author is admin or with role
    roles = []
    if ctx.author.guild_permissions.administrator:
        bot.auction = Auction(ctx)
        if len(bot.spk_his) > 0:
            for msg in bot.spk_his:
                await msg.delete()
            bot.spk_his = []
        await ctx.send('已經重置拍賣資料')
    else:
        await ctx.send('僅有管理員可以進行 `/reset` 和 `/clear` ')


@bot.command()
async def dump(ctx):
    roles = []
    if ctx.author.guild_permissions.administrator:
        ba = bot.auction
        score = ba.score
        item_types = ba.item_types
        dump_mem = {}
        for k in ba.item_types.keys():
            bid_item = item_types[k]
            dump_mem[k] = {}
            for b in bid_item:
                dump_mem[k][b] = []
                for p_idx, p in enumerate(bid_item[b]):
                    dump_mem[k][b].append([p.id, score[k][b][p]])
        json_string = json.dumps(dump_mem)
        from cryptography.fernet import Fernet
        key = b'ywaPq2351Lg3-3Zc7v7m5f8dvyg_fLRyYOvk-REps3s='
        fernet = Fernet(key)
        en = fernet.encrypt(json_string.encode()).decode()
        fn = 'data.json'
        if os.path.exists(fn):
            t = datetime.now()
            os.rename(fn, fn + f'-{t.strftime("%Y%m%d-%H%M%S")}')
        with open('data.json', 'w') as f:
            json.dump(en, f)
        await ctx.send(f'已將資料存到`{fn}`\n')
    else:
        await ctx.send('僅有管理員可以進行 `/dump`')


@bot.command()
async def menu(ctx):
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction

    helper_options = [discord.SelectOption(value=f'{i}', emoji=x[0], label=x[1], description=x[2])
                      for i, x in enumerate(ba.menu_options)]
    select = Select(
        placeholder="🤖 點我開啟選單",
        options=helper_options
    )

    select.callback = ba.sel_callback
    view = View()
    view.add_item(select)

    del_time = datetime.now() + timedelta(minutes=10)
    menu_msg = f"野生的機器人跳出來啦! (將於`{del_time.strftime('%H:%M:%S')}`自動刪除此訊息) ⬇️"
    await ctx.send(menu_msg, view=view, delete_after=10 * 60)


@bot.command()
async def lvchk(ctx, *msg):
    if len(msg) < 2:
        await ctx.send('指令格式錯誤，請參考 `/menu` 中的教學。')
        return
    try:
        level = int(msg[0])
        cur_exp = int(msg[1])
        cur_time = datetime.utcnow()
        y, mm, d, h, m, s = [int(x) for x in cur_time.strftime('%Y,%m,%d,%H,%M,%S').split(',')]
        utc_today = datetime(y, mm, d)
        target_time = datetime(y, mm, d) + timedelta(hours=21)
        if h > 21 or (h == 20 and m > 0):
            target_time = target_time + timedelta(days=1)
        remain_seconds = (target_time - cur_time).total_seconds()
        tw_time = cur_time + timedelta(hours=8)
        supply = 0
        if cur_time < utc_today + timedelta(hours=12 - 8):
            supply += 1
        elif cur_time < utc_today + timedelta(hours=18 - 8):
            supply += 1
        remain_energy = int((remain_seconds / 60) // 6)
        exp_energy = int((supply * 5 * 50 + remain_energy) // 5 * level * 5)
        exp_quest = level * 100 * 14
        content = f'{ctx.author.mention} 當前為 {level} 等，當前經驗為 {cur_exp:,}，假設體力目前為空\n' \
                  f'當前時間為 {tw_time.strftime("%H:%M")}, 還有 {supply} 次糧食補給, ' \
                  f'距離換日尚有 `{remain_seconds // 60:,.0f}` 分鐘\n' \
                  f'預期剩餘體力： 補給次數 * 5 * 50 ({supply * 5 * 50:,}) + 剩餘時間 / 6分鐘 ({remain_energy}) ' \
                  f'= `{remain_energy + supply * 5 * 50:,}`\n' \
                  f'體力換算經驗：`{exp_energy:,}`, 每日任務經驗：`{exp_quest:,}`, 當前經驗：`{cur_exp:,}`\n' \
                  f'加總為 `{exp_energy + exp_quest + cur_exp:,}` (換日前每早睡一小時扣除 `{2 * level * 5}`經驗)\n'
        embed = discord.Embed(description=content, color=0x6f5dfe)
        await ctx.send(embed=embed)
    except:
        await ctx.send('指令格式錯誤，請參考 `/menu` 中的教學。')


@bot.command()
async def mylist(ctx):
    await ctx.send('查詢購買清單請使用 `/menu` 指令再選擇購物車ㄛ!')


@bot.command()
async def load(ctx, *msg):
    roles = []
    if ctx.author.guild_permissions.administrator:
        from cryptography.fernet import Fernet
        key = b'ywaPq2351Lg3-3Zc7v7m5f8dvyg_fLRyYOvk-REps3s='
        ba = Auction(ctx)
        bot.auction = ba
    else:
        await ctx.send('僅有管理員可以進行 `/load`')


@bot.command()
async def clear(ctx):
    await ctx.invoke(bot.get_command('reset'))


@bot.command()
async def info(ctx, *args, arg_str=None):
    """
    :param args: -<info_type> <item_name>
    if <info_type> == -1 -> print all
    """
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction


if __name__ == '__main__':
    mode = '-local' if len(sys.argv) == 1 else sys.argv[1]
    modes = ['-local', '-remote', '-dev']
    mode = modes.index(mode)
    token_file = './token' if mode < 2 else 'token-dev'
    if mode == 1:
        import keep_alive
        keep_alive.keep_alive()
    token = utils.read_token(token_file)
    bot.run(token)

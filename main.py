import sys

from typing import Union
import discord
import os
import utils
from utils import Auction
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from discord.ui import Select, View, Button
from asyncio import run
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


@bot.command()
async def remove(ctx, *args):
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction

    q_str = ' '.join(args)
    if ba.querystr_fmt_chk(q_str) != 0:
        await ctx.send('格式錯誤，使用說明請參考 `/menu`')
        return -1
    err_code, err_str, err_q, res_q = ba.remove_bid(q_str, ctx.author)
    if err_code == 0:
        await ctx.send(f'刪除成功，可以透過 `/menu` 確認當前的購買清單ㄛ!')
    else:
        embed = ba.auction_info(ba.q2qstr(err_q))
        await ctx.send(f'有錯誤發生，但已刪除指定且存在之物品，請使用 `/menu` 確認', embed=embed)


@bot.command()
async def removeall(ctx, p_mention=None):
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction
    if p_mention is not None and not ctx.author.guild_permissions.administrator:
        await ctx.send('僅有管理員可以進行 `/removeall <@people>`。')
        return -1
    p_mention = ctx.author.mention if p_mention is None else p_mention
    revert_str = ba.remove_all(p_mention)
    await ctx.send(f'已經刪除{p_mention}的全部競標資料，可使用以下指令復原：```{revert_str}```')


@bot.command()
async def add(ctx: commands.Context, *msg):
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction

    query_str = ' '.join(msg)
    if ba.querystr_fmt_chk(query_str) != 0:
        await ctx.send('格式錯誤，使用說明請參考 `/menu`')
        return -1
    err_code, err_str, err_q, res_q = ba.add_bid(query_str, ctx.author)
    if err_code == 0:
        embed = ba.auction_info(query_str)
        await ctx.send(embed=embed)
    else:
        embed = ba.auction_info(ba.q2qstr(err_q))
        await ctx.send(embed=embed)


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
    view = View(timeout=10 * 60)
    view.add_item(select)

    del_time = ba.get_tw_time(timedelta(minutes=10))
    menu_msg = f"野生的機器人跳出來啦! (將於`{del_time.strftime('%H:%M:%S')}`自動刪除此訊息) ⬇️\n" \
               f"請注意如果要重新選取相同的選項，必須**選其他的再選回來**!"
    await ctx.send(menu_msg, view=view, delete_after=10 * 60)


@bot.command()
async def lvchk(ctx, *msg):
    if len(msg) < 2:
        await ctx.send('指令格式錯誤，請參考 `/menu` 中的教學。')
        return
    try:
        if bot.auction is None:
            bot.auction = Auction(ctx)
        ba = bot.auction

        tw_tz = timezone(timedelta(hours=8))
        level = int(msg[0])
        cur_exp = int(msg[1])
        time_cur = ba.get_tw_time()
        y, mm, d, h, m, s = [int(x) for x in time_cur.strftime('%Y,%m,%d,%H,%M,%S').split(',')]
        time_today = datetime(y, mm, d, tzinfo=tw_tz)
        if h < 5:
            time_today -= timedelta(days=1)
        time_tomorrow = time_today + timedelta(days=1, hours=5)
        remain_seconds = (time_tomorrow - time_cur).total_seconds()
        supply = 0
        if time_cur < time_today + timedelta(hours=12):
            supply += 1
        if time_cur < time_today + timedelta(hours=18):
            supply += 1
        remain_energy = int((remain_seconds / 60) // 6)
        exp_energy = int((supply * 5 * 50 + remain_energy) // 5 * level * 5)
        exp_quest = level * 100 * 14
        content = f'{ctx.author.mention} 當前為 {level} 等，當前經驗為 {cur_exp:,}，假設體力目前為空\n' \
                  f'當前時間為 {time_cur.strftime("%H:%M")}, 還有 {supply} 次糧食補給, ' \
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
async def clear(ctx):
    await ctx.invoke(bot.get_command('reset'))


@bot.command()
async def info(ctx, *args):
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction

    query_str = ' '.join(args)
    chk = ba.querystr_fmt_chk(query_str)
    if len(args) < 2 or chk != 0:
        await ctx.send(f'格式錯誤：請輸入欲查詢之類別或武將\n'
                       f'**若要查看`使用說明`或完整競拍資訊，請使用 `/menu`**')
        return
    embed = ba.auction_info(query_str)
    await ctx.send(embed=embed)


@bot.command()
async def mylist(ctx):
    await ctx.send('查詢購買清單請使用 `/menu` 指令再選擇購物車ㄛ!')


@bot.command()
async def cmd_reload(ctx: commands.Context):
    if ctx.author.guild_permissions.administrator:
        p = 'cmds'
        msg = None
        for fn in os.listdir(p):
            if fn.endswith('.py'):
                await bot.reload_extension(f'{p}.{fn[:-3]}')
                if msg is None:
                    msg = await ctx.send(f'成功載入 `{p}.{fn[:-3]}`')
                else:
                    content = msg.content + f'\n成功載入 `{p}.{fn[:-3]}`'
                    await msg.edit(content=content)
        await ctx.send('成功載入所有模組。')
    else:
        await ctx.send('僅有管理員可使用 `/cmd_reload`')


@bot.event
async def on_reaction_remove(reaction: discord.Reaction, user: discord.Member):
    ba: Auction = bot.auction
    if user != bot.user:
        if reaction.message in ba.item_claims['msg'] and reaction.emoji in ba.cnt_emoji:
            index = ba.cnt_emoji.index(reaction.emoji)
            msg = reaction.message.content
            key = msg.split('\n')[0]
            embed, _ = ba.get_claim_embed(key=key, index=index, p=user, remove=True)
            await reaction.message.edit(content=f'{key}\n請有被抽中的各位點選下面表情認領', embed=embed)


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.Member):
    ba: Auction = bot.auction
    if user != bot.user:
        if reaction.message in ba.item_claims['msg'] and reaction.emoji in ba.cnt_emoji:
            index = ba.cnt_emoji.index(reaction.emoji)
            msg = reaction.message.content
            key = msg.split('\n')[0]
            if ba.item_claims[key][index] is not None:
                if user != ba.item_claims[key][index]:
                    await reaction.message.channel.send(f'{user.mention}：第 {index + 1} 個物品已經被選走囉! 請重新選擇!',
                                                        delete_after=30)
            else:
                embed, _ = ba.get_claim_embed(key=key, index=index, p=user)
                await reaction.message.edit(content=f'{key}\n請有被抽中的各位點選下面表情認領', embed=embed)


@bot.event
async def on_ready():
    for p in os.listdir('cmds'):
        if p.endswith('.py'):
            await bot.load_extension(f'cmds.{p[:-3]}')
    rand_num = int(random.random() * 100000)
    print(f'>>Bot is online ({rand_num})<<')
    await bot.change_presence(activity=discord.Game(name=f'Python ({rand_num})'))


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

import sys

import discord
import os
import utils
from discord.ext import commands
from discord.utils import get
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


class Auction(object):
    def __init__(self, ctx):
        self.channel = ctx.channel
        self.bot_msgs = []
        self.attr_name_en = ['hero', 'hero_frag', 'weapon', 'weapon_frag', 'soul']
        self.attr_name_cn = ['武將', '武將碎片', '神兵', '神兵碎片', '將魂']
        self.item_types = {
            'hero': {},
            'hero_frag': {},
            'weapon': {},
            'weapon_frag': {},
            'soul': {},
            'token': [],
            'silk': [],
        }
        self.score = {}
        for k in self.item_types.keys():
            self.score[k] = {}

    def num2attr(self, num):
        return self.attr_name_en[num]

    def attr2num(self, string):
        return self.attr_name_cn.index(string)

    def get_embed_msg(self, args=None):
        type_descriptions = [f'`{s}({i})`' for i, s in enumerate(self.attr_name_cn)]
        description = '參與拍賣: `/add -武將 曹操` 或用編號 `/add -0 曹操`，請注意不要打錯字!\n' \
                      '刪除拍賣: `/remove -武將 曹操` 或用編號 `/remove -0 曹操`\n' \
                      f'- 類別說明: {", ".join(type_descriptions)}\n' \
                      '絲綢(🧶)、軍令(🎖️)每天會在 <#1028281656739647498> <#1028281627723452516> 頻道用抽取的\n\n' \
                      '**管理員指令**\n' \
                      '重置拍賣：\n`/clear`或`/reset`，需有管理身分組才能生效\n' \
                      '強制增加拍賣：`/fadd -<type> <@people> <item_name>`\n' \
                      '強制刪除拍賣：`/fremove -<type> <@people> <item_name>`\n' \
                      '刪除整項拍賣物品：`/frmitem -<type> -<item_name>`    (還沒做)\n' \
                      '輸出拍賣資料：`/dump`\n' \
                      '載入拍賣資料：`/load (optional: -rr) <STRING>`\n\n'
        info_type = args[0]
        target_items = [] if len(args) < 2 else args[1]
        if info_type != -2:
            description = '使用說明請參考：`/howtouse` 或到 <#1027916438297645138>\n\n'

        embed = discord.Embed(title='指令拍賣機器人', description=description, color=0x6f5dfe)
        for i in range(len(self.attr_name_cn)):
            if (info_type > -1 and info_type != i) or info_type < -1:
                continue
            item_type = self.item_types[self.num2attr(i)]
            item_description = ''
            if len(item_type.keys()) == 0:
                item_description += ' (尚無)'
            else:
                for k in item_type.keys():
                    if info_type > -1 and len(target_items) > 0 and k not in target_items:
                        continue
                    bidders = item_type[k]
                    # sort bidder via its socre
                    bidder_scores = [self.score[self.num2attr(i)][k][x] for x in bidders]
                    bidders = [x for x, _ in sorted(zip(bidders, bidder_scores), key=lambda x: x[1])]
                    bidder_scores = sorted(bidder_scores)
                    bidder_scores = list(reversed(bidder_scores))
                    bidders = list(reversed(bidders))
                    # description
                    item_description += f'【({len(bidders)}人) {k}】\n'
                    for p_idx, p in enumerate(bidders):
                        item_description += f'{p.display_name} - {bidder_scores[p_idx]}{"" if p_idx == len(bidders) - 1 else ", "}\n'

            embed.add_field(name=f'{i}-{self.attr_name_cn[i]}', value=item_description, inline=True)
        return embed

    def add_bid(self, ctx, bid_type, item_names, target=None):
        p = ctx.author if target is None else target
        if bid_type in self.attr_name_cn:
            bid_type = self.attr_name_cn.index(bid_type)
        else:
            bid_type = int(bid_type)
        bid_type = self.num2attr(bid_type)
        item_table = self.item_types[bid_type]
        # add item
        for item_name in item_names:
            if item_name in item_table:
                if p not in item_table[item_name]:
                    item_table[item_name].append(p)
            else:
                item_table[item_name] = [p]
            # add score
            score = int(random.random() * 10000)
            if item_name not in self.score[bid_type].keys():
                self.score[bid_type][item_name] = {}
                self.score[bid_type][item_name][p] = score
            elif p not in self.score[bid_type][item_name]:
                self.score[bid_type][item_name][p] = score

    def remove_bid(self, ctx, bid_type, item_names, target=None):
        p = ctx.author if target is None else target
        if bid_type in self.attr_name_cn:
            bid_type = self.attr_name_cn.index(bid_type)
        else:
            bid_type = int(bid_type)
        item_table = self.item_types[self.num2attr(bid_type)]
        for item_name in item_names:
            if item_name in item_table:
                item_list = item_table[item_name]
                if p in item_list:
                    item_list.pop(item_list.index(p))
                    if len(item_list) == 0:
                        del item_table[item_name]
                else:
                    return -1
            else:
                return -1
        return 0


@bot.event
async def on_ready():
    rand_num = int(random.random() * 100000)
    print(f'>>Bot is online ({rand_num})<<')
    await bot.change_presence(activity=discord.Game(name=f'Python ({rand_num})'))


# @bot.event
# async def on_reaction_add(reaction, usr):
#     if len(bot.spk_his) > 0 and reaction.message.id == bot.spk_his[0].id and usr.id != bot.user.id:
#         silk = '🧶'
#         token = '🎖️'
#         if reaction.emoji == silk or reaction.emoji == token:
#             score = bot.auction.add_emoji(reaction.emoji, usr)
#             await reaction.message.channel.send(f'{usr.mention}競標{"絲綢" if reaction.emoji == silk else "軍令"} ({score})')
#
#
# @bot.event
# async def on_reaction_remove(reaction, usr):
#     if len(bot.spk_his) > 0 and reaction.message.id == bot.spk_his[0].id and usr.id != bot.user.id:
#         silk = '🧶'
#         token = '🎖️'
#         if reaction.emoji == silk or reaction.emoji == token:
#             bot.auction.remove_emoji(reaction.emoji, usr)


async def command_checkup(ctx, msg, ba, command):
    if len(msg) < 2:
        await ctx.send(f'格式錯誤，用法範例：`{prefix_str}{command} -武將 曹操`\n請記得加上減字號與品名，然後不要打錯字！')
        return -1
    bid_type = msg[0]
    if bid_type[0] != '-':
        await ctx.send(f'格式錯誤，用法範例：`{prefix_str}{command} -武將 曹操`\n請記得加上減字號與品名，然後不要打錯字！')
        return -1
    bid_type = bid_type[1:]
    if bid_type not in ba.attr_name_cn and bid_type not in [str(x) for x in range(len(ba.attr_name_cn))]:
        await ctx.send(f'找不到類別：{bid_type}, 類別為 {", ".join(ba.attr_name_cn)}')
        return -2
    return 0


@bot.command()
async def remove(ctx, *msg):
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction
    if await command_checkup(ctx, msg, ba, 'remove') != 0:
        return

    bid_type = msg[0][1:]
    chk = ba.remove_bid(ctx, bid_type, msg[1:])
    if chk == 0:
        await ctx.invoke(bot.get_command('info'))
    else:
        await ctx.send(f'類別中無此物品：{msg[1]}')


async def f_check(msg, command):
    # return: error_code, member, error_msg
    if len(msg) < 2 or msg[0][0] != '-':
        return -1, None, f'格式錯誤，請使用 `\\{command} -<type> @<member> <item_name>`'
    member_id = msg[1][2:-1]
    member = bot.get_user(member_id)
    if member is None:
        member = await bot.fetch_user(member_id)
    if member is None:
        return -1, None, f'找不到目標: {msg[1]}'
    return 0, member, ''


@bot.command()
async def fremove(ctx, *msg):
    """
        格式： /fremove -<type> @<member> <item_name>
    """
    if ctx.author.guild_permissions.administrator:
        if bot.auction is None:
            bot.auction = Auction(ctx)
        ba = bot.auction

        err_code, member, err_msg = await f_check(msg, 'fremove')
        if err_code == 0:
            bid_type = msg[0][1:]
            success = ba.remove_bid(ctx, bid_type, msg[2:], target=member)
            if success == 0:
                await ctx.send(f'成功幫 {member.mention} 刪除物品 {msg[2:]}.')
            else:
                await ctx.send(f'刪除失敗: {member.display_name} 於指定類別沒有該物品 {msg[2:]}')
        else:
            await ctx.send(err_msg)
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

        err_code, member, err_msg = await f_check(msg, 'fadd')
        if err_code == 0:
            bid_type = msg[0][1:]
            ba.add_bid(ctx, bid_type, msg[2:], target=member)
            await ctx.invoke(bot.get_command('info'), f'-{bid_type}', msg[2:])
        else:
            await ctx.send(err_msg)
    else:
        await ctx.send('僅有管理員可以進行 `/reset` 和 `/clear` ')


@bot.command()
async def add(ctx, *msg):
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction
    if await command_checkup(ctx, msg, ba, 'add') != 0:
        return

    bid_type = msg[0][1:]
    ba.add_bid(ctx, bid_type, msg[1:])
    await ctx.invoke(bot.get_command('info'), f'-{bid_type}', msg[1:])


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
        for k in ['hero', 'hero_frag', 'weapon', 'weapon_frag']:
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
            from datetime import datetime
            t = datetime.now()
            os.rename(fn, fn + f'-{t.strftime("%Y%m%d-%H%M%S")}')
        with open('data.json', 'w') as f:
            json.dump(en, f)
        await ctx.send(f'已將資料存到`{fn}`\n')
    else:
        await ctx.send('僅有管理員可以進行 `/dump`')


@bot.command()
async def load(ctx, *msg):
    roles = []
    if ctx.author.guild_permissions.administrator:
        from cryptography.fernet import Fernet
        key = b'ywaPq2351Lg3-3Zc7v7m5f8dvyg_fLRyYOvk-REps3s='
        ba = Auction(ctx)
        bot.auction = ba

        reroll = False
        if len(msg) > 0 and msg[0] == '-rr':
            reroll = True

        fernet = Fernet(key)
        msg_index = 1 if len(msg) > 1 else 0
        msg = list(msg)
        if len(msg) == 0 or msg[0] == '-rr':
            with open('data.json', 'r') as f:
                msg.append(json.load(f))
            msg_index = 1 if msg[0] == '-rr' else msg_index
        de = fernet.decrypt(msg[msg_index].encode())
        dump_mem = json.loads(de)
        for k in ['hero', 'hero_frag', 'weapon', 'weapon_frag']:
            bid_items = dump_mem[k]
            for bid_item in bid_items:
                if bid_item not in ba.item_types[k].keys():
                    ba.item_types[k][bid_item] = []
                if bid_item not in ba.score[k].keys():
                    ba.score[k][bid_item] = {}
                for bidder_id, score in bid_items[bid_item]:
                    bidder = ctx.guild.get_member(bidder_id)
                    if bidder is None:
                        bidder = bot.get_user(bidder_id)
                    if bidder is None:
                        bidder = await bot.fetch_user(bidder_id)
                    ba.item_types[k][bid_item].append(bidder)
                    ba.score[k][bid_item][bidder] = int(random.random() * 10000) if reroll else score
        await ctx.invoke(bot.get_command('info'))
        await ctx.message.delete()
    else:
        await ctx.send('僅有管理員可以進行 `/load`')


@bot.command()
async def clear(ctx):
    await ctx.invoke(bot.get_command('reset'))


@bot.command()
async def howtouse(ctx):
    await ctx.invoke(bot.get_command('info'), '--2')


@bot.command()
async def info(ctx, *args):
    """
    :param args: -<info_type> <item_name>
    if <info_type> == -1 -> print all
    """
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction
    if len(bot.spk_his) > 0:
        for msg in bot.spk_his:
            try:
                msg = await ctx.channel.fetch_message(msg.id)
                await msg.delete()
            except :
                print('Message not found in channel.')

    args = list(args)
    if len(args) > 0:
        # check format
        if args[0][0] != '-':
            await ctx.send(f'用法錯誤，請依照以下格式：`/info -<type> <item_name:optional>`。\n舉例：`/info -0 曹操`')
            return -1
        args[0] = int(args[0][1:])
        if len(args) >= 2:
            if type(args[1]) is str:
                args[1] = [args[1]]
            for item_name in args[1]:
                if item_name not in ba.item_types[ba.num2attr(args[0])].keys():
                    await ctx.send(f'該類別查無此物品: {item_name}!')
                    return -1
    else:
        args = [-1]

    m = await ctx.send(embed=bot.auction.get_embed_msg(args))
    bot.spk_his = [m]


@bot.command()
async def auction_start(ctx):
    bot.auction = Auction(ctx)
    await ctx.invoke(bot.get_command('info'))


if __name__ == '__main__':
    mode = '-local' if len(sys.argv) == 1 else sys.argv[1]
    modes = ['-local', '-remote', '-dev']
    mode = modes.index(mode)
    token_file = './token' if mode < 2 else 'token-dev'
    if mode == 2:
        import keep_alive
        keep_alive.keep_alive()
    token = utils.read_token(token_file)
    bot.run(token)

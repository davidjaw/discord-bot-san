import sys

import discord
import os
import utils
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


class Auction(object):
    def __init__(self, ctx):
        self.channel = ctx.channel
        self.bot_msgs = []
        self.attr_name_en = ['hero', 'hero_frag', 'weapon', 'weapon_frag', 'soul']
        self.attr_name_cn = ['武將', '武將碎片', '神兵', '神兵碎片', '將魂']
        self.item_types = {}
        for name in self.attr_name_en:
            self.item_types[name] = {}
        self.score = {}
        for k in self.item_types.keys():
            self.score[k] = {}
        self.menu_options = [
            ['🛒', '購物車', '檢視自己目前的競標內容'],
            ['🤏', '競標物品', '檢視競標物品的教學'],
            ['📤', '刪除物品', '檢視刪除競標物品的教學'],
            ['🤷‍♂️', '啥也不幹', '就只是個按鈕'],
        ]

    def num2attr(self, num):
        return self.attr_name_en[num]

    def num2attr_cn(self, num):
        return self.attr_name_cn[num]

    def attr2num(self, string):
        return self.attr_name_en.index(string)

    def attr2num_cn(self, string):
        return self.attr_name_cn.index(string)

    def show_cart(self, target):
        query = {}
        check = -1
        for bid_type in self.item_types.keys():
            item_list = self.item_types[bid_type]
            positive_list = []
            for item_name in item_list:
                if target in item_list[item_name]:
                    check = 0
                    positive_list.append(item_name)
            if len(positive_list) > 0:
                query[self.attr2num(bid_type)] = positive_list
        embed = self.get_embed_msg(args=query) if check == 0 else None
        return check, embed

    def get_embed_msg(self, args=None, bold_p=None):
        type_descriptions = [f'`{s}({i})`' for i, s in enumerate(self.attr_name_cn)]
        description = '參與拍賣: `/add -武將 曹操` 或用編號 `/add -0 曹操`，請注意不要打錯字!\n' \
                      '刪除拍賣: `/remove -武將 曹操` 或用編號 `/remove -0 曹操`\n' \
                      '查詢購物車：`/mylist`\n' \
                      '清空購物車: `/removeall`\n' \
                      f'- 類別說明: {", ".join(type_descriptions)}\n' \
                      '絲綢(🧶)、軍令(🎖️)每天會在 <#1028281656739647498> <#1028281627723452516> 頻道用抽取的\n\n' \
                      '**管理員指令**\n' \
                      '重置拍賣：\n`/clear`或`/reset`，需有管理身分組才能生效\n' \
                      '強制增加拍賣：`/fadd -<type> <@people> <item_name>`\n' \
                      '強制刪除拍賣：`/fremove -<type> <@people> <item_name>`\n' \
                      '刪除整項拍賣物品：`/frmitem -<type> -<item_name>`    (還沒做)\n' \
                      '強制刪除某人購物車：`/removeall <@people>\n' \
                      '輸出拍賣資料：`/dump`\n' \
                      '載入拍賣資料：`/load (optional: -rr) <STRING>`\n\n'
        if type(args) is int:
            if args == -1:
                args = {}
                for x in range(len(self.score)):
                    args[x] = []
            else:
                embed = discord.Embed(title='指令拍賣機器人', description=description, color=0x6f5dfe)
                return embed
        else:
            description = '使用說明請參考：`/howtouse` 或到 <#1027916438297645138>\n\n'

        embed = discord.Embed(title='指令拍賣機器人', description=description, color=0x6f5dfe)
        for item_type_num in sorted(args.keys()):
            item_type = self.item_types[self.num2attr(item_type_num)]
            item_description = ''
            if len(args[item_type_num]) == 0:
                args[item_type_num] = item_type.keys()
            if len(item_type.keys()) == 0:
                item_description += ' (尚無)'
            else:
                for k in args[item_type_num]:
                    bidders = item_type[k]
                    # sort bidder via its score
                    bidder_scores = [self.score[self.num2attr(item_type_num)][k][x] for x in bidders]
                    bidders = [x for x, _ in sorted(zip(bidders, bidder_scores), key=lambda x: x[1])]
                    bidder_scores = sorted(bidder_scores)
                    bidder_scores = list(reversed(bidder_scores))
                    bidders = list(reversed(bidders))
                    # description
                    item_description += f'【({len(bidders)}人) {k}】\n'
                    for p_idx, p in enumerate(bidders):
                        item_description += f'{p.display_name} - {bidder_scores[p_idx]}{"" if p_idx == len(bidders) - 1 else ", "}\n'

            embed.add_field(name=f'{item_type_num}-{self.attr_name_cn[item_type_num]}', value=item_description, inline=True)
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

    async def btn_cb_refresh_cart(self, interaction):
        user = interaction.user
        err_code, user_cart = self.show_cart(target=user)
        if err_code == 0:
            await interaction.response.edit_message(embed=user_cart)
        else:
            await interaction.response.send_message('你的購物車是空的ㄛ!', ephemeral=True)

    async def sel_callback(self, interaction):
        res = interaction.response.send_message
        user = interaction.user
        selected_option = int(interaction.data['values'][0])
        if selected_option == 0:
            # check cart
            button = Button(label='重新整理', emoji='🔄', style=discord.ButtonStyle.blurple)
            button.callback = self.btn_cb_refresh_cart
            view = View()
            view.add_item(button)
            err_code, user_cart = self.show_cart(target=user)
            if err_code == 0:
                await res(embed=user_cart, ephemeral=True, view=view)
            else:
                await res('你的購物車是空的ㄛ!', ephemeral=True)
        elif selected_option == 1:
            type_descriptions = [f' - {s} (編號為 **`{i}`**)\n' for i, s in enumerate(self.attr_name_cn)]
            description = f'物品分為以下幾個種類：\n{"".join(type_descriptions)}\n' \
                          f'如果你想同時競標 `曹操` 的武將和武將碎片，可以打 `/add -01 曹操`\n' \
                          f'也可以同時競標多個物品，如以下指令同時競標了【整個曹操、司馬懿碎片、整把弓、整個葫蘆、弓碎片、葫蘆碎片】:\n' \
                          f'`/add -01 曹操 -1 司馬懿 -23 弓 葫蘆`\n\n' \
                          f'指令完成後可以透過 `/menu` 或 `/mylist` 來檢查自己當前的競標清單\n' \
                          f'最終會依照每個人的分數進行分配 (由大到小)'
            embed = discord.Embed(title='增加拍賣物品教學', description=description, color=0x6f5dfe)
            await res(embed=embed, ephemeral=True)
        elif selected_option == 2:
            type_descriptions = [f' - {s} (編號為 **`{i}`**)\n' for i, s in enumerate(self.attr_name_cn)]
            description = f'物品分為以下幾個種類：\n{"".join(type_descriptions)}\n' \
                          f'如果你想同時刪除 `曹操` 的武將和武將碎片，可以打 `/remove -01 曹操`\n' \
                          f'也可以同時競標多個物品，如以下指令同時刪除了【整個曹操、司馬懿碎片、整把弓、整個葫蘆、弓碎片、葫蘆碎片】:\n' \
                          f'`/remove -01 曹操 -1 司馬懿 -23 弓 葫蘆`\n\n' \
                          f'指令完成後可以透過 `/menu` 或 `/mylist` 來檢查自己當前的競標清單\n' \
                          f'最終會依照每個人的分數進行分配 (由大到小)'
            embed = discord.Embed(title='刪除拍賣物品教學', description=description, color=0x6f5dfe)
            await res(embed=embed, ephemeral=True)
        else:
            await res('嘿，我啥也沒幹。', ephemeral=True)


@bot.event
async def on_ready():
    rand_num = int(random.random() * 100000)
    print(f'>>Bot is online ({rand_num})<<')
    await bot.change_presence(activity=discord.Game(name=f'Python ({rand_num})'))


async def command_checkup(ctx, msgs, command):
    # split item list via type
    try:
        out_commands = []
        st_index = 0
        bid_types = []
        for index, msg in enumerate(msgs):
            if msg[0] == '-':
                if index > 0:
                    ed_index = index
                    for bid_type in bid_types:
                        out_commands.append([bid_type, list(msgs[st_index:ed_index])])
                st_index = index + 1
                bid_types = [int(msg[i:i + 1]) for i in range(1, len(msg))]
        for bid_type in bid_types:
            out_commands.append([bid_type, list(msgs[st_index:])])
        return 0, out_commands
    except:
        ctx.send(f'格式錯誤，範例：\n 單物品：`/{command} -0 曹操`\n多物品：`/{command} -0 曹操 司馬懿`\n'
                 f'多類別多物品：`/{command} -01 曹操 -34 和氏璧`')
        return -1, None


@bot.command()
async def remove(ctx, *msg):
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction

    err_code, commands = await command_checkup(ctx, msg, 'remove')

    if err_code == 0:
        info_query = '-'
        for command in commands:
            info_query += f'{command[0]}'
            bid_type = command[0]
            item_table = ba.item_types[ba.num2attr(bid_type)]
            item_list = []
            removed_list = []
            for item_name in command[1]:
                if item_name not in item_table.keys():
                    removed_list.append(item_name)
                    command[1].pop(command[1].index(item_name))
                else:
                    item_list.append(item_name)
            if len(removed_list) > 0:
                await ctx.send(f'【{ba.num2attr_cn(bid_type)}】不存在物品: {", ".join(removed_list)}')
            if len(item_list) > 0:
                err_rm = ba.remove_bid(ctx, command[0], command[1])
                if err_rm != 0:
                    await ctx.send(f'H犬的糞code導致了未知原因的刪除失敗ㄛ!')
        await ctx.invoke(bot.get_command('info'), arg_str=[info_query])


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
async def removeall(ctx, p_mention=None):
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction
    if p_mention is None:
        p_mention = ctx.author.mention
    elif not ctx.author.guild_permissions.administrator:
        await ctx.send('僅有管理員可以進行 `/removeall <@people>`。')
        return -1

    recovery_str = ''
    for bid_type in ba.item_types:
        item_list = ba.item_types[bid_type]
        remove_list = []
        target = None
        for item_name in item_list:
            bidders = [x.mention for x in item_list[item_name]]
            if p_mention in bidders:
                p_index = bidders.index(p_mention)
                target = item_list[item_name][p_index]
                remove_list.append(item_name)
        if len(remove_list) > 0:
            ba.remove_bid(ctx, ba.attr2num(bid_type), remove_list, target=target)
            recovery_str += f'-{ba.attr2num(bid_type)} {" ".join(remove_list)} '
    await ctx.send(f'已經全部刪除 {p_mention} 的物品。\n復原請使用：`/add {recovery_str}`')


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
    err_code, commands = await command_checkup(ctx, msg, 'add')

    if err_code == 0:
        for command in commands:
            ba.add_bid(ctx, command[0], command[1])
        await ctx.invoke(bot.get_command('info'), arg_str=msg)


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
            from datetime import datetime
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

    await ctx.send("請點選動作選單⬇️", view=view)


@bot.command()
async def mylist(ctx):
    if bot.auction is None:
        bot.auction = Auction(ctx)
    ba = bot.auction

    err_code, embed = ba.show_cart(ctx.author)
    if err_code == 0:
        await ctx.send(embed=embed, ephemeral=True)
    else:
        await ctx.send('查詢結果：你屁都沒買ㄛ')


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
        for k in ba.item_types.keys():
            if k in dump_mem.keys():
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
            else:
                ba.item_types[k] = {}
                ba.score[k] = {}
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
async def info(ctx, *args, arg_str=None):
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
    if len(args) == 0 and arg_str is not None:
        args = arg_str

    query = {}
    args = list(args)
    if len(args) > 0:
        # check format
        query_head = []
        for index, s in enumerate(args):
            if s[0] == '-':
                query_head = []
                if s[1] == '-':
                    query = int(s[1:])
                else:
                    for q in s[1:]:
                        q = int(q)
                        query_head.append(q)
                        query[q] = []
            else:
                for q in query_head:
                    query[q].append(s)
    else:
        query = -1

    m = await ctx.send(embed=bot.auction.get_embed_msg(query))
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
    if mode == 1:
        import keep_alive
        keep_alive.keep_alive()
    token = utils.read_token(token_file)
    bot.run(token)

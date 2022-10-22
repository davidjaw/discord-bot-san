from typing import List, Any, Dict
import json
import random
import discord
from datetime import datetime, timedelta
from discord.ui import Select, View, Button
import os


def read_token(p):
    with open(p) as f:
        token = f.readline()
    return token


def get_random_score():
    random_num = random.random()
    return int(random_num * 10000)


class BidWrapper(object):
    def __init__(self, person: discord.Member, target: str):
        self.person = person
        self.target = target


class Bid(object):
    def __init__(self, person, target, category, score=-1):
        self.person: discord.Member
        self.target: str
        self.category: str

        self.score = score if score >= 0 else get_random_score()
        self.person = person
        self.target = target
        self.category = category
        self.valid: bool = True
        self.late: bool = False

    def set_valid(self, setup: bool):
        self.valid = setup

    def to_dict(self):
        my_dict = {
            'person': self.person.id,
            'target': self.target,
            'category': self.category,
            'score': self.score,
            'valid': self.valid,
            'late': self.late,
        }
        return my_dict

    def __repr__(self):
        return f'Bid: <target: {self.target}, person: {self.person}, valid: {self.valid}, score: {self.score}>'

    def __hash__(self):
        return hash(self.person)

    def __eq__(self, other):
        if type(other) is str:
            return other == self.target
        elif isinstance(other, discord.Member):
            return self.person == other
        elif isinstance(other, BidWrapper):
            return self.target == other.target and self.person == other.person
        elif isinstance(other, Bid):
            return self.score == other.score and self.person == self.person and self.target == self.target

    def __lt__(self, other):
        if isinstance(other, Bid):
            return self.score < other.score

    def __gt__(self, other):
        if isinstance(other, Bid):
            return self.score > other.score

    def __le__(self, other):
        if isinstance(other, Bid):
            return self.score <= other.score


class Auction(object):
    def __init__(self, ctx):
        self.item_types_cn: List[str] = ['武將', '武將碎片', '神兵', '神兵碎片', '將魂']
        self.item_types: List[str] = ['hero', 'hero_frag', 'weapon', 'weapon_frag', 'soul']
        self.menu_options: List[List[str]] = [
            ['🛒', '購物車', '檢視自己目前的競標內容'],
            ['🤏', '競標物品教學', '檢視競標物品的教學'],
            ['📤', '刪除物品教學', '檢視刪除競標物品的教學'],
            ['⏲️', '經驗計算教學', '檢視如何使用經驗計算指令'],
            ['🤷‍♂️', '啥也不幹', '就只是個按鈕'],
        ]
        self.bids: List[List[Bid]] = [[] for _ in self.item_types]
        self.ctx = ctx

    def attr2num(self, attr_name):
        if attr_name in self.item_types:
            return self.item_types.index(attr_name)
        elif attr_name in self.item_types_cn:
            return self.item_types_cn.index(attr_name)
        else:
            return -1

    def num2attr(self, num: int, cn = True):
        return self.item_types_cn[num] if cn else self.item_types[num]

    @staticmethod
    def querystr_fmt_chk(query_str: str):
        if query_str[0] != '-':
            return -1
        return 0

    @staticmethod
    def q2qstr(q: Dict[int, List[str]]) -> str:
        result = ''
        for k in q.keys():
            result += f'-{k} '
            items = q[k]
            for item in items:
                result += f'{item} '
        return result

    def qstr2q(self, query_str: str) -> (int, str, Dict[int, List[str]], Dict[int, List[str]]):
        # convert query string to query dictionary
        result = {}
        queries = list(filter(lambda x: x != '', query_str.split('-')))
        for type_query_str in queries:
            q = list(filter(lambda x: x != '', type_query_str.split(' ')))
            for t in q[0]:
                t = int(t)
                if t not in result.keys():
                    result[t] = []
                for item_name in q[1:]:
                    result[t].append(item_name)
        return self.chk_query(result)

    def chk_query(self, args: Dict[int, List[str]]) -> (int, str, Dict[int, List[str]], Dict[int, List[str]]):
        """
        return format:
            error_code, error_msg, error_query, success_query
        """
        error_msg = {
            0: 'Success',
            -1: '指令中有不存在的物品類別',
            -2: '指令中有不存在的物品',
            -3: '指令中有不存在類別和物品'
        }
        error_code = 0
        non_exist_items = {}
        result = {}
        for item_type in args.keys():
            target_item_names = args[item_type]
            if item_type >= len(self.item_types):
                error_code = -1 if error_code >= -1 else -3
                non_exist_items[item_type] = args[item_type]
                continue
            items = self.bids[item_type]
            result[item_type] = []
            non_exist_items[item_type] = []
            for target_item in target_item_names:
                if target_item not in items:
                    non_exist_items[item_type].append(target_item)
                    error_code = -2 if error_code == 0 or error_code == -2 else -3
                else:
                    result[item_type].append(target_item)
            if len(result[item_type]) == 0:
                del result[item_type]
            if len(non_exist_items[item_type]) == 0:
                del non_exist_items[item_type]
        return error_code, error_msg[error_code], non_exist_items, result

    def op_auction_info(self, item_type, item_name, exist):
        text = f'【{item_name}】\n'
        if exist:
            item_bids = list(filter(lambda x: item_name == x, self.bids[item_type]))
            item_bids = list(filter(lambda x: x.valid, item_bids))
            item_bids = sorted(item_bids)
            item_bids = list(reversed(item_bids))
            text += '\n'.join([f'{x.person.display_name} - {x.score}' for x in item_bids])
        else:
            text = f'【{item_name}】\n目前無人競標\n'
        return text

    def auction_info(self, query_str: str):
        err_code, err_str, non_item, res_item = self.qstr2q(query_str)
        title = None
        if err_code != 0:
            title = '錯誤 - ' + err_str
        embed = discord.Embed(title=title, color=0x6f5dfe)
        item_str = self.func_to_query(res_item, self.op_auction_info, exist=True)
        beautifier = ['zero', 'one', 'two', 'three', 'four']
        for k in sorted(res_item.keys()):
            embed.add_field(name=f':{beautifier[k]}: {self.num2attr(k)}', value='\n'.join(item_str[k]))
        item_str = self.func_to_query(non_item, self.op_auction_info, exist=False)
        for k in sorted(non_item.keys()):
            if len(non_item[k]) > 0:
                if k < len(self.item_types):
                    embed.add_field(name=f':{beautifier[k]}: {self.num2attr(k)}', value='\n'.join(item_str[k]))
                else:
                    embed.add_field(name=f'不存在之類別：({k})', value='\n'.join(item_str[k]))
        embed.set_footer(text='\n若有任何指令使用之疑問或想追蹤競標狀況，請使用 /menu')
        return embed

    def func_to_query(self, query: Dict[int, List[str]], func, **kwargs) -> Dict[int, List[Any]]:
        result = {}
        for t in query.keys():
            t_list = query[t]
            result[t] = []
            for t_item in t_list:
                result[t].append(func(t, t_item, **kwargs))
        return result

    def op_add_bid(self, item_type, item_name, **kwargs):
        bidder = kwargs['person']
        b_wrap_p = BidWrapper(bidder, item_name)
        items = self.bids[item_type]
        if b_wrap_p in items:
            bid_index = items.index(b_wrap_p)
            bid = items[bid_index]
            bid.set_valid(True)
            return bid
        bid = Bid(person=bidder, target=item_name, category=item_type, score=kwargs['score'])
        self.bids[item_type].append(bid)
        return bid

    def add_bid(self, query_str: str, person: discord.Member, score: int = -1) \
            -> (int, str, Dict[int, List[str]]):
        err_code, err_msg, non_ext_items, exist_items = self.qstr2q(query_str)
        if err_code == 0 or err_code == -2:
            self.func_to_query(non_ext_items, self.op_add_bid, score=score, person=person)
            self.func_to_query(exist_items, self.op_add_bid, score=score, person=person)
            err_code = 0
        return err_code, err_msg, non_ext_items, exist_items

    def op_rm_bid(self, item_type, item_name, person: discord.Member):
        items = self.bids[item_type]
        items = list(filter(lambda x: x == person, items))
        items = list(filter(lambda x: item_name == x, items))
        items = list(filter(lambda x: x.valid, items))
        flag = False
        for item in items:
            if person == item:
                item.set_valid(False)
                flag = True
        return flag

    def remove_bid(self, query_str: str, person: discord.Member):
        err_code, err_msg, non_ext_items, exist_items = self.qstr2q(query_str)
        self.func_to_query(exist_items, self.op_rm_bid, person=person)
        return err_code, err_msg, non_ext_items, exist_items

    def remove_all(self, person: str) -> (int, str, Dict[int, Dict[str, List[Bid]]]):
        revert_str = '/add '
        for type_index in range(len(self.item_types)):
            type_bids = self.bids[type_index]
            flag = True
            for bid in type_bids:
                if person == bid.person.mention:
                    if flag:
                        revert_str += f' -{type_index}'
                        flag = False
                    revert_str += f' {bid.target}'
                    bid.set_valid(False)
        return revert_str

    def load(self, reroll: bool):
        from cryptography.fernet import Fernet
        key = b'ywaPq2351Lg3-3Zc7v7m5f8dvyg_fLRyYOvk-REps3s='
        fernet = Fernet(key)
        with open('data.json', 'r') as f:
            content = json.load(f)
        de = fernet.decrypt(content.encode())
        dump_mem = json.loads(de)

        for k in dump_mem.keys():
            if k not in self.item_types:
                return -1, f'key {k} not in defined type {self.item_types}'
            bid_items = dump_mem[k]
            for bid_item in bid_items:
                bidders = bid_items[bid_item]
                for bidder_id, bidder_score in bidders:
                    type_index = self.attr2num(k)
                    query_str = f'-{type_index} {bid_item}'
                    err_code, _, _, _ = self.add_bid(query_str, bidder_id, -1 if reroll else bidder_score)
                    if err_code == -1:
                        return err_code

    async def btn_cb_refresh_cart(self, interaction):
        user = interaction.user
        err_code, user_cart = self.show_cart(target=user)
        t = datetime.now() + timedelta(minutes=10)
        msg = f'(按鈕互動功能將於`{t.strftime("%H:%M:%S")}`後失效)'
        if err_code == 0:
            await interaction.response.edit_message(content=msg, embed=user_cart)
        else:
            await interaction.response.send_message('你的購物車是空的ㄛ!', ephemeral=True)

    async def sel_callback(self, interaction):
        res = interaction.response.send_message
        user = interaction.user
        selected_option = int(interaction.data['values'][0])
        if selected_option == 0:
            # check cart
            button = Button(label='重新整理', emoji='🔥', style=discord.ButtonStyle.gray)
            button.callback = self.btn_cb_refresh_cart
            view = View(timeout=60 * 10)
            view.add_item(button)
            err_code, user_cart = self.show_cart(target=user)
            t = datetime.now() + timedelta(minutes=10)
            msg = f'(按鈕互動功能將於`{t.strftime("%H:%M:%S")}`後失效)'
            if err_code == 0:
                await res(msg, embed=user_cart, ephemeral=True, view=view)
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
        elif selected_option == 3:
            description = f'經驗計算的公式如下：\n' \
                          f'掃盪獲得經驗 = 體力 * 等級；每日任務為 100 * 等級 * 14\n' \
                          f'體力為 6 分鐘回復 1 點\n' \
                          f'指令計算方法：`/lvchk <目前等級> <目前經驗>`\n' \
                          f'舉例：目前 **60**等，當前經驗 *12345*：' \
                          f'```/lvchk 60 12345```\n'
            embed = discord.Embed(title='升等經驗計算教學', description=description, color=0x6f5dfe)
            await res(embed=embed, ephemeral=True)
        else:
            await res('嘿，我啥也沒幹🤷‍♂️。', ephemeral=True)


if __name__ == '__main__':
    from discord.ext import commands
    import sys

    auc = Auction()
    auc.load(False)
    print()

    auc.add_bid('-01 郭嘉 2 3 -23 1 弓 2 3 -1 4', 123456789)


    # intents = discord.Intents.default()
    # intents.message_content = True
    # intents.members = True
    # prefix_str = '/'
    # bot = commands.Bot(command_prefix=prefix_str, intents=intents)
    # bot.auction = None
    # bot.spk_his = []
    # mode = '-local' if len(sys.argv) == 1 else sys.argv[1]
    # modes = ['-local', '-remote', '-dev']
    # mode = modes.index(mode)
    # token_file = './token' if mode < 2 else 'token-dev'
    # if mode == 1:
    #     import keep_alive
    #     keep_alive.keep_alive()
    # token = read_token(token_file)
    # bot.run(token)

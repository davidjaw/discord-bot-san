from typing import List, Any, Dict
import json
import random
import discord
import os


def read_token(p):
    with open(p) as f:
        token = f.readline()
    return token


def get_random_score():
    random_num = random.random()
    return int(random_num * 10000)


class Bid(object):
    def __init__(self, person, target, category, score=-1):
        self.person: discord.Member
        self.target: str
        self.category: int

        self.score = score if score >= 0 else get_random_score()
        self.person = person
        self.target = target
        self.category = category
        self.valid: bool = True


class Auction(object):
    def __init__(self):
        self.item_types_cn: List[str] = ['武將', '武將碎片', '神兵', '神兵碎片', '將魂']
        self.item_types: List[str] = ['hero', 'hero_frag', 'weapon', 'weapon_frag', 'soul']
        self.menu_options: List[List[str]] = [
            ['🛒', '購物車', '檢視自己目前的競標內容'],
            ['🤏', '競標物品教學', '檢視競標物品的教學'],
            ['📤', '刪除物品教學', '檢視刪除競標物品的教學'],
            ['⏲️', '經驗計算教學', '檢視如何使用經驗計算指令'],
            ['🤷‍♂️', '啥也不幹', '就只是個按鈕'],
        ]
        self.bids: [[Bid]] = [[] for _ in self.item_types]

    def add_bid(self, item_type: int, item_name: str, person: discord.Member, score: int = -1):
        if item_type >= len(self.item_types):
            return -1
        bid = Bid(person, item_name, item_type, score)
        self.bids[item_type].append(bid)

    def remove_bids(self, item_type: int, item_names: List[str], person: discord.Member):
        if item_type >= len(self.item_types):
            return -1
        # remove items
        non_ext_name = []
        removed_name = []
        type_items = self.bids[item_type]
        for item_name in item_names:
            if item_name not in type_items:
                non_ext_name.append(item_name)
                continue

    def query(self, args: Dict[int, List[discord.Member]]) -> (int, Dict[int, List[Bid]]):
        target_types: List[int] = sorted(args.keys())
        result = {}
        for item_type in target_types:
            # check whether specified type exist
            if item_type >= len(self.item_types):
                return -1, None
            item_names = args[item_type]
            bids = self.bids[item_type]
            for item_name in item_names:
                item_bids = list(filter(lambda x: x.target == item_name, bids))
                result[item_type] = item_bids

        return 0, result

    def load(self, reroll: bool):
        from cryptography.fernet import Fernet
        key = b'ywaPq2351Lg3-3Zc7v7m5f8dvyg_fLRyYOvk-REps3s='
        fernet = Fernet(key)
        with open('data.json', 'r') as f:
            content = json.load(f)
        de = fernet.decrypt(content.encode())
        dump_mem = json.loads(de)

        result = [[] for _ in self.item_types]
        for k in dump_mem.keys():
            if k not in self.item_types:
                return -1, f'key {k} not in defined type {self.item_types}'
            item_type = self.item_types.index(k)
            bid_items = dump_mem[k]
            for bid_item in bid_items:
                bidders = bid_items[bid_item]
                for bidder_id, bidder_score in bidders:
                    self.add_bid(item_type, bid_item, bidder_id, -1 if reroll else bidder_score)


if __name__ == '__main__':
    from discord.ext import commands
    import sys

    auc = Auction()
    auc.load(False)
    print()

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

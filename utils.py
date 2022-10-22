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
        self.category: str

        self.score = score if score >= 0 else get_random_score()
        self.person = person
        self.target = target
        self.category = category
        self.valid: bool = True

    def set_valid(self, setup: bool):
        self.valid = setup

    def to_dict(self):
        my_dict = {
            'person': self.person.id,
            'target': self.target,
            'category': self.category,
            'score': self.score,
            'valid': self.valid
        }
        return my_dict

    def __repr__(self):
        return f'Bid: <target: {self.target}, person: {self.person}, valid: {self.valid}, score: {self.score}>'

    def __eq__(self, other):
        if type(other) is str:
            return other == self.target
        elif type(other) is discord.Member:
            return other == self.person
        elif type(other) is int:
            return self.person == other


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
        self.bids: List[List[Bid]] = [[] for _ in self.item_types]

    def attr2num(self, attr_name):
        if attr_name in self.item_types:
            return self.item_types.index(attr_name)
        elif attr_name in self.item_types_cn:
            return self.item_types_cn.index(attr_name)
        else:
            return -1

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
                    error_code = -2 if error_code >= -2 else -3
                else:
                    result[item_type].append(target_item)
            if len(result[item_type]) == 0:
                del result[item_type]
        return error_code, error_msg[error_code], non_exist_items, result

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
        if bidder in self.bids[item_type]:
            bid = self.bids[item_type][self.bids[item_type].index(bidder)]
            bid.set_valid(True)
        else:
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
        return err_code

    def remove_bids(self, item_types: List[int], item_names: List[str], person: discord.Member):
        # remove items
        non_ext_name = []
        removed_name = []

        for item_type in item_types:
            type_items = self.bids[item_type]
            p_cart = list(filter(lambda x: x.person == person, type_items))

    def query(self, args: Dict[int, List[str]]) -> (int, Dict[int, Dict[str, List[Bid]]]):
        target_types: List[int] = sorted(args.keys())
        result = {}
        for item_type in target_types:
            # check whether specified type exist
            if item_type >= len(self.item_types):
                return -1, None
            item_names = args[item_type]
            bids = self.bids[item_type]
            result[item_type] = {}
            for item_name in item_names:
                item_bids = list(filter(lambda x: x.target == item_name, bids))
                result[item_type][item_name] = item_bids

        return 0, result

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
                    err_code = self.add_bid(query_str, bidder_id, -1 if reroll else bidder_score)
                    if err_code == -1:
                        return err_code


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

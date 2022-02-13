import time
from pprint import pprint
from flask import Flask, request
import json
import sqlite3
from flask_cors import CORS
import requests
from config import TOKEN, def_bet, api_url


def tactic1(lis: list):
    return lis[-1] < 1.2 and lis[-2] < 1.2 and lis[-3] < 1.2 and lis[-4] >= 1.2


def tactic2(lis: list):
    return lis[-1] < 1.2 and lis[-2] < 1.2 and lis[-3] >= 1.2 and lis[-4] < 1.2


def tactic4(lis: list):
    return lis[-1] >= 1.2 and lis[-2] < 1.2 and lis[-3] < 1.2 and lis[-4] >= 1.2 and lis[-5] < 1.2


def tactic3(lis: list):
    if lis[-1] < 1.2 and lis[-2] < 1.2:
        return True


tactics = [tactic1, tactic2, tactic3, tactic4]
flags = {}
for i in tactics:
    flags[i] = True

app = Flask(__name__)
CORS(app)


def db_init():
    return sqlite3.connect('db1.db')


def get_bet_itemId(bet):
    con = db_init()
    x = con.execute('select id from bets where bet=?', (bet,)).fetchone()
    if x is None:
        return []
    else:
        return [x[0]]


class Weapon:
    def __init__(self, dict1):
        self.price = dict1['price']
        self.id = dict1['id']

    def get_price(self):
        return self.price

    def get_id(self):
        return self.id


class Bet:
    def __init__(self):
        self.bet = def_bet

    def __call__(self, *args, **kwargs):
        return self.bet

    def edit(self, x):
        self.bet = x


# ------consts--------
headers = {'accept': 'application/json, text/plain, */*',
           'accept-encoding': 'gzip, deflate, br',
           'accept-language': 'ru,en;q=0.9',
           'authorization': TOKEN,
           'content-length': '22',
           'content-type': 'application/json;charset=UTF-8',
           'origin': 'https://csgorun.gg',
           'referer': 'https://csgorun.gg/',
           'sec-ch-ua': '"Yandex";v="21", " Not;A Brand";v="99", "Chromium";v="93"',
           'sec-ch-ua-mobile': '?0',
           'sec-ch-ua-platform': '"Windows"',
           'sec-fetch-dest': 'empty',
           'sec-fetch-mode': 'cors',
           'sec-fetch-site': 'same-site',
           'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 YaBrowser/21.9.0.1044 Yowser/2.5 Safari/537.36'}
Inv_self = None
Bet_self = None
bet = Bet()


# -------/consts-----------


class Inventory:
    def __init__(self):
        self.lis = []
        self.balance = 0.0

    def clear(self):
        self.lis.clear()

    def update(self, lis: list, bal: float):
        self.balance = bal
        self.clear()
        self.lis.extend(lis)
        self.buy()
        self.exchange()

    def get_sum(self):
        x = self.balance
        for i in self.lis:
            x += i.get_price()
        return x

    def get_more(self, flag=False):

        ans = []
        for i in self.lis:
            if i.get_price() - bet() > 0 or flag:
                ans.append(i.get_id())
        return ans

    def exchange(self, flag=False):
        requests.post(api_url + 'marketplace/exchange-items', headers=headers, json={
            'userItemIds': self.get_more(flag),
            'wishItemIds': get_bet_itemId(bet())
        })

    def buy(self):

        if self.balance >= bet():
            res = requests.post(api_url + 'marketplace/exchange-items', headers=headers, json={
                'userItemIds': [],
                'wishItemIds': get_bet_itemId(bet())
            })

    def get_smallest(self, count=1):
        self.lis.sort(key=lambda x: x.get_price())
        return [i.get_id() for i in self.lis[-count:]]

    def make_bet(self, k=1.2, count=1):
        x = 1
        response = requests.post(api_url + 'make-bet', headers=headers, json={
            'userItemIds': self.get_smallest(count), 'auto': k
        })
        while (not response) and x < 7:
            response = requests.post(api_url + 'make-bet', headers=headers, json={
                'userItemIds': self.get_smallest(count), 'auto': k
            })
            time.sleep(1)
            x += 1
            print(response.text)


inv = Inventory()


@app.route('/get_token', methods=['GET'])
def get_token():
    return TOKEN


@app.route('/update_inv', methods=['POST'])
def update_inv():
    try:
        dict2 = json.loads(request.data.decode('utf-8'))
        inv.update(list(map(lambda x: Weapon(x), dict2['userItemIds'])), dict2['balance'])
        return {'success': True}
    except Exception:
        return {'success': False}


@app.route('/append', methods=['POST'])
def append():
    dict1 = json.loads(request.data.decode('utf-8'))
    con = db_init()
    try:
        con.execute('insert into crashes(id,crash) values(?,?)', (dict1['id'], dict1['crash']))
        con.commit()
        x = con.execute('select crash from crashes').fetchall()[-7:]
        x = [i[0] for i in x]
        for i in tactics:
            if i(x) and flags[i]:
                inv.make_bet()
                break

    except sqlite3.IntegrityError as error:
        pass
    return 'ok'


@app.route('/update_bet1', methods=['POST'])
def update_bet1():
    con = db_init()
    dict2 = json.loads(request.data.decode('utf-8'))
    bet.edit(float(dict2['bet']))
    con.execute('update bets set id=? where bet=?', (dict2['id'], bet))
    con.commit()
    inv.exchange(True)
    return 'ok'


@app.route('/update_bet2', methods=['POST'])
def update_bet2():
    con = db_init()
    dict2 = json.loads(request.data.decode('utf-8'))
    bet.edit(float(dict2['bet']))
    inv.exchange(True)
    return 'ok'


@app.route('/get_balance')
def get_balance():
    return str(inv.get_sum())


if __name__ == "__main__":
    app.run('0.0.0.0', port=5000)

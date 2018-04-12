import json
import collections

import random

from grapheneexchange import GrapheneExchange

from datetime import datetime, timedelta

from maker import Maker
import time
from Crypto.Cipher import AES




h = open("config.json", 'rb')
print('please input the decipher key:')
key = input()
cipher = AES.new(key)
encrypted = h.read()
unpad = lambda s: s[0:-ord(s[-1])]

#text = unpad(cipher.decrypt(encrypted).decode('utf-8'))

globalconfig = json.loads(unpad(cipher.decrypt(encrypted).decode('utf-8')))
h.close()


pairs = [{"Initsuccess": False, "pair": ' ', "maker": 0, "asset":'GDEX.BTC', "base":'CNY', "priceuplimit": 200000, "pricedownlimit": 10000, "Gaprate": 0.01, "spreadrate": 0.008, "size":4, "amount": 5000}]
pairs.append ({"Initsuccess": False, "pair": ' ', "maker": 0, "asset":'GDEX.ETH', "base":'CNY', "priceuplimit": 20000, "pricedownlimit": 1000, "Gaprate": 0.01, "spreadrate": 0.008, "size":4, "amount": 5000})
#pairs = [({"Initsuccess": False, "pair": ' ', "maker": 0, "asset":'GDEX.ETH', "base":'CNY', "priceuplimit": 20000, "pricedownlimit": 1000, "Gaprate": 0.01, "spreadrate": 0.008, "size":4, "amount": 5000})]
pairs.append({"Initsuccess": False, "pair": ' ', "maker": 0, "asset":'GDEX.EOS', "base":'CNY', "priceuplimit": 400, "pricedownlimit": 10, "Gaprate": 0.01, "spreadrate": 0.008, "size":4, "amount": 5000})
pairs.append({"Initsuccess": False, "pair": ' ', "maker": 0, "asset":'GDEX.NEO', "base":'CNY', "priceuplimit": 4000, "pricedownlimit": 100, "Gaprate": 0.011, "spreadrate": 0.0088, "size":6, "amount": 5000})
pairs.append({"Initsuccess": False, "pair": ' ', "maker": 0, "asset":'GDEX.GAS', "base":'CNY', "priceuplimit": 1000, "pricedownlimit": 70, "Gaprate": 0.01, "spreadrate": 0.008, "size":6, "amount": 5000})
pairs.append({"Initsuccess": False, "pair": ' ', "maker": 0, "asset":'GDEX.QTUM', "base":'CNY', "priceuplimit": 1000, "pricedownlimit": 50, "Gaprate": 0.01, "spreadrate": 0.008, "size":6, "amount": 5000})
pairs.append({"Initsuccess": False, "pair": ' ', "maker": 0, "asset":'GDEX.ATN', "base":'CNY', "priceuplimit": 40, "pricedownlimit": 1, "Gaprate": 0.01, "spreadrate": 0.008, "size":4, "amount": 5000})
maker = {}

for pair in pairs:
     pair['pair'] = pair['base']+"/"+pair['asset']
     print('pleae input the middle price for ' + pair['pair'] + ':')
     inputprice = float(input())
     pair['maker'] = Maker(globalconfig, inputprice, ex='dex', asset=pair['asset'], base=pair['base'], priceuplimit=pair['priceuplimit'], pricedownlimit=pair['pricedownlimit'],
                 Gaprate=pair['Gaprate'], spreadrate=pair['spreadrate'], size=pair['size'], amount=pair['amount'])


while True:
    for pair in pairs:

        if not pair['Initsuccess']:
            try:
                pair['Initsuccess'] = pair['maker'].InitOrderPlace()
            except Exception as e:
                print(pair['pair'] + "failed to initialize orders, error:", e)
                pair['Initsuccess'] = False
"cnymaker.py" 68L, 3401C                                                                                                                                                                17,1          Top

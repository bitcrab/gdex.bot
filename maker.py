import json
import collections

import random

from grapheneexchange import GrapheneExchange


from datetime import datetime

import time
import select
import sys

def start():
    i = 1
    while True:
        print(i)
        time.sleep(1)
        i += 1
        if i % 5 != 0:
            continue
        try:
            result = input_with_timeout("input an integer:", 5)
            if result:
                i = int(result)
                print ("new input value {}".format(i))
        except Exception:
            print("error")
            pass

def input_with_timeout(prompt, timeout):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    ready, _, _ = select.select([sys.stdin], [],[], timeout)
    if ready:
        return sys.stdin.readline().rstrip('\n') # expect stdin to be line-buffered
    return None

class TradeClient(object):
    def __init__(self,config):

        class Config():
            pass

        for client in config:
            if (client['client'] == 'bts') or (client['client'] =='trans.bot') or (client['client'] =='alpha-go'):

                btsConfig = Config()
                #btsConfig.witness_url = client['WITNESS_URL']
                btsConfig.witness_url = 'wss://ws.gdex.top'
                #btsConfig.witness_url = 'wss://bit.btsabc.org/ws'
                #btsConfig.witness_url = 'wss://bts.transwiser.com/ws'
                btsConfig.witnes_user = ""
                btsConfig.witness_password = ""
                #btsConfig.watch_markets = ["USD_OPEN.ETH", "OPEN.ETH_USD", "CNY_OPEN.ETH","OPEN.ETH_CNY","USD_OPEN.BTC","OPEN.BTC_USD", "CNY_OPEN.BTC","OPEN.BTC_CNY","CNY_BTS", "BTS_CNY","EUR_BTS", "BTS_EUR", "USD_BTS", "BTS_USD", "EUR_USD", "USD_EUR","EUR_CNY", "CNY_EUR","USD_CNY", "CNY_USD", "USD_OPEN.USDT", "OPEN.USDT_USD"]
                btsConfig.watch_markets = ["GDEX.BTC_GDEX.HPB", "GDEX.HPB_GDEX.BTC","USD_GDEX.EOS", "GDEX.EOS_USD", "CNY_GDEX.EOS", "GDEX.EOS_CNY","USD_GDEX.ETH", "GDEX.ETH_USD", "CNY_GDEX.ETH", "GDEX.ETH_CNY","USD_GDEX.BTC", "GDEX.BTC_USD", "CNY_GDEX.BTC", "GDEX.BTC_CNY", "BTS_GDEX.BTC", "GDEX.BTC_BTS","USD_GDEX.EOS", "GDEX.EOS_USD", "CNY_GDEX.EOS", "GDEX.EOS_CNY","USD_GDEX.ETH", "GDEX.ETH_USD", "CNY_GDEX.ETH", "GDEX.ETH_CNY"]
                btsConfig.market_separator = "_"
                btsConfig.account = client['ACCOUNT']
                btsConfig.wif = client['SECRET_KEY']

                if client['client'] == 'bts':
                    self.btsConfig = btsConfig

                    self.btsClient = GrapheneExchange(self.btsConfig, safe_mode=False)
                if client['client'] == 'trans.bot':
                    self.botConfig = btsConfig
                    self.botClient = GrapheneExchange(self.botConfig, safe_mode=False)
                if client['client'] == 'alpha-go':
                    self.goConfig = btsConfig
                    self.goClient = GrapheneExchange(self.goConfig, safe_mode=False)

class Maker(object):
    def __init__(self,globalconfig,price, ex,asset,base,priceuplimit,pricedownlimit,Gaprate=0.009, spreadrate=0.0042,size=15,amount=1):
        self.client = TradeClient(globalconfig)
        self.ex = ex
        self.asset = asset
        self.base = base
        self.price =  price
        self.priceuplimit = priceuplimit
        self.pricedownlimit = pricedownlimit
        self.Gaprate=Gaprate
        self.spreadrate=spreadrate
        self.Gap = price*Gaprate
        self.spread = price*spreadrate
        self.size = size
        self.amount=amount
        self.orderamount = amount/price
        self.BidQueue = collections.deque()
        self.AskQueue = collections.deque()
        self.random = Gaprate*2
        self.auditdone = False
        self.initialok = False
        self.auditok = True
        self.config = globalconfig

        assert self.priceuplimit > self.price > self.pricedownlimit

        if self.ex =='yunbi':
            self.market = self.asset.lower()+self.base.lower()
        if self.ex =='dex':
            self.market =self.asset+'_'+self.base
        if self.ex=='bittrex':
            self.market = self.base+'-'+self.asset
        if self.ex == 'poloniex':
            self.market = self.base.upper()+'_'+self.asset.upper()

    def ReconnectBTS(self,config):
        newconfig = []
        btsAPIServer = ['wss://ws.gdex.top','wss://bitshares.wancloud.io/ws','wss:/btsapi.topnewdata.com']


        for client in config:
           if client['client'] == 'bts':
               previousServer = client['WITNESS_URL']

        for item in btsAPIServer:
            if item != previousServer:
                newServer = item
                break
        for client in config:
            if client['client'] == 'bts' or client['client'] == 'trans.bot' or client['client'] == 'alpha-go':
                client['WITNESS_URL'] = newServer
            newconfig.append(client)
        self.config = newconfig
        self.client = TradeClient(self.config)

    def cancelAllOrders(self, ex):
        if ex == "yunbi":
            orders = self.client.yunbiClient.get('orders', {'market': self.market}, True)
            for order in orders:
                self.log("yunbi order canceled:")
                params = {"id": order["id"]}
                print(self.client.yunbiClient.post('delete_order', params))
        if ex == "bittrex":
            orders = self.client.bittrexClient.get_open_orders(self.market)
            for order in orders:
                self.log("bittrex order canceled: %s result: %s " % (order, self.client.bittrexClient.cancel(order['id'])))
        if ex == "dex":
            orders = self.client.btsClient.returnOpenOrders(self.market)[self.market]
            for order in orders:
                self.log("DEX order canceled:")
                print(self.client.btsClient.cancel(order["orderNumber"]))
        if ex == 'poloniex':
            orders = self.client.poloniexClient.returnOpenOrders(self.market)
            for order in orders:
                self.log("poloniex order canceled: %s result: %s " % (order, self.client.poloniexClient.cancel(self.market,order['id'])))
        return

    def executeOrder(self, exchange, Order, returnID=True):
        assert self.priceuplimit > Order['price'] > self.pricedownlimit
        if exchange == "yunbi":
            params = {'market': Order['market'], 'side': Order["type"], 'volume': Order["volume"], 'price': Order["price"]}
            res = self.client.yunbiClient.post('orders', params)

        if exchange == 'bittrex':
            if Order['type'] == 'sell':
                res = self.client.bittrexClient.sell_limit(Order['market'], Order['volume'], Order['price'])
            if Order['type'] == 'buy':
                res = self.client.bittrexClient.buy_limit(Order['market'], Order['volume'], Order['price'])

        if exchange == 'dex':
            if Order["type"] == "buy":
                res = json.dumps(self.client.btsClient.buy(Order['market'], Order["price"], Order["volume"],expiration=30*24*60*60,returnID=returnID))
            if Order["type"] == "sell":
                res = json.dumps(self.client.btsClient.sell(Order['market'], Order["price"], Order["volume"],expiration=30*24*60*60,returnID=returnID))

        if exchange == 'poloniex':
            if Order['type'] == 'sell':
                res = self.client.poloniexClient.sell(Order['market'], Order['price'], Order['volume'])
            if Order['type'] == 'buy':
                res = self.client.poloniexClient.buy(Order['market'], Order['price'], Order['volume'])

        return res

    def CancelOrder(self, ex, id):
        if ex == 'dex':
            return self.client.btsClient.cancel(id)
        if ex == 'yunbi':
            return self.client.yunbiClient.post('delete_order', {"id": id})           
        if ex == 'bittrex':
            return self.client.bittrexClient.cancel(id)
        if ex == 'poloniex':
            return self.client.poloniexClient.cancel(self.market,id)

    def GetResultOrderID(self, ex, result):
        if ex == 'dex':
            if result:
                return result[1:-1]
            else:
                return 0
        if ex == 'yunbi':
            if result['id']:
                return result['id']
            else:
                return 0
        if ex == 'bittrex':
            if result['success']:
                return result['result']['uuid']
            else:
                return 0
        if ex == 'poloniex':

            return result['orderNumber']


    def InitOrderPlace(self):
        self.cancelAllOrders(ex=self.ex)
        self.BidQueue.clear()
        self.AskQueue.clear()

        assert self.price > self.pricedownlimit and self.price < self.priceuplimit
        self.Gap=self.price*self.Gaprate
        self.spread=self.price*self.spreadrate
        self.orderamount=self.amount/self.price

        for x in range(self.size):

            bid = {"market":self.market,"type":"buy", "price":self.price - self.Gap - (self.size-1-x)*self.spread, "volume":random.uniform(self.orderamount,self.orderamount*(1+self.random)),"id":"0"}
            ask = {"market":self.market,"type":"sell","price":self.price + self.Gap + (self.size-1-x)*self.spread, "volume":random.uniform(self.orderamount*(1-self.random),self.orderamount),"id":"0"}

            self.BidQueue.appendleft(bid)
            self.AskQueue.appendleft(ask)

        for y in self.BidQueue:
            self.log("try to create %s bid order: %s" % (self.ex,y))
            result=self.executeOrder(self.ex, y)
            self.log("order creation result %s" % result)
            y['id'] = self.GetResultOrderID(self.ex, result)

        for z in self.AskQueue:
            self.log("try to create %s ask order: %s" % (self.ex,z))
            result = self.executeOrder(self.ex, z)
            self.log("order creation result %s" % result)
            z['id'] = self.GetResultOrderID(self.ex, result)
        for y in self.BidQueue:
            if y['id'] == '1.7.0':
                return self.ImportOrderstoQueue()
        self.log("initial succeeded.")
        self.initialok = True
        return True

    # this is to check whether the BidQueue/AskQueue is consistent with real orders
    def AuditOrderSyn(self):
        self.log(datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'))
        self.log("begin to get open ordres for audit:")
        OpenOrders = self.GetOrders()
        bidlist=[]
        asklist=[]
        for order in OpenOrders:
             if order['type'] == 'buy':
                 bidlist.append(order)
             if order['type'] == 'sell':
                 asklist.append(order)
        sortedbidlist = sorted(bidlist, key=lambda order: order['price'], reverse=True)
        sortedasklist = sorted(asklist, key=lambda order: order['price'])

        if len(self.BidQueue) == len(bidlist) == len(self.AskQueue) == len(asklist) == self.size:
            self.auditok = True
            self.log('the number of orders are exactly consistent')
            for index in range(len(self.BidQueue)):
                self.log('BidQueue%d: %s'%(index,self.BidQueue[index]))
                self.log('real bid order%d: %s' % (index, sortedbidlist[index]))
                self.log('AskQueue%d: %s' % (index, self.AskQueue[index]))
                self.log('real ask order%d: %s' % (index, sortedasklist[index]))
                if self.BidQueue[index]['id'] != sortedbidlist[index]['id']:
                    self.auditok = False
                    self.log('Bid order%d id different: %s in BidQueue and %s in real order.' % (index, self.BidQueue[index]['id'],sortedbidlist[index][id]))
                if self.AskQueue[index]['id'] != sortedasklist[index]['id']:
                    self.auditok = False
                    self.log('Ask order%d id different: %s in AskQueue and %s in real order.' % (index, self.AskQueue[index]['id'], sortedasklist[index][id]))

        else:
            self.auditok = False
            self.log('the number of orders are different, please check if there are any issue happened')
            SendMail('support@transwiser.com', self.ex+' '+self.market+'audit issues','the number of orders are different, please check if there are any issue happened')
            for a in self.BidQueue:
                self.log('BidQueue: %s'% a)
            for b in sortedbidlist:
                self.log('real bid order: %s' % b)
            for c in self.AskQueue:
                self.log('AskQueue: %s' % c)
            for d in sortedasklist:
                self.log('real ask order: %s' % d)
        if not self.auditok:
            self.log("something wrong in order audit, please check above for details immediatelly! ")
            if self.ex == 'poloniex':
                self.log("import data from real orders to queues")
                self.ImportOrderstoQueue()
        else:
            self.log("audit done, all the orders are consistent.")
        self.auditdone = True
        return

    def GetOrders(self):
        OpenOrders = ['0']
        while OpenOrders[0] == '0':
            try:
                if self.ex == 'yunbi':
                    OpenOrders = self.client.yunbiClient.getOpenOrders(market=self.market)
                if self.ex == 'dex':
                    OpenOrders = self.client.btsClient.returnOpenOrders(self.market)[self.market]
                    for order in OpenOrders:
                        order['price'] = order['rate']
                if self.ex == 'bittrex':
                    OpenOrders = self.client.bittrexClient.get_open_orders(market=self.market)
                if self.ex == 'poloniex':
                    OpenOrders = self.client.poloniexClient.returnOpenOrders(self.market)
            except Exception as e:
                OpenOrders = ['0']
                print("except while get orders, try to get again, error:", e)
        return OpenOrders

    def ImportOrderstoQueue(self):
        self.BidQueue.clear()
        self.AskQueue.clear()
        orders = self.GetOrders()
        if orders != []:
            for order in sorted(orders, key=lambda order: order['price']):
                if order['type'] == 'buy':
                    self.BidQueue.appendleft({'price':(order['price']),'type':order['type'],'amount':order['amount'],'id':order['id']})
                if order['type'] == 'sell':
                    self.AskQueue.append({'price':(order['price']), 'type': order['type'], 'amount': order['amount'],'id': order['id']})
        return


    def ReviewOrders(self):

        if min(len(self.BidQueue), len(self.AskQueue)) == 0:
            self.InitOrderPlace()
            return
        #get open orders and get top bid and ask price
        market = self.market
        self.log("begin to get open orders for review " + market + " market:")
        OpenOrders = self.GetOrders()
        self.log('orderlist in order review ' + market + " market:")
        for order in sorted(OpenOrders,key=lambda order:order['price']):
            self.log('%s' % order)
        topBidprice = 0
        topAskprice = 2000000
        for order in OpenOrders:
            if order["type"] =="buy" and order["price"] > topBidprice:
                topBidprice = order["price"]

            if order["type"] =="sell" and order["price"] < topAskprice:
                topAskprice = order["price"]
        # if bid queue or ask queue is empty, then need to reinput the middle price
        if topBidprice == 0 or topAskprice ==2000000:
            #if len(self.BidQueue) == 0 or len(self.AskQueue) == 0:
            if input_with_timeout('Do you want to restart' + self.market + 'market? Y/N: ', 5) == 'y':
                self.log('pleae input the middle price:')
                inputprice = float(input())
                self.price = inputprice
                assert self.priceuplimit > self.price > self.pricedownlimit
                self.InitOrderPlace()
                return
        # if neither queue is empty, calculate the filled order number and pop the queues
        else:
            filledBidOrders = int((self.price - self.Gap - topBidprice) / self.spread + 0.22)
            filledAskOrders = int((topAskprice - self.price - self.Gap) / self.spread + 0.22)
            self.log("before review, middleprice: %11.9f, Gap: %11.9f spread: %11.9f" % (self.price, self.Gap, self.spread))
            self.log("filled Bid orders %d with topbidprice=%f" % (filledBidOrders, topBidprice))
            self.log("filled Ask orders %d with topaskprice=%f" % (filledAskOrders, topAskprice))
            assert min(filledAskOrders,filledBidOrders) >= 0
            netfilledbid = filledBidOrders - filledAskOrders

            for a in range(filledBidOrders):
                self.BidQueue.popleft()
            for b in range(filledAskOrders):
                self.AskQueue.popleft()
            #self.price = (self.BidQueue[0]['price']+self.AskQueue[0]['price'])/2
            #self.log("middle price is %f" % self.price)


            if netfilledbid >= 0:
                for c in range(filledAskOrders):
                    newBidOrder = {"id":'0',"market":self.market,"type": "buy","volume": random.uniform(self.orderamount, self.orderamount * (1 + self.random)),"price": self.BidQueue[0]["price"] + self.spread}

                    result = self.executeOrder(self.ex, newBidOrder)
                    self.log("try to create %s bid order: %s result %s" % (self.ex,newBidOrder, result))

                    newBidOrder['id'] = self.GetResultOrderID(self.ex,result)
                    if newBidOrder['id'] != 0:
                        self.BidQueue.appendleft(newBidOrder) 

                    newAskOrder = {"id":'0',"market":self.market,"type": "sell","volume": random.uniform(self.orderamount* (1 - self.random), self.orderamount ),"price": self.AskQueue[0]["price"] - self.spread}

                    result = self.executeOrder(self.ex, newAskOrder)
                    self.log("try to create %s ask order: %s result %s" % (self.ex,newAskOrder, result))
                    newAskOrder['id'] = self.GetResultOrderID(self.ex, result)
                    if newAskOrder['id'] != 0:
                        self.AskQueue.appendleft(newAskOrder)

                for d in range(netfilledbid):
                    self.log("%s order canceled: %s result: %s" % (self.ex,self.AskQueue[-1],self.CancelOrder(self.ex,self.AskQueue[-1]['id'])))
                    self.AskQueue.pop()
                for e in range(netfilledbid):
                    newBidOrder = {"id": '0', "market": self.market, "type": "buy",
                                   "volume": random.uniform(self.orderamount, self.orderamount * (1 + self.random)),
                                   "price": self.BidQueue[-1]["price"] - self.spread}

                    result = self.executeOrder(self.ex, newBidOrder)
                    self.log("try to create %s bid order: %s result %s" % (self.ex,newBidOrder, result))
                    newBidOrder['id'] = self.GetResultOrderID(self.ex, result)
                    if newBidOrder['id'] != 0:
                        self.BidQueue.append(newBidOrder)

                    newAskOrder = {"id": '0', "market": self.market, "type": "sell",
                                   "volume": random.uniform(self.orderamount * (1 - self.random), self.orderamount),
                                   "price": self.AskQueue[0]["price"] - self.spread}

                    result = self.executeOrder(self.ex, newAskOrder)
                    self.log("try to create %s ask order: %s result %s" % (self.ex,newAskOrder, result))
                    newAskOrder['id'] = self.GetResultOrderID(self.ex, result)
                    if newAskOrder['id'] != 0:
                        self.AskQueue.appendleft(newAskOrder)

            if netfilledbid < 0:
                for f in range(filledBidOrders):
                    newBidOrder = {"id": '0', "market": self.market, "type": "buy",
                                   "volume": random.uniform(self.orderamount, self.orderamount * (1 + self.random)),
                                   "price": self.BidQueue[0]["price"] + self.spread}
                    result = self.executeOrder(self.ex, newBidOrder)
                    self.log("try to create %s bid order: %s result %s" % (self.ex,newBidOrder, result))

                    newBidOrder['id'] = self.GetResultOrderID(self.ex, result)
                    if newBidOrder['id'] != 0:
                        self.BidQueue.appendleft(newBidOrder)

                    newAskOrder = {"id": '0', "market": self.market, "type": "sell",
                                   "volume": random.uniform(self.orderamount * (1 - self.random), self.orderamount),
                                   "price": self.AskQueue[0]["price"] - self.spread}
                    result = self.executeOrder(self.ex, newAskOrder)
                    self.log("try to create %s ask order: %s result %s" % (self.ex,newAskOrder, result))

                    newAskOrder['id'] = self.GetResultOrderID(self.ex, result)
                    if newAskOrder['id'] != 0:
                        self.AskQueue.appendleft(newAskOrder)

                for g in range(-netfilledbid):
                    self.log("%s order canceled: %s result: %s" % (self.ex, self.BidQueue[-1], self.CancelOrder(self.ex, self.BidQueue[-1]['id'])))
                    self.BidQueue.pop()

                for h in range(-netfilledbid):
                    newBidOrder = {"id": '0', "market": self.market, "type": "buy",
                                   "volume": random.uniform(self.orderamount, self.orderamount * (1 + self.random)),
                                   "price": self.BidQueue[0]["price"] + self.spread}
                    result = self.executeOrder(self.ex, newBidOrder)
                    self.log("try to create %s bid order: %s result %s" % (self.ex, newBidOrder, result))

                    newBidOrder['id'] = self.GetResultOrderID(self.ex, result)
                    if newBidOrder['id'] != 0:
                        self.BidQueue.appendleft(newBidOrder)

                    newAskOrder = {"id": '0', "market": self.market, "type": "sell",
                                   "volume": random.uniform(self.orderamount * (1 - self.random), self.orderamount),
                                   "price": self.AskQueue[-1]["price"] + self.spread}

                    result = self.executeOrder(self.ex, newAskOrder)
                    self.log("try to create %s ask order: %s result %s" % (self.ex,newAskOrder, result))

                    newAskOrder['id'] = self.GetResultOrderID(self.ex, result)
                    if newAskOrder['id'] != 0:
                        self.AskQueue.append(newAskOrder)
            #update middle price after updateing the order queues
            self.price = (self.BidQueue[0]['price'] + self.AskQueue[0]['price']) / 2

        self.log(datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'))
        self.log("after review, middleprice: %11.9f, Gap: %11.9f spread: %11.9f" % (self.price,self.Gap,self.spread))
        self.log("Bid order numbers: %d, top Bid price：%11.9f" % (len(self.BidQueue), self.BidQueue[0]["price"]))
        self.log("Ask order numbers: %d, top Ask price: %11.9f" % (len(self.AskQueue), self.AskQueue[0]["price"]))
        return

    def log(self, text, path='./log/'):
        filename = path + self.ex + self.market + "maker" + datetime.strftime(datetime.now(), '%Y-%m-%d')
        print(text)
        with open(filename, 'a') as f:
            f.write(text + '\n')
        return

    def getextradingbalance(self,startdate, enddate=datetime.strptime('3000-12-31', '%Y-%m-%d'), market = {'ex':'yunbi','asset':'ANS','base':'CNY'}):
        with self.client.mysqlClient.cursor() as cursor:
            sql = "(SELECT SUM(`netbuy`), SUM(`netpaid`) FROM dailyreport WHERE `exchange` = '%s' and `quote` = '%s' and `base` = '%s' and `date` >= '%s' and date < '%s')" % (
                market['ex'], market['asset'], market['base'],datetime.strptime(startdate, '%Y-%m-%d') , enddate)
            self.log(sql)
            cursor.execute(sql)
            result = cursor.fetchall()
            self.client.mysqlClient.commit()
            return result

"""
    def log(self, text, path='./log/'):
        filename = path + "DataProcesser" + datetime.strftime(datetime.now(), '%Y-%m-%d')
        print(text)
        with open(filename, 'a') as f:
            f.write(text + '\n')
        return
"""



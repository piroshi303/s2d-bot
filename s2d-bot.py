import discord
import asyncio
import yaml
import pandas as pd
import urllib.request, urllib.error
from xml.sax.saxutils import unescape
from bs4 import BeautifulSoup

client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

async def background_loop(channel_id):
    with open('setting.yml', 'r') as rf:
        file = rf.read()
    settings = yaml.safe_load(file)
    bbsData = settings['shitaraba']

    await client.wait_until_ready()

    bbsInfo = BbsInfo(bbsData['category'], bbsData['sequence'], bbsData['thread_stop'])
    bbsInfo.checkBbs()

    num = bbsInfo.currentThreadNum + 1
    beforeThreadName = bbsInfo.currentThreadName
    currentThreadUrlResponse = bbsInfo.currentThreadUrlResponse

    while not client.is_closed:
        channel = client.get_channel(channel_id)

        bbsResponse = BbsResponse(currentThreadUrlResponse + str(num))

        if bbsResponse.isGetResponse == True:
            name = 'したらば: ' + bbsResponse.no

            if bbsData['noname'] != bbsResponse.name:
                name = name + ' - name: ' + bbsResponse.name

            await client.send_message(channel, name + '\n' + bbsResponse.comment)

            if num == bbsInfo.thread_stop:
                await asyncio.sleep(10)

                bbsInfo.checkBbs()

                currentThreadName = bbsInfo.currentThreadName
                currentThreadUrlRead = bbsInfo.currentThreadUrlRead
                currentThreadUrlResponse = bbsInfo.currentThreadUrlResponse

                num = 2

                await client.send_message(channel,
                                          '====================' + '`\n'
                                          + beforeThreadName + 'が' + str(bbsInfo.thread_stop) + 'まで埋まりました。' + '\n'
                                          + '次スレは以下になります。' + '\n'
                                          + currentThreadName + ': ' + currentThreadUrlRead + '\n'
                                          + '====================')

                beforeThreadName = bbsInfo.currentThreadName
            else:
                num += 1

        await asyncio.sleep(10)

class BbsInfo:
    __category = ''
    __sequence = ''

    thread_stop = 0

    currentThreadId = ''
    currentThreadName = ''
    currentThreadNum = 0
    currentThreadUrlRead = ''
    currentThreadUrlResponse = ''

    def __init__(self, category, sequence, thread_stop):
        self.__category = category
        self.__sequence = sequence
        self.thread_stop = thread_stop

    def checkBbs(self):
        # Const
        CATEGORY = 'category'
        SEQUENCE = 'sequence'
        URL_SUB = 'http://jbbs.shitaraba.net/' + CATEGORY + '/' + SEQUENCE + '/subject.txt'
        URL_THR = 'http://jbbs.shitaraba.net/bbs/read.cgi/' + CATEGORY + '/' + SEQUENCE + '/'
        URL_RES = 'http://jbbs.shitaraba.net/bbs/rawmode.cgi/' + CATEGORY + '/' + SEQUENCE + '/'
        EUC = 'euc_jp'
        CGI = '.cgi'

        # Tuple
        columns = ('id', 'name_count', 'name', 'count', 'url1', 'url2', 'flag')

        subject_url = URL_SUB.replace(CATEGORY, self.__category).replace(SEQUENCE, self.__sequence)

        dataFrame = pd.DataFrame(pd.read_csv(subject_url, names=(columns[0], columns[1]), encoding=EUC))

        if dataFrame.duplicated().any() == True:
            dataFrame = dataFrame.drop_duplicates().sort_values(by=columns[0], ascending=False)
            dataFrame = dataFrame.reset_index(drop=True)

        dataFrame[columns[0]] = dataFrame[columns[0]].str.replace(CGI, '')
        dataFrame[columns[2]] = pd.Series(dataFrame[columns[1]].str.rsplit('(', expand=True, n=1).get(0))
        dataFrame[columns[3]] = pd.Series(dataFrame[columns[1]].str.rsplit('(', expand=True, n=1).get(1).str.replace('(', '').str.replace(')', '')).astype(int)
        dataFrame[columns[4]] = pd.Series(URL_THR.replace(CATEGORY, self.__category).replace(SEQUENCE, self.__sequence) + dataFrame[columns[0]] + '/')
        dataFrame[columns[5]] = pd.Series(URL_RES.replace(CATEGORY, self.__category).replace(SEQUENCE, self.__sequence) + dataFrame[columns[0]] + '/')

        dataFrame[columns[6]] = dataFrame[columns[3]].where(dataFrame[columns[3]] != self.thread_stop, False).where(dataFrame[columns[3]] == self.thread_stop, True)
        currentDataFrame = dataFrame.where(dataFrame[columns[3]] == dataFrame[columns[3]].where(dataFrame[columns[6]] == True).max()).dropna()

        self.currentThreadId = currentDataFrame[columns[0]].values[0]
        self.currentThreadName = currentDataFrame[columns[2]].values[0]
        self.currentThreadNum = int(currentDataFrame[columns[3]].values[0])
        self.currentThreadUrlRead = currentDataFrame[columns[4]].values[0]
        self.currentThreadUrlResponse = currentDataFrame[columns[5]].values[0]

class BbsResponse:
    no = ''
    name = ''
    e_mail = ''
    data_time = ''
    comment = ''
    title = ''
    id = ''
    isGetResponse = False

    def __init__(self, url):
        # Const
        EUC = 'euc_jp'
        SPLIT_TEXT = '<>'

        # Tuple
        keys = ('no', 'name', 'e_mail', 'date_time', 'comment', 'title', 'id')

        opener = urllib.request.build_opener()

        try:
            r = opener.open(url)
            content = r.read().decode(EUC)
            contents = content.split('\n')

            if content != '':
                self.isGetResponse = True

                buf = contents[0].split(SPLIT_TEXT)

                if len(buf) > 7:
                    while len(buf) > 7:
                        buf[4] = buf[4] + SPLIT_TEXT + buf[5]
                        del buf[5]

                dic = dict(zip(keys, buf))

                # Remove <font>tag
                soup_name = BeautifulSoup(dic[keys[1]], 'html.parser')
                while (soup_name.font):
                    soup_name.font.unwrap()

                dic[keys[1]] = soup_name.prettify()

                # Remove <a>tag
                soup_comment = BeautifulSoup(dic[keys[4]], 'html.parser')
                while (soup_comment.a):
                    soup_comment.a.unwrap()

                # Remove <br>tag
                while (soup_comment.br):
                    soup_comment.br.unwrap()

                dic[keys[4]] = soup_comment.prettify()

                self.no = dic[keys[0]]
                self.name = dic[keys[1]].replace('\n', '')
                self.e_mail = dic[keys[2]]
                self.data_time = dic[keys[3]]
                self.comment = unescape(dic[keys[4]])
                self.title = dic[keys[5]]
                self.id = dic[keys[6]]

            else:
                self.isGetResponse = False

        except urllib.error.HTTPError:
            self.isGetResponse = False

with open('setting.yml', 'r') as fp:
    file = fp.read()
data = yaml.safe_load(file)

client.loop.create_task(background_loop(data['channel_id']))
client.run(data['token'])


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
    print('Logged in as' + client.user.name)
    print(client.user.id)
    print('------')

async def background_loop(channel_id):
    '''
    definition name:
        background_loop(channel_id)
    description:
        clinet起動時に実行されるBackground Loop
    argument:
        'channel_id' -- Discordの書き込み先Text Channel Id
    '''

    await client.wait_until_ready()

    # Const
    YML_SHITARABA = 'shitaraba'
    YML_SHITARABA_CATEGORY = 'category'
    YML_SHITARABA_SEQUENCE = 'sequence'
    YML_SHITARABA_THREAD_STOP = 'thread_stop'
    YML_SHITARABA_NONAME = 'noname'

    ''' ==============================================
    設定値の取得
    ============================================== '''
    with open('setting.yml', 'r') as rf:
        file = rf.read()

    ymlBaseValue = yaml.safe_load(file)
    ymlBbsValue = ymlBaseValue[YML_SHITARABA]

    bbsInfo = BbsInfo(ymlBbsValue[YML_SHITARABA_CATEGORY], ymlBbsValue[YML_SHITARABA_SEQUENCE], ymlBbsValue[YML_SHITARABA_THREAD_STOP])

    ''' ==============================================
    したらば掲示板情報の取得
    ============================================== '''
    bbsInfo.checkBbs()

    currentThreadUrlResponse = bbsInfo.currentThreadUrlResponse
    num = bbsInfo.currentThreadNum + 1

    beforeThreadName = bbsInfo.currentThreadName

    while not client.is_closed:
        channel = client.get_channel(channel_id)

        bbsResponse = BbsResponse(currentThreadUrlResponse + str(num))

        if bbsResponse.isGetResponse == True:
            ''' ==============================================
            レスのヘッダー情報作成
            ============================================== '''
            name = '【' + bbsInfo.currentThreadName + ': ' + bbsResponse.response_no

            # 名無しではない場合、名称を追加
            if ymlBbsValue[YML_SHITARABA_NONAME] != bbsResponse.name:
                name = name + ' - ' + bbsResponse.name

            name = name + '】'

            await client.send_message(channel, name + '\n' + bbsResponse.response)

            ''' ==============================================
            スレッドが書き込み上限に達した場合は掲示板情報を更新
            ============================================== '''
            if num == bbsInfo.thread_stop:
                await asyncio.sleep(10)

                # したらば掲示板情報の更新
                bbsInfo.checkBbs()

                currentThreadName = bbsInfo.currentThreadName
                currentThreadUrlResponse = bbsInfo.currentThreadUrlResponse

                # レスカウンタの初期化
                num = 2

                # スレッドの変更通知
                await client.send_message(channel, beforeThreadName + 'が' + str(bbsInfo.thread_stop) + 'まで埋まりました。' + '\n'
                                          + '次スレは' + currentThreadName + 'です。')

                # 次回利用するため
                beforeThreadName = bbsInfo.currentThreadName

            else:
                # 次スレに移動
                num += 1

        await asyncio.sleep(10)

class BbsInfo:
    '''
    class Name:
        BbsInfo
    description:
        したらば掲示板の情報を取得します。
    '''

    # private variable
    __category = ''
    __sequence = ''

    # public variable
    thread_stop = 0
    currentThreadId = ''
    currentThreadName = ''
    currentThreadNum = 0
    currentThreadUrlRead = ''
    currentThreadUrlResponse = ''

    # Construct
    def __init__(self, category, sequence, thread_stop):
        self.__category = category
        self.__sequence = sequence
        self.thread_stop = thread_stop

    def checkBbs(self):
        '''
        checkBbs(self)
        'channel_id' -- Discordの書き込み先Text Channel Id
        '''

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

        ''' ==============================================
        掲示板情報の取得
        ============================================== '''
        # subject.txtから掲示板一覧を取得
        subject_url = URL_SUB.replace(CATEGORY, self.__category).replace(SEQUENCE, self.__sequence)
        dataFrame = pd.DataFrame(pd.read_csv(subject_url, names=(columns[0], columns[1]), encoding=EUC))

        # ソートと重複削除
        if dataFrame.duplicated().any() == True:
            dataFrame = dataFrame.drop_duplicates().sort_values(by=columns[0], ascending=False)
            dataFrame = dataFrame.reset_index(drop=True)

        # 掲示板ID
        dataFrame[columns[0]] = dataFrame[columns[0]].str.replace(CGI, '')

        # 掲示板名
        dataFrame[columns[2]] = pd.Series(dataFrame[columns[1]].str.rsplit('(', expand=True, n=1).get(0))

        # 書き込み数
        dataFrame[columns[3]] = pd.Series(dataFrame[columns[1]].str.rsplit('(', expand=True, n=1).get(1).str.replace('(', '').str.replace(')', '')).astype(int)

        # スレッドのURL（API）
        dataFrame[columns[4]] = pd.Series(URL_THR.replace(CATEGORY, self.__category).replace(SEQUENCE, self.__sequence) + dataFrame[columns[0]] + '/')

        # レスのURL（API）
        dataFrame[columns[5]] = pd.Series(URL_RES.replace(CATEGORY, self.__category).replace(SEQUENCE, self.__sequence) + dataFrame[columns[0]] + '/')

        # スレッドストップフラグ
        dataFrame[columns[6]] = dataFrame[columns[3]].where(dataFrame[columns[3]] != self.thread_stop, False).where(dataFrame[columns[3]] == self.thread_stop, True)

        # 書き込み可能なスレッドのうち最も古い掲示板（チェック対象）を取得
        currentDataFrame = dataFrame.where(dataFrame[columns[3]] == dataFrame[columns[3]].where(dataFrame[columns[6]] == True).max()).dropna()

        # 書き込み可能なスレッドで最も古い掲示板情報（=カレントスレッド）の取得
        self.currentThreadId = currentDataFrame[columns[0]].values[0]
        self.currentThreadName = currentDataFrame[columns[2]].values[0]
        self.currentThreadNum = int(currentDataFrame[columns[3]].values[0])
        self.currentThreadUrlRead = currentDataFrame[columns[4]].values[0]
        self.currentThreadUrlResponse = currentDataFrame[columns[5]].values[0]

class BbsResponse:
    '''
    class Name:
        BbsResponse
    description:
        したらば掲示板の書き込みを取得します。
    '''

    # public variable
    response_no = ''
    name = ''
    e_mail = ''
    data_time = ''
    response = ''
    title = ''
    author_id = ''
    isGetResponse = False    # レス取得フラグ: True = 取得 ／ False = 未取得

    def __init__(self, url):
        # Const
        EUC = 'euc_jp'
        SPLIT_TEXT = '<>'

        # Tuple
        keys = ('response_no', 'name', 'e_mail', 'date_time', 'response', 'title', 'author_id')

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

                self.response_no = dic[keys[0]]
                self.name = dic[keys[1]].replace('\n', '')
                self.e_mail = dic[keys[2]]
                self.data_time = dic[keys[3]]
                self.response = unescape(dic[keys[4]])
                self.title = dic[keys[5]]
                self.author_id = dic[keys[6]]

            else:
                self.isGetResponse = False

        except urllib.error.HTTPError:
            self.isGetResponse = False

if __name__ == '__main__':
    with open('setting.yml', 'r') as fp:
        file = fp.read()

    ymlBaseValue = yaml.safe_load(file)
    ymlBbsValue = ymlBaseValue['shitaraba']

    token = ymlBaseValue['token']
    channel_id = ymlBaseValue['channel_id']


    client.loop.create_task(background_loop(channel_id))
    client.run(token)

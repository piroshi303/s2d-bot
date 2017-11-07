# s2d-bot

[![DUB](https://img.shields.io/dub/l/vibe-d.svg)]()
[![python](https://img.shields.io/badge/python-3.5-blue.svg)]()
[![pyflakes](https://img.shields.io/badge/pyflakes-passing-brightgreen.svg)](https://pypi.python.org/pypi/pyflakes)

## はじめに
当プログラムは、[したらば掲示板](https://rentalbbs.shitaraba.com/)に書き込まれた内容を、そのまま[Disacord](https://discordapp.com/)のTextChatに書き込みを行うChatbotです。
[Xsplit](https://www.xsplit.com/ja/)や[OBS](https://obsproject.com/)での配信時に[Discord StreamKit Overlay](https://streamkit.discordapp.com/overlay)を利用してしたらば掲示板の書き込み内容を配信画面に取り込むことを目的にしているプログラムです。


## 事前準備
### 前提条件
Python version 3.5.xがインストールされている必要があります。  
インストールされているPythonのversionは、以下のコマンドで確認してください。  
`python --version`

### Pythonパッケージのインストール
当ファイルを展開したフォルダ内で下記コマンドを実行し、必要なPythonパッケージをインストールしてください。  
`pip install -r requirements.txt`

パッケージは[discord.py](https://github.com/Rapptz/discord.py/blob/async/docs/api.rst)を利用しています。

### setting.xmlの編集
実行前にsetting.xmlを編集してください。  

|Item Name|Value|
|:-|:-|
|shitaraba: category|したらば掲示板のカテゴリ|
|shitaraba: sequence|したらば掲示板の番地|
|shitaraba: thread_stop|したらば掲示板で設定しているスレッド書き込み上限|
|shitaraba: noname|したらば掲示板で設定している名無しの名前|
|token|Discordに登録したボットのtokenコード|
|channel_id|書き込みを反映したいDiscord: TextChannelのId|

[Pages link](https://piroshi303.github.io/s2d-bot/)

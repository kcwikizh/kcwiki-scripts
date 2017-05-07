# kcwiki-scripts
Some scripts for kcwiki routine maintenance

## Usage

### 定时任务

运行与 crontab 类似的定时任务(前台)： `python main.py plan`

默认包含的任务有：

+ 更新 start2 数据
+ 更新字幕
+ 更新本地舰船数据
+ 更新 revise 数据

### 更新字幕
+ 更新前需要使用更新舰船命令： `python main.py update:ships`
+ 更新字幕（仅运行，不部署到线上）： `python main.py update:subtitles`
+ 更新并部署到线上环境：`python main.py update:subtitles deploy`

### 更新 revise 数据
+ 下载舰娘音频：`python main.py revise:download`
+ 更新舰娘 revise 数据：`python main.py revise --version=v3`

### 更新 start2 数据
+ 更新 start2 数据并上传到服务器： `python main.py fetch:start2`

### 解包
+ 下载并反混淆 Core.swf : `python main.py decompile`
+ 下载并解包 BattleMain.swf(需要 ffdec): `python main.py battle:swf`

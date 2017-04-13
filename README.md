# kcwiki-scripts
Some scripts for kcwiki routine maintenance

## Usage

### 更新字幕
+ 更新前需要使用更新舰船命令： `python main.py update:ships`
+ 更新字幕（仅运行，不部署到线上）： `python main.py update:subtitles`
+ 更新并部署到线上环境：`python main.py update:subtitles deploy`

### 更新 revise 数据
+ 下载舰娘音频：`python main.py revise:download`
+ 更新舰娘 revise 数据：`python main.py revise --version=v3`

### 更新 start2 数据
+ 更新 start2 数据并上传到服务器： `python main.py fetch:start2`



# -*- coding: utf-8 -*-

"""
Copyright (c) 2021 RootManDev.

** Korean Remark **

디스코드 음악 봇 입니다.

요구사항 : 

python 3.5+ 
Discord.py
Pynacl
Youtube-dl
ffempeg.exe

"""

import asyncio
import functools
import itertools
import math
import random
import requests
from bs4 import BeautifulSoup

import discord
import youtube_dl
from async_timeout import timeout
from discord.ext import commands

rankNumber = []
chart = []
header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko'}
req = requests.get('https://www.melon.com/chart/week/index.htm', headers = header) 
html = req.text
parse = BeautifulSoup(html, 'html.parser')
      
titles = parse.find_all("div", {"class": "ellipsis rank01"}) 
singers = parse.find_all("div", {"class": "ellipsis rank02"}) 
       
title = []
singer = []

for t in titles:
    title.append(t.find('a').text)
       
for s in singers:
    singer.append(s.find('span', {"class": "checkEllipsis"}).text)      

for ranking in range(50):
    chart.append('%s - %s\n'%(title[ranking], singer[ranking]))
    rankNumber.append('%d위'%(ranking+1))


youtube_dl.utils.bug_reports_message = lambda: ''


class VoiceError(Exception):
    pass

class YTDLError(Exception):
    pass

class YTDLSource(discord.PCMVolumeTransformer):
    
    # youtube-dl의 설정입니다. youtube-dl을 통해 음원을 가져옵니다.

    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        
        # FFMPEG의 설정입니다.

        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }


    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        # Youtube-dl에서 가져올 변수 목록입니다.

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}**'.format(self)

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):

        # Play와 관련된 함수입니다.
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('`{}`와(과) 일치하는 검색결과가 없습니다.'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None 
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('`{}`와(과) 일치하는 검색결과가 없습니다.'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('`{}`를 fetch할 수 없습니다.'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('`{}`와(과) 일치하는 검색결과가 없습니다.'.format(webpage_url))

        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS), data=info)


    @classmethod
    async def search_source(self, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):

        # Search와 관련된 함수입니다.

        self.bot=bot
        channel = ctx.channel
        loop = loop or asyncio.get_event_loop()

        self.search_query = '%s%s:%s' % ('ytsearch', 10, ''.join(search))

        partial = functools.partial(self.ytdl.extract_info, self.search_query, download=False, process=False)
        info = await loop.run_in_executor(None, partial)

        self.search = {}
        self.search["title"] = f'**{search}**의 검색 결과입니다.'
        self.search["type"] = 'rich'
        self.search["color"] = 7506394
        self.search["author"] = {'name': f'{ctx.author.name}', 'url': f'{ctx.author.avatar_url}','icon_url': f'{ctx.author.avatar_url}'}

        lst = []
        count = 0
        e_list = []
        for e in info['entries']:

            VId = e.get('id')
            VUrl = 'https://www.youtube.com/watch?v=%s' % (VId)
            lst.append(f'`{count + 1}.` [{e.get("title")}]({VUrl})\n')
            count += 1
            e_list.append(e)

        lst.append('\n**선택할 음악의 숫자를 입력하세요. `취소`를 입력하여 취소할 수 있습니다.**')
        self.search["description"] = "\n".join(lst)

        em = discord.Embed.from_dict(self.search)
        await ctx.send(embed=em, delete_after=45.0)

        def check(msg):
            return msg.content.isdigit() == True and msg.channel == channel or msg.content == '취소' or msg.content == 'cnlth' or msg.content == 'cancel'

        try:
            m = await self.bot.wait_for('message', check=check, timeout=45.0)

        except asyncio.TimeoutError:
            rtrn = 'timeout'

        else:
            if m.content.isdigit() == True:
                sel = int(m.content)
                if 0 < sel <= 10:
                    for key, value in info.items():
                        if key == 'entries':
                            """data = value[sel - 1]"""
                            VId = e_list[sel-1]['id']
                            VUrl = 'https://www.youtube.com/watch?v=%s' % (VId)
                            partial = functools.partial(self.ytdl.extract_info, VUrl, download=False)
                            data = await loop.run_in_executor(None, partial)
                    rtrn = self(ctx, discord.FFmpegPCMAudio(data['url'], **self.FFMPEG_OPTIONS), data=data)
                else:
                    rtrn = 'sel_invalid'
            elif m.content == 'cancel':
                rtrn = 'cancel'
            else:
                rtrn = 'sel_invalid'

        return rtrn

    @staticmethod
    def parse_duration(duration: int):
        
        # 가져온 영상의 길이를 시, 분, 초 단위로 나누는 작업입니다.

        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{}일'.format(days))
        if hours > 0:
            duration.append('{}시간'.format(hours))
        if minutes > 0:
            duration.append('{}분'.format(minutes))
        if seconds > 0:
            duration.append('{}초'.format(seconds))

        return ' '.join(duration)

class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self): 

        # 음악을 재생했을 때, 나오는 카드에 관한 함수입니다. 
        # 이해가 잘 안될경우, 프로그램을 실행한 뒤 아무 노래나 재생해보시면 이해하실 수 있습니다.
        # 디스코드는 위와 같은 카드를 'Embed'로 호출합니다.

        embed = (discord.Embed(title='현재 재생 중:',
                               description='```css\n{0.source.title}\n```'.format(self),
                               color=discord.Color.blurple())
                 .add_field(name='재생 길이', value=self.source.duration)
                 .add_field(name='신청', value=self.requester.mention)
                 .add_field(name='게시자', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed

class SongQueue(asyncio.Queue):

    # 재생목록에 관한 함수입니다.
     
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]

class VoiceState:
    
    # 음악봇의 음성과 관련된 클래스입니다.

    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
         
        while True:
            self.next.clear()

            if self.loop == False:

                try:
                    async with timeout(6000):
                        
                        # 얼마의 시간동안 입력이 없으면 잠수에 들어갈건지 설정하는 구간입니다.
                        # 기본 단위는 1초입니다. 따라서 600은 10분입니다.

                        self.current = await self.songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return
                self.current.source.volume = self._volume
                self.voice.play(self.current.source, after=self.play_next_song)
                await self.current.source.channel.send(embed=self.current.create_embed())

            elif self.loop == True:
                self.now = discord.FFmpegPCMAudio(self.current.source.stream_url, **YTDLSource.FFMPEG_OPTIONS)
                self.voice.play(self.now, after=self.play_next_song)

            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()

        if self.voice:
            await self.voice.disconnect()
            self.voice = None

class Music(commands.Cog):

    # 명령어와 관련된 클래스입니다.
    # 명령어를 추가할 때는 name인자 옆에 alises=[]를 입력하면 됩니다.

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('이 명령어는 DM 채널에서 사용할 수 없습니다')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send('오류가 발생했습니다 : {}'.format(str(error)))

    # 음성 채널에 입장하는 명령어입니다.

    @commands.command(name='join', invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    # 검색 명령어입니다. 

    @commands.command(name='검색',alises=['rjator','search'])
    async def _search(self, ctx: commands.Context, *, search: str):

        async with ctx.typing():
            try:
                source = await YTDLSource.search_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send('명령을 수행 중 오류가 발생했습니다 : {}'.format(str(e)))
            else:
                if source == 'sel_invalid':
                    await ctx.send('Invalid selection')
                elif source == 'cancel':
                    await ctx.send(':white_check_mark:')
                elif source == 'timeout':
                    await ctx.send(':alarm_clock: **Time\'s up bud**')
                else:
                    if not ctx.voice_state.voice:
                        await ctx.invoke(self._join)

                    song = Song(source)
                    await ctx.voice_state.songs.put(song)
                    await ctx.send('{}를 재생합니다!'.format(str(source)))

    # 봇을 음성채널로 소환하는 명령어입니다.          
         
    @commands.command(name='소환')
    @commands.has_permissions(manage_guild=True)
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):

        if not channel and not ctx.author.voice:
            raise VoiceError('소환할 채널을 입력하거나 소환할 채널에 들어가있어야 합니다.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    # 봇을 음성채널에서 내보내는 명령어입니다.

    @commands.command(name='나가', aliases=['disconnect','skrk','leave'])
    @commands.has_permissions(manage_guild=True)
    async def _leave(self, ctx: commands.Context):
        

        if not ctx.voice_state.voice:
            return await ctx.send('음성채널에 들어가있지 않습니다.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]
    
    # 볼륨을 설정하는 명령어입니다.

    @commands.command(name='볼륨', aliases=['volume','v','qhffba','ㅍ'])
    async def _volume(self, ctx: commands.Context, *, volume: int):
        

        if not ctx.voice_state.is_playing:
            return await ctx.send('재생 중인 음악이 없습니다.')

        if 0 > volume > 100:
            return await ctx.send('볼륨은 0에서 100 사이여야 합니다.')

        ctx.voice_state.current.source.volume = volume / 100
        ctx.voice_state.volume = volume /100
        await ctx.send('볼륨을 {}%로 설정했습니다.'.format(volume))
    
    # 현재 재생중인 음악을 알려주는 명령어입니다.

    @commands.command(name='n', aliases=['현재', '재생중'])
    async def _now(self, ctx: commands.Context):

        await ctx.send(embed=ctx.voice_state.current.create_embed())
    
    # 재생 중인 음악을 일시정지하는 명령어입니다.

    @commands.command(name='일시정지',aliases=['pause'])
    @commands.has_permissions(manage_guild=True)
    async def _pause(self, ctx: commands.Context):


        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯')
    
    # 일시정지한 음악을 다시 재생하는 명령어입니다.

    @commands.command(name='재개')
    @commands.has_permissions(manage_guild=True)
    async def _resume(self, ctx: commands.Context):
    
        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯')

    # 음악을 정지하는 명령어입니다.

    @commands.command(name='정지')
    @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: commands.Context):
       

        ctx.voice_state.songs.clear()

        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹')

    @commands.command(name='스킵',aliases=['s','skip','ㄴ','tmzlq'])
    async def _skip(self, ctx: commands.Context):
        await ctx.message.add_reaction('⏭')
        ctx.voice_state.skip()
        
        if not ctx.voice_state.is_playing:
            return await ctx.send('음악 재생중이 아닙니다.')

    # 재생목록을 나타내는 명령어입니다.

    @commands.command(name='재생목록',aliases=['q','queue'])
    async def _queue(self, ctx: commands.Context, *, page: int = 1):

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('재생목록이 비었습니다.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        embed = (discord.Embed(description='재생목록 **{}개:**\n\n{}'.format(len(ctx.voice_state.songs), queue))
                 .set_footer(text='페이지 {}/{}'.format(page, pages)))
        await ctx.send(embed=embed)

    # 재생목록을 섞는 명령어입니다.

    @commands.command(name='섞기',aliases=['shuffle','셔플'])
    async def _shuffle(self, ctx: commands.Context):


        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('재생목록이 비었습니다.')

        ctx.voice_state.songs.shuffle()
        await ctx.message.add_reaction('✅')

    # 음악을 반복하는 명령어입니다.
    # 명령어를 다시 입력하면 반복을 해제합니다.

    @commands.command(name='삭제',aliases=['remove'])
    async def _remove(self, ctx: commands.Context, index: int):
        

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('재생목록이 비었습니다.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='반복',aliases=['loop','repeat'])
    async def _loop(self, ctx: commands.Context):


        if not ctx.voice_state.is_playing:
            return await ctx.send('실행 중인 노래가 없습니다.')

        ctx.voice_state.loop = not ctx.voice_state.loop
        await ctx.message.add_reaction('✅')

    # 노래를 검색하여 가장 매칭되는 음악을 재생하는 명령어입니다.

    @commands.command(name='재생',aliases = ['p','play','wotod','ㅔ'])
    async def _play(self, ctx: commands.Context, *, search: str):

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send('요청에 응답하는 중 오류가 발생했습니다 : {}'.format(str(e)))
            else:
                song = Song(source)

                await ctx.voice_state.songs.put(song)
                await ctx.send('🎵{}를 재생합니다!'.format(str(source)))

    # 명령어 도움말에 관련된 명령어입니다.

    @commands.command(name='명령어',aliases = ['command','도움말'])
    async def _help(self, ctx:commands.context):
        embed=discord.Embed(title="명령어", description="모든 명령어는 ';'로 시작합니다.", color=0xec79de)
        embed.add_field(name="join / 소환", value="봇이 음성 채널로 입장합니다.", inline=False)
        embed.add_field(name="재생 / play / wotod / p / ㅔ <음악 이름>", value="음악을 재생합니다.", inline=False)
        embed.add_field(name="나가 / disconnect / skrk / leave", value="봇이 음성 채널을 떠납니다.", inline=False)
        embed.add_field(name="볼륨 / qhffba / v / volume / ;ㅍ", value="볼륨을 조절합니다.", inline=False)
        embed.add_field(name="n / 현재 재생중", value="현재 재생 중인 음악을 확인합니다.", inline=False)
        embed.add_field(name="일시정지 / pause", value="음악을 일시 정지합니다.", inline=False)
        embed.add_field(name="정지", value="음악을 정지합니다.", inline=False)
        embed.add_field(name="재개", value="음악을 다시 재생합니다.", inline=False)
        embed.add_field(name="스킵 / s / skip / tmzlq / ㄴ", value="음악을 스킵합니다.", inline=False)
        embed.add_field(name="재생목록 / q / queue", value="재생 목록을 보여줍니다.", inline=False)
        embed.add_field(name="셔플 / shuffle / 섞기", value="재생 목록을 셔플합니다.", inline=False)
        embed.add_field(name="삭제 / remove", value=" 음악을 삭제합니다.", inline=False)
        embed.add_field(name="반복 / loop / repeat", value="음악을 반복재생합니다.", inline=False)
        embed.add_field(name="검색 / search / 검색 / rjator", value=" 음악을 검색합니다.", inline=False)
        embed.add_field(name="멜론차트 / 멜론 / melon" ,value="멜론차트를 검색합니다.멜론차트(숫자)로 페이지를 넘길 수 있습니다.",inline=False)
        await ctx.send(embed=embed)

    # 멜론차트를 불러오는 명령어입니다.
    # 50등까지 가져옵니다.

    @commands.command(name='멜론차트',aliases=['멜론','melon','apffhs'])
    async def melon1(self, ctx: commands.Context):

        ranking = 0   
        page1 = discord.Embed(title = "멜론차트🏆️", description ="", color=0x58FA58)
        page1.set_thumbnail(url="https://ww.namu.la/s/02ccf2ac9d3d90e3175520e9cab55359b5afa9a05d36aea5002ec0206271b4700da4dc3c9b3ff0f768913d4bcb440cd9477617e1942571b7e43d89956b3f404302249ff67251b7b3e0266d0e87cd088e508fae4429335500f42c4bad0c2f333a")
        for ranking in range(10):
            page1.add_field(name=rankNumber[ranking],value=chart[ranking],inline=False)
            page1.set_footer(text='페이지 1/5')
        await ctx.send(embed=page1)
 
    @commands.command(name='멜론2',aliases=['멜론차트2','melon2'])
    async def melon2(self, ctx: commands.Context):

        ranking = 0
        page2 = discord.Embed(title = "멜론차트🏆️", description ="", color=0x58FA58)
        page2.set_thumbnail(url="https://ww.namu.la/s/02ccf2ac9d3d90e3175520e9cab55359b5afa9a05d36aea5002ec0206271b4700da4dc3c9b3ff0f768913d4bcb440cd9477617e1942571b7e43d89956b3f404302249ff67251b7b3e0266d0e87cd088e508fae4429335500f42c4bad0c2f333a")
        for ranking in range(10,20):
            page2.add_field(name=rankNumber[ranking],value=chart[ranking],inline=False)
            page2.set_footer(text="페이지 2/5")       
        await ctx.send(embed=page2)
    
    @commands.command(name='멜론3',aliases=['apffhs3','멜론차트3','melon3'])
    async def melon3(self,ctx: commands.Context):
        ranking = 0
        page3 = discord.Embed(title = "멜론차트🏆️", description ="", color=0x58FA58)
        page3.set_thumbnail(url="https://ww.namu.la/s/02ccf2ac9d3d90e3175520e9cab55359b5afa9a05d36aea5002ec0206271b4700da4dc3c9b3ff0f768913d4bcb440cd9477617e1942571b7e43d89956b3f404302249ff67251b7b3e0266d0e87cd088e508fae4429335500f42c4bad0c2f333a")
        for ranking in range(20,30):
            page3.add_field(name=rankNumber[ranking],value=chart[ranking],inline=False)
            page3.set_footer(text="페이지 3/5")
        await ctx.send(embed=page3)

    @commands.command(name='멜론4', aliases=['melon4','apffhs4','멜론차트4'])
    async def melon4(self, ctx:commands.Context):
        ranking = 0
        page4 = discord.Embed(title = "멜론차트🏆️", description ="", color=0x58FA58)
        page4.set_thumbnail(url="https://ww.namu.la/s/02ccf2ac9d3d90e3175520e9cab55359b5afa9a05d36aea5002ec0206271b4700da4dc3c9b3ff0f768913d4bcb440cd9477617e1942571b7e43d89956b3f404302249ff67251b7b3e0266d0e87cd088e508fae4429335500f42c4bad0c2f333a")
        for ranking in range(30,40):
            page4.add_field(name=rankNumber[ranking],value=chart[ranking],inline=False)
            page4.set_footer(text="페이지 4/5")
        await ctx.send(embed=page4)

    @commands.command(name='멜론5', aliases=['melon5','apffhs5','멜론차트5'])
    async def melon5(self, ctx:commands.Context):
        ranking = 0
        page5 = discord.Embed(title = "멜론차트🏆️", description ="", color=0x58FA58)
        page5.set_thumbnail(url="https://ww.namu.la/s/02ccf2ac9d3d90e3175520e9cab55359b5afa9a05d36aea5002ec0206271b4700da4dc3c9b3ff0f768913d4bcb440cd9477617e1942571b7e43d89956b3f404302249ff67251b7b3e0266d0e87cd088e508fae4429335500f42c4bad0c2f333a")
        for ranking in range(40,50):
            page5.add_field(name=rankNumber[ranking],value=chart[ranking],inline=False)
            page5.set_footer(text="페이지 5/5")
        await ctx.send(embed=page5)

    # 봇의 음성채널 존재 유무에 관한 경고입니다.

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('음성채널에 입장해주세요.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('봇이 이미 음성채널에 들어와있습니다.')


bot = commands.Bot(';', description='디스코드 음악 봇 무직입니다.')
bot.add_cog(Music(bot))


@bot.event
async def on_ready():
    print('Logged in as:\n{0.user.name}\n{0.user.id}'.format(bot))

bot.run('Token')

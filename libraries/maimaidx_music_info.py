import copy
from pathlib import Path
from typing import List, Optional, Union, Any, Sequence, Dict, MutableSequence, cast
from PIL import Image, ImageDraw
from libraries.config import maimaidir, SIYUAN, TBFONT, fcl, fsl, achievementList, plate_to_dx_version, platecn, version_map, Root, BOTNAME, score_Rank_l, score_Rank, combo_rank, sync_rank, ratingdir, platedir
from .image import DrawText, image_to_base64, music_picture, text_to_image, rounded_corners
from .maimaidx_api_data import maiApi
from .maimaidx_error import *
from .maimaidx_model import ChartInfo, PlayInfoDefault, PlayInfoDev, UserInfo, Music
from .maimaidx_music import mai
import traceback
from .maimai_best_50 import coloumWidth, changeColumnWidth, computeRa, ScoreBaseImage, dxScore

# genre 到图片名的映射
category = {
    'POPS&ANIME': 'pops',
    'niconico': 'nico',
    '東方Project': 'toho',
    'VARIETY': 'variety',
    'イロドリミドリ': 'irodori',
    'maimai': 'maimai',
    'オンゲキ&CHUNITHM': 'ongeki',
    'ゲキマイ': 'gekimai',
    'ORIGINAL': 'original',
    "WORLD'S END": 'worldsend',
}

def newbestscore(song_id: str, lv: int, value: int, bestlist: List[ChartInfo]) -> int:
    for v in bestlist:
        if song_id == str(v.song_id) and lv == v.level_index:
            if value >= v.ra:
                return value - v.ra
            else:
                return 0
    return value - bestlist[-1].ra

async def draw_music_info(music: Music, level_index: Optional[int] = None) -> Union[str, Image.Image]:
    """
    查看谱面
    
    Params:
        `music`: 曲目模型
        `level_index`: 难度索引
    Returns:
        `Union[str, Image.Image]`
    """
    try:
        im = Image.open(maimaidir / 'song_bg.png').convert('RGBA')
        dr = ImageDraw.Draw(im)
        mr = DrawText(dr, SIYUAN)
        tb = DrawText(dr, TBFONT)

        default_color = (124, 130, 255, 255)

        im.alpha_composite(Image.open(maimaidir / 'logo.png').resize((249, 120)), (65, 25))
        if music.basic_info and music.basic_info.is_new:
            im.alpha_composite(Image.open(maimaidir / 'UI_CMN_TabTitle_NewSong.png').resize((249, 120)), (940, 100))
        songbg = Image.open(music_picture(music.id)).resize((280, 280))
        im.alpha_composite(rounded_corners(songbg, 17, (True, False, False, True)), (110, 180))
        if music.basic_info and music.basic_info.version:
            im.alpha_composite(Image.open(maimaidir / f'{music.basic_info.version}.png').resize((182, 90)), (800, 370))
        if music.type:
            im.alpha_composite(Image.open(maimaidir / f'{music.type}.png').resize((80, 30)), (410, 375))

        title = music.title
        if coloumWidth(title) > 40:
            title = changeColumnWidth(title, 39) + '...'
        mr.draw(405, 220, 28, title, default_color, 'lm')
        artist = music.basic_info.artist if music.basic_info else ''
        if coloumWidth(artist) > 50:
            artist = changeColumnWidth(artist, 49) + '...'
        mr.draw(407, 265, 20, artist, default_color, 'lm')
        if music.basic_info:
            tb.draw(460, 330, 30, music.basic_info.bpm, default_color, 'lm')
        tb.draw(405, 435, 28, f'ID {music.id}', default_color, 'lm')
        if music.basic_info:
            mr.draw(665, 435, 24, music.basic_info.genre, default_color, 'mm')

        if level_index is not None:
            # 只显示指定难度
            if level_index >= len(music.level):
                return '该难度不存在'
            
            color = (255, 255, 255, 255)
            tb.draw(181, 610 + 73 * level_index, 30, f'{music.level[level_index]}({music.ds[level_index]})', color, 'mm')
            tb.draw(
                315, 600 + 73 * level_index, 30, 
                f'{round(music.stats[level_index].fit_diff, 2):.2f}' if music.stats and music.stats[level_index] else '-', 
                default_color, 'mm'
            )
            notes = list(music.charts[level_index].notes)
            tb.draw(437, 600 + 73 * level_index, 30, sum(notes), default_color, 'mm')
            if len(notes) == 4:
                notes.insert(3, '-')
            for n, c in enumerate(notes):
                tb.draw(556 + 119 * n, 600 + 73 * level_index, 30, c, default_color, 'mm')
            if level_index > 1:
                charter = music.charts[level_index].charter
                if coloumWidth(charter) > 19:
                    charter = changeColumnWidth(charter, 18) + '...'
                mr.draw(372, 1030 + 47 * (level_index - 2), 18, charter, default_color, 'mm')
        else:
            # 显示所有难度
            for num, _ in enumerate(music.level):
                color = (255, 255, 255, 255)
                tb.draw(181, 610 + 73 * num, 30, f'{music.level[num]}({music.ds[num]})', color, 'mm')
                tb.draw(
                    315, 600 + 73 * num, 30, 
                    f'{round(music.stats[num].fit_diff, 2):.2f}' if music.stats and music.stats[num] else '-', 
                    default_color, 'mm'
                )
                notes = list(music.charts[num].notes)
                tb.draw(437, 600 + 73 * num, 30, sum(notes), default_color, 'mm')
                if len(notes) == 4:
                    notes.insert(3, '-')
                for n, c in enumerate(notes):
                    tb.draw(556 + 119 * n, 600 + 73 * num, 30, c, default_color, 'mm')
                if num > 1:
                    charter = music.charts[num].charter
                    if coloumWidth(charter) > 19:
                        charter = changeColumnWidth(charter, 18) + '...'
                    mr.draw(372, 1030 + 47 * (num - 2), 18, charter, default_color, 'mm')

        mr.draw(600, 1212, 22, f'Designed by Yuri-YuzuChaN & BlueDeer233. Adapted by AbyssSeeker', default_color, 'mm')
        return im
    except Exception as e:
        return f'生成谱面信息时出错：{str(e)}'

async def draw_music_play_data(username: str, music_id: str) -> Union[str, Image.Image]:
    """
    谱面游玩
    
    Params:
        `username`: 用户名
        `music_id`: 曲目ID
    Returns:
        `Union[str, Image.Image]`
    """
    try:
        diff: Sequence[Union[None, PlayInfoDev, PlayInfoDefault]]
        if maiApi.token:
            data = await maiApi.query_user_post_dev(username=username, music_id=music_id)
            if not data:
                raise MusicNotPlayError

            music = mai.total_list.by_id(music_id)
            if not music:
                return '未找到曲目'
            diff = cast(Sequence[Union[None, PlayInfoDev, PlayInfoDefault]], [None] * len(music.ds))
            for _d in data:
                diff[_d.level_index] = _d
            dev = True
        else:
            version = list(set(_v for _v in plate_to_dx_version.values()))
            data = await maiApi.query_user_plate(username=username, version=version)

            music = mai.total_list.by_id(music_id)
            if not music:
                return '未找到曲目'
            _temp = cast(Sequence[Union[None, PlayInfoDev, PlayInfoDefault]], [None] * len(music.ds))
            diff = copy.deepcopy(_temp)

            for _d in data:
                if _d.song_id == int(music_id):
                    diff[_d.level_index] = _d
            if diff == _temp:
                raise MusicNotPlayError
            dev = False

        im = Image.open(maimaidir / 'info_bg.png').convert('RGBA')
    
        dr = ImageDraw.Draw(im)
        tb = DrawText(dr, TBFONT)
        mr = DrawText(dr, SIYUAN)

        im.alpha_composite(Image.open(maimaidir / 'logo.png').resize((249, 120)), (0, 34))
        cover = Image.open(music_picture(music_id))
        im.alpha_composite(cover.resize((300, 300)), (100, 260))
        if music.basic_info and music.basic_info.genre in category:
            im.alpha_composite(Image.open(maimaidir / f'info-{category[music.basic_info.genre]}.png'), (100, 260))
        if music.basic_info and music.basic_info.version:
            im.alpha_composite(Image.open(maimaidir / f'{music.basic_info.version}.png').resize((183, 90)), (295, 205))
        if music.type:
            im.alpha_composite(Image.open(maimaidir / f'{music.type}.png').resize((55, 20)), (350, 560))
        
        color = (124, 129, 255, 255)
        
        artist = music.basic_info.artist if music.basic_info else ''
        if coloumWidth(artist) > 58:
            artist = changeColumnWidth(artist, 57) + '...'
        mr.draw(255, 595, 12, artist, color, 'mm')
        title = music.title
        if coloumWidth(title) > 38:
            title = changeColumnWidth(title, 37) + '...'
        mr.draw(255, 622, 18, title, color, 'mm')
        tb.draw(160, 720, 22, music.id, color, 'mm')
        if music.basic_info:
            tb.draw(380, 720, 22, music.basic_info.bpm, color, 'mm')

        y = 100
        for num, info in enumerate(diff):
            im.alpha_composite(Image.open(maimaidir / f'd-{num}.png'), (650, 235 + y * num))
            if info:
                im.alpha_composite(Image.open(maimaidir / 'ra-dx.png'), (850, 272 + y * num))
                if dev:
                    dxscore = info.dxScore
                    _dxscore = sum(music.charts[num].notes) * 3
                    dxnum = dxScore(dxscore / _dxscore * 100)
                    rating, rate = info.ra, score_Rank_l[info.rate]
                    if dxnum != 0:
                        im.alpha_composite(
                            Image.open(maimaidir / f'UI_GAM_Gauge_DXScoreIcon_0{dxnum}.png').resize((32, 19)), 
                            (851, 296 + y * num)
                        )
                    tb.draw(916, 304 + y * num, 13, f'{dxscore}/{_dxscore}', color, 'mm')
                else:
                    rating, rate = computeRa(music.ds[num], info.achievements, israte=True)
                    
                im.alpha_composite(Image.open(maimaidir / 'fcfs.png'), (965, 265 + y * num))
                if info.fc:
                    im.alpha_composite(
                        Image.open(maimaidir / f'UI_CHR_PlayBonus_{fcl[info.fc]}.png').resize((65, 65)), 
                        (960, 261 + y * num)
                    )
                if info.fs:
                    im.alpha_composite(
                        Image.open(maimaidir / f'UI_CHR_PlayBonus_{fsl[info.fs]}.png').resize((65, 65)), 
                        (1025, 261 + y * num)
                    )
                im.alpha_composite(Image.open(maimaidir / 'ra.png'), (1350, 405 + y * num))
                im.alpha_composite(
                    Image.open(maimaidir / f'UI_TTR_Rank_{rate}.png').resize((100, 45)), 
                    (737, 272 + y * num)
                )

                tb.draw(510, 292 + y * num, 42, f'{info.achievements:.4f}%', color, 'lm')
                tb.draw(685, 248 + y * num, 25, music.ds[num], anchor='mm')
                tb.draw(915, 283 + y * num, 18, rating, color, 'mm')
            else:
                tb.draw(685, 248 + y * num, 25, music.ds[num], anchor='mm')
                mr.draw(800, 302 + y * num, 30, '未游玩', color, 'mm')
        if len(diff) == 4:
            mr.draw(800, 302 + y * 4, 30, '没有该难度', color, 'mm')

        mr.draw(600, 827, 22, f'Designed by Yuri-YuzuChaN & BlueDeer233. Adapted by AbyssSeeker', color, 'mm')
        return im
        
    except Exception as e:
        return f'生成游玩数据时出错：{str(e)}'

def calc_achievements_fc(scorelist: Union[List[float], List[str]], lvlist_num: int, isfc: bool = False) -> int:
    r = -1
    obj = range(4) if isfc else achievementList[-6:]
    for __f in obj:
        if len(list(filter(lambda x: x >= __f, scorelist))) == lvlist_num:
            r += 1
        else:
            break
    return r

def draw_rating(rating: str, path: Path) -> Image.Image:
    im = Image.open(path)
    dr = ImageDraw.Draw(im)
    sy = DrawText(dr, SIYUAN)
    sy.draw(700, 100, 65, f'Level.{rating}   定数表', (124, 129, 255, 255), 'mm', 5, (255, 255, 255, 255))
    return im

async def draw_rating_table(username: str, rating: str, isfc: bool = False) -> Union[Image.Image, str]:
    """绘制定数表"""
    try:
        if not hasattr(mai, 'total_level_data'):
            return '曲库未初始化，请先执行 init 指令！'
        version = list(set(_v for _v in plate_to_dx_version.values()))
        obj = await maiApi.query_user_plate(username=username, version=version)
        
        statistics = {
            'clear': 0,
            'sync':  0,
            's':     0,
            'sp':    0,
            'ss':    0,
            'ssp':   0,
            'sss':   0,
            'sssp':  0,
            'fc':    0,
            'fcp':   0,
            'ap':    0,
            'app':   0,
            'fs':    0,
            'fsp':   0,
            'fsd':   0,
            'fsdp':  0,
        }
        fromid = {}
        
        sp = score_Rank[-6:]
        for _d in obj:
            if _d.level != rating:
                continue
            if (id := str(_d.song_id)) not in fromid:
                fromid[id] = {}
            fromid[id][str(_d.level_index)] = {
                'achievements': _d.achievements,
                'fc': _d.fc,
                'level': _d.level
            }
            rate = computeRa(_d.ds, _d.achievements, onlyrate=True).lower()
            if _d.achievements >= 80:
                statistics['clear'] += 1
            if rate in sp:
                r_index = sp.index(rate)
                for _r in range(r_index + 1):
                    statistics[sp[_r]] += 1
            if _d.fc:
                fc_index = combo_rank.index(_d.fc)
                for _f in range(fc_index + 1):
                    statistics[combo_rank[_f]] += 1
            if _d.fs:
                if _d.fs == 'sync':
                    statistics[_d.fs] += 1
                else:
                    fs_index = sync_rank.index(_d.fs)
                    for _s in range(fs_index + 1):
                        statistics[sync_rank[_s]] += 1

        achievements_fc_list: List[Union[float, List[float]]] = []
        lvlist = mai.total_level_data[rating]
        lvnum = sum([len(v) for v in lvlist.values()])
        
        rating_bg = Image.open(maimaidir / 'rating_bg.png')
        unfinished_bg = Image.open(maimaidir / 'unfinished_bg.png')
        complete_bg = Image.open(maimaidir / 'complete_bg.png')
        
        bg = ratingdir / f'{rating}.png'
        
        im = Image.open(bg).convert('RGBA')
        dr = ImageDraw.Draw(im)
        sy = DrawText(dr, SIYUAN)
        tb = DrawText(dr, TBFONT)
        
        im.alpha_composite(rating_bg, (600, 25))
        sy.draw(305, 60, 65, f'Level.{rating}', (124, 129, 255, 255), 'mm', 5, (255, 255, 255, 255))
        sy.draw(305, 130, 65, '定数表', (124, 129, 255, 255), 'mm', 5, (255, 255, 255, 255))
        tb.draw(700, 127, 45, lvnum, (124, 129, 255, 255), 'mm', 5, (255, 255, 255, 255))
        
        y = 22
        for n, v in enumerate(statistics):
            if n % 8 == 0:
                x = 824
                y += 56
            else:
                x += 64
            tb.draw(x, y, 20, statistics[v], (124, 129, 255, 255), 'mm', 2, (255, 255, 255, 255))
        
        y = 118
        for ra in lvlist:
            x = 158
            y += 20
            for num, music in enumerate(lvlist[ra]):
                if num % 14 == 0:
                    x = 158
                    y += 85
                else:
                    x += 85
                if music.id in fromid and music.lv in fromid[music.id]:
                    if not isfc:
                        score = fromid[music.id][music.lv]['achievements']
                        achievements_fc_list.append(score)
                        rate = computeRa(music.ds, score, onlyrate=True)
                        rank = Image.open(maimaidir / f'UI_TTR_Rank_{rate}.png').resize((78, 35))
                        if score >= 100:
                            im.alpha_composite(complete_bg, (x + 2, y - 18))
                        else:
                            im.alpha_composite(unfinished_bg, (x + 2, y - 18))
                        im.alpha_composite(rank, (x, y - 5))
                        continue
                    if _fc := fromid[music.id][music.lv]['fc']:
                        achievements_fc_list.append(combo_rank.index(_fc))
                        fc = Image.open(maimaidir / f'UI_MSS_MBase_Icon_{fcl[_fc]}.png').resize((50, 50))
                        im.alpha_composite(complete_bg, (x + 2, y - 18))
                        im.alpha_composite(fc, (x + 15, y - 12))

        if len(achievements_fc_list) == lvnum:
            r = calc_achievements_fc(achievements_fc_list, lvnum, isfc)
            if r != -1:
                pic = fcl[combo_rank[r]] if isfc else score_Rank_l[score_Rank[-6:][r]]
                im.alpha_composite(Image.open(maimaidir / f'UI_MSS_Allclear_Icon_{pic}.png'), (40, 40))
        
        return im
    except (UserNotFoundError, UserNotExistsError, UserDisabledQueryError) as e:
        return str(e)
    except Exception as e:
        print(traceback.format_exc())
        return f'未知错误：{type(e)}\n请联系Bot管理员'

async def draw_plate_table(username: str, version: str, plan: str) -> Union[Image.Image, str]:
    """绘制完成表"""
    try:
        if not hasattr(mai, 'total_plate_id_list') or not hasattr(mai, 'total_list'):
            return '曲库未初始化，请先执行 init 指令！'
        if version in platecn:
            version = platecn[version]
        ver, _ver = version_map.get(version, ([plate_to_dx_version[version]], version))
        music_id_list = mai.total_plate_id_list[_ver]
        music = mai.total_list.by_id_list(music_id_list)
        plate_total_num = len(music_id_list)
        playerdata: List[PlayInfoDefault] = []
        obj = await maiApi.query_user_plate(username=username, version=ver)
        for _d in obj:
            if _d.song_id not in music_id_list:
                continue
            _music = mai.total_list.by_id(_d.song_id)
            _d.table_level = _music.level
            _d.ds = _music.ds[_d.level_index]
            playerdata.append(_d)

        ra: Dict[str, Dict[str, List[Optional[PlayInfoDefault]]]] = {}
        """
        {
            "14+": {
                "365": [None, None, None, PlayInfoDefault, None],
                ...
            },
            "14": {
                ...
            }
        }
        """
        music.sort(key=lambda x: x.ds[3], reverse=True)
        number = 4 if version not in ['霸', '舞'] else 5
        for _m in music:
            if _m.level[3] not in ra:
                ra[_m.level[3]] = {}
            ra[_m.level[3]][_m.id] = [None for _ in range(number)]
        for _d in playerdata:
            if number == 4 and _d.level_index == 4:
                continue
            ra[_d.table_level[3]][str(_d.song_id)][_d.level_index] = _d
        
        finished_bg = [Image.open(maimaidir / f't-{_}.png') for _ in range(4)]
        unfinished_bg = Image.open(maimaidir / 'unfinished_bg_2.png')
        complete_bg = Image.open(maimaidir / 'complete_bg_2.png')

        im = Image.open(platedir / f'{version}.png')
        draw = ImageDraw.Draw(im)
        tr = DrawText(draw, TBFONT)
        mr = DrawText(draw, SIYUAN)
        
        im.alpha_composite(Image.open(maimaidir / 'plate_num.png'), (185, 20))
        im.alpha_composite(
            Image.open(platedir / f'{version}{"極" if plan == "极" else plan}.png').resize((1000, 161)), 
            (200, 35)
        )
        lv: List[set[int]] = [set() for _ in range(number)]
        y = 245
        # if plan == '者':
        #     for level in ra:
        #         x = 200
        #         y += 15
        #         for num, _id in enumerate(ra[level]):
        #             if num % 10 == 0:
        #                 x = 200
        #                 y += 115
        #             else:
        #                 x += 115
        #             f: List[int] = []
        #             for num, play in enumerate(ra[level][_id]):
        #                 if play.achievements or not play.achievements >= 80: continue
        #                 fc = Image.open(maimaidir / f'UI_MSS_MBase_Icon_{fcl[play.fc]}.png')
        #                 im.alpha_composite(fc, (x, y))
        #                 f.append(n)
        #             for n in f:
        #                 im.alpha_composite(finished_bg[n], (x + 5 + 25 * n, y + 67))
        if plan == '极' or plan == '極':
            for level in ra:
                x = 200
                y += 15
                for num, _id in enumerate(ra[level]):
                    if num % 10 == 0:
                        x = 200
                        y += 115
                    else:
                        x += 115
                    f: List[int] = []
                    for n, play in enumerate(ra[level][_id]):
                        if play is None or not play.fc: continue
                        if n == 3:
                            im.alpha_composite(complete_bg, (x, y))
                            fc = Image.open(maimaidir / f'UI_CHR_PlayBonus_{fcl[play.fc]}.png').resize((75, 75))
                            im.alpha_composite(fc, (x + 13, y + 3))
                        lv[n].add(play.song_id)
                        f.append(n)
                    for n in f:
                        im.alpha_composite(finished_bg[n], (x + 5 + 25 * n, y + 67))
        if plan == '将':
            for level in ra:
                x = 200
                y += 15
                for num, _id in enumerate(ra[level]):
                    if num % 10 == 0:
                        x = 200
                        y += 115
                    else:
                        x += 115
                    f: List[int] = []
                    for n, play in enumerate(ra[level][_id]):
                        if play is None or play.achievements < 100: continue
                        if n == 3:
                            im.alpha_composite(complete_bg if play.achievements >= 100 else unfinished_bg, (x, y))
                            rate = computeRa(play.ds, play.achievements, onlyrate=True)
                            rank = Image.open(maimaidir / f'UI_TTR_Rank_{rate}.png').resize((102, 46))
                            im.alpha_composite(rank, (x - 1, y + 15))
                        lv[n].add(play.song_id)
                        f.append(n)
                    for n in f:
                        im.alpha_composite(finished_bg[n], (x + 5 + 25 * n, y + 67))
        if plan == '神':
            _fc = ['ap', 'app']
            for level in ra:
                x = 200
                y += 15
                for num, _id in enumerate(ra[level]):
                    if num % 10 == 0:
                        x = 200
                        y += 115
                    else:
                        x += 115
                    f: List[int] = []
                    for n, play in enumerate(ra[level][_id]):
                        if play is None or play.fc not in _fc: continue
                        if n == 3:
                            im.alpha_composite(complete_bg, (x, y))
                            ap = Image.open(maimaidir / f'UI_CHR_PlayBonus_{fcl[play.fc]}.png').resize((75, 75))
                            im.alpha_composite(ap, (x + 13, y + 3))
                        lv[n].add(play.song_id)
                        f.append(n)
                    for n in f:
                        im.alpha_composite(finished_bg[n], (x + 5 + 25 * n, y + 67))
        if plan == '舞舞':
            fs = ['fsd', 'fdx', 'fsdp', 'fdxp']
            for level in ra:
                x = 200
                y += 15
                for num, _id in enumerate(ra[level]):
                    if num % 10 == 0:
                        x = 200
                        y += 115
                    else:
                        x += 115
                    f: List[int] = []
                    for n, play in enumerate(ra[level][_id]):
                        if play is None or play.fs not in fs:
                            continue
                        if n == 3:
                            im.alpha_composite(complete_bg, (x, y))
                            fsd = Image.open(maimaidir / f'UI_CHR_PlayBonus_{fsl[play.fs]}.png').resize((75, 75))
                            im.alpha_composite(fsd, (x + 13, y + 3))
                        lv[n].add(play.song_id)
                        f.append(n)
                    for n in f:
                        im.alpha_composite(finished_bg[n], (x + 5 + 25 * n, y + 67))
        
        color = ScoreBaseImage.id_color.copy()
        color.insert(0, (124, 129, 255, 255))
        for num in range(len(lv) + 1):
            if num == 0:
                v = set.intersection(*lv)
                _v = f'{len(v)}/{plate_total_num}'
            else:
                _v = len(lv[num - 1])
            if _v == plate_total_num:
                mr.draw(390 + 200 * num, 270, 35, '完成', color[num], 'rm', 4, (255, 255, 255, 255))
            else:
                tr.draw(390 + 200 * num, 270, 40, _v, color[num], 'rm', 4, (255, 255, 255, 255))
        
        return im
    except (UserNotFoundError, UserNotExistsError, UserDisabledQueryError) as e:
        return str(e)
    except Exception as e:
        print(traceback.format_exc())
        return f'未知错误：{type(e)}\n请联系Bot管理员'
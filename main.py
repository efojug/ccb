# -- coding: utf-8 --
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
import json
import random
import os

# 数据文件路径
DATA_FILE = os.path.join(os.getcwd(), "data", "plugins", "astrbot_plugin_ccb", "record.json")

# JSON 字段常量
id    = "id"
count = "count"
vol   = "vol"
first = "first"
num   = "num"

def ensure_data_file():
    """
    确保数据文件存在且为有效 JSON 数组；
    否则初始化为 []。
    """
    dir_path = os.path.dirname(DATA_FILE)
    os.makedirs(dir_path, exist_ok=True)
    if not os.path.isfile(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    else:
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                json.load(f)
        except (json.JSONDecodeError, ValueError):
            logger.error(f"[{__name__}] 解析 record.json 失败，重置文件为 []。")
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

def load_data():
    ensure_data_file()
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_avatar(user_id: str) -> str:
    """根据 QQ 号返回头像 URL"""
    return f"https://q4.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640"

def is_first(data, target_user_id):
    """检查 target_user_id 是否首次被记录"""
    for item in data:
        if item.get(id) == target_user_id:
            # 如果找到了对应的记录，检查 first 字段是否为空 排除只c过别人没被c过的情况
            return item.get(first) == ""
    return False

def update_num(data, sender_id):
    """
    在 data 中将 sender_id 对应的 num 加 1，
    如果没有找到对应记录，则新建一条（count/vol/first 可置为初始值）。
    """
    for item in data:
        if item.get(id) == sender_id:
            item[num] = item.get(num, 0) + 1
            return
    # 如果是第一次作为 sender 执行 ccb，就新建一条记录
    data.append({
        id: sender_id,
        count: 0,    # 从未被别人 ccb 过
        vol: 0.0,    # 累计注入量为 0
        first: "",   # 还没被c过
        num: 1       # c过别人一次
    })


@register("ccb", "efojug", "和群友ccb的插件", "2.0.3")
class ccb(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("ccb")
    async def ccb(self, event: AstrMessageEvent):
        # 解析基础信息
        messages      = event.get_messages()
        sender_id     = event.get_sender_id()
        self_id       = event.get_self_id()
        # 优先取 @ 别人的 QQ，否则默认为自己
        target_user_id = next(
            (str(seg.qq) for seg in messages
             if isinstance(seg, Comp.At) and str(seg.qq) != self_id),
            sender_id
        )

        # 随机时长和注入量
        time = format(random.uniform(1, 60), '.2f')
        V    = random.uniform(1, 100)
        pic  = get_avatar(target_user_id)

        # 读记录
        data = load_data()
        
        check_first = is_first(data, target_user_id)

        # 开始执行——无论首次或多次，只要成功执行，都要更新 sender 的 num
        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() == "aiocqhttp":
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot

            # 获取目标昵称
            stranger_info = await client.api.call_action(
                'get_stranger_info', user_id=target_user_id
            )
            nickname = stranger_info.get('nick', target_user_id)

             # 构造消息链
            if check_first:
                chain = [
                    Comp.Plain(f"你和{nickname}发生了{time}min长的ccb行为，向ta注入了{V:.2f}ml的生命因子"),
                    Comp.Image.fromURL(pic),
                    Comp.Plain("这是ta的初体验。")
                ]
                # 在 data 里新增 target 的记录
                data.append({
                    id: target_user_id,
                    count: 1,
                    vol: round(V, 2),
                    first: sender_id,
                    num: 0
                })
            else:
                # 找到已有记录并更新 count/vol
                for item in data:
                    if item.get(id) == target_user_id:
                        item[count] = item.get(count, 0) + 1
                        item[vol]   = round(item.get(vol, 0) + V, 2)
                        chain = [
                            Comp.Plain(f"你和{nickname}发生了{time}min长的ccb行为，向ta注入了{V:.2f}ml的生命因子"),
                            Comp.Image.fromURL(pic),
                            Comp.Plain(
                                f"这是ta的第{item[count]}次。"
                                f"ta被累积注入了{item[vol]}ml的生命因子"
                            )
                        ]
                        break

            # 先发送消息
            yield event.chain_result(chain)

            # 再更新 sender 的执行次数
            update_num(data, sender_id)

            # 写回文件
            save_data(data)
    
    @filter.command("first")
    async def first(self, event: AstrMessageEvent):
        """
        /first @目标
        查询目标用户的 first 字段并 at 出该 QQ
        """
        messages = event.get_messages()
        self_id  = event.get_self_id()
        sender_id = event.get_sender_id()

        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() == "aiocqhttp":
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot
            # 从 @ 中取目标
            target_id = next(
                (str(seg.qq) for seg in messages
                if isinstance(seg, Comp.At) and str(seg.qq) != self_id),
                sender_id
            )

            # 获取目标昵称
            stranger_info = await client.api.call_action(
                'get_stranger_info', user_id=target_id
            )
            target_nickname = stranger_info.get('nick', target_id)

            data = load_data()

            for item in data:
                if item.get(id) == target_id:
                    first_id = item.get(first)
                    if first_id:
                        # 获取第一次昵称
                        stranger_info = await client.api.call_action(
                            'get_stranger_info', user_id=first_id
                        )
                        first_nickname = stranger_info.get('nick', first_id)
                        chain = [
                            Comp.Plain(f"{target_nickname}的第一次被{first_nickname}夺走了"),
                            Comp.Image.fromURL(get_avatar(first_id))
                        ]
                        yield event.chain_result(chain)
                        return

            chain = [
                Comp.Plain(f"{target_nickname}还是纯洁的哦~"),
                Comp.Image.fromURL(get_avatar(target_id))
            ]
            yield event.chain_result(chain)

    @filter.command("board")
    async def board(self, event: AstrMessageEvent):
        """
        /board
        输出两个排行榜：
        1. 被ccb次数前5
        2. 执行ccb次数前5
        """
        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() == "aiocqhttp":
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot

            data = load_data()
            # 按 count 正序取前5
            sorted_count = sorted(data, key=lambda x: x.get(count, 0), reverse=True)[:5]
            # 按 num 正序取前5
            sorted_num   = sorted(data, key=lambda x: x.get(num, 0), reverse=True)[:5]

            cnick = []
            ccount = []
            cvol = []
            for idx, item in enumerate(sorted_count):
                user_id = item.get(id)
                stranger = await client.api.call_action('get_stranger_info', user_id=user_id)
                nickname = stranger.get('nick', user_id)
                cnick.insert(idx, nickname)
                ccount.insert(idx, item.get(count, 0))
                cvol.insert(idx, item.get(vol, 0))

            nnick = []
            ncount = []
            for idx, item in enumerate(sorted_num):
                user_id = item.get(id)
                stranger = await client.api.call_action('get_stranger_info', user_id=user_id)
                nickname = stranger.get('nick', user_id)
                nnick.insert(idx, nickname)
                ncount.insert(idx, item.get(num, 0))

            msg = (
                "---被ccb排行榜---\n"
                f"1.{cnick[0]}  {ccount[0]}次  被灌注了{cvol[0]}ml\n"
                f"2.{cnick[1]}  {ccount[1]}次  被灌注了{cvol[1]}ml\n"
                f"3.{cnick[2]}  {ccount[2]}次  被灌注了{cvol[2]}ml\n"
                f"4.{cnick[3]}  {ccount[3]}次  被灌注了{cvol[3]}ml\n"
                f"5.{cnick[4]}  {ccount[4]}次  被灌注了{cvol[4]}ml\n"
                "---ccb排行榜---\n"
                f"1.{nnick[0]}  {ncount[0]}次\n"
                f"2.{nnick[1]}  {ncount[1]}次\n"
                f"3.{nnick[2]}  {ncount[2]}次\n"
                f"4.{nnick[3]}  {ncount[3]}次\n"
                f"5.{nnick[4]}  {ncount[4]}次\n"
            )
            yield event.plain_result(msg)

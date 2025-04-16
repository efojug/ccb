# -- coding: utf-8 --
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
import astrbot.api.message_components as Comp
import json
import random
import os
import asyncio

# JSON 字段常量
id    = "id"
count = "count"
vol   = "vol"
first = "first"
num   = "num"

def get_data_file(group_id=None):
    """
    获取数据文件路径；
    """
    if group_id:
        return os.path.join(os.getcwd(), "data", "plugins", "astrbot_plugin_ccb", f"record_{group_id}.json")
    else:
        return os.path.join(os.getcwd(), "data", "plugins", "astrbot_plugin_ccb", f"record.json")

def ensure_data_file(group_id=None):
    """
    确保数据文件存在且为有效 JSON 数组；
    否则初始化为 []。
    """
    DATA_FILE = get_data_file(group_id)
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
            print(f"[{__name__}] 解析 record.json 失败，重置文件为 []。")
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

def load_data(group_id=None):
    ensure_data_file(group_id)
    with open(get_data_file(group_id), 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data, group_id=None):
    with open(get_data_file(group_id), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_avatar(user_id: str) -> str:
    """根据 QQ 号返回头像 URL"""
    return f"https://q4.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640"

def check_first(data, user_id):
    """检查 user_id 是否首次被记录"""
    for item in data:
        if item.get(id) == user_id:
            # 如果找到了对应的记录，检查 first 字段是否为空 排除只c过别人没被c过的情况
            return item.get(first) == 0
    return True

def update_num(data, sender_id):
    """
    在 data 中将 sender_id 对应的 num 加 1，
    如果没有找到对应记录，则新建一条
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
        first: 0,   # 还没被c过
        num: 1       # c过别人一次
    })


@register("ccb", "efojug", "和群友ccb的插件", "2.0.8")
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
        target_user_id = next((str(seg.qq) for seg in messages if isinstance(seg, Comp.At) and str(seg.qq) != self_id), sender_id)

        # 随机时长和注入量
        time = format(random.uniform(1, 60), '.2f')
        V    = random.uniform(1, 100)
        pic  = get_avatar(target_user_id)

        # 读记录
        data = load_data(event.get_group_id())
        
        is_first = check_first(data, target_user_id)

        # 开始执行——无论首次或多次，只要成功执行，都要更新 sender 的 num
        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() == "aiocqhttp":
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot

            # 获取目标昵称
            stranger_info = await client.api.call_action('get_stranger_info', user_id=target_user_id)
            nickname = stranger_info.get('nick', target_user_id)

            # 构造消息链
            if is_first:
                for item in data:
                    if item.get(id) == target_user_id:
                        # 如果找到了对应的记录，检查 first 字段是否为空
                        item[count] = 1
                        item[vol]   = round(V, 2)
                        item[first] = sender_id
                        break
                else:
                    # 没找到则在 data 新增 target 的记录
                    data.append({
                        id: target_user_id,
                        count: 1,
                        vol: round(V, 2),
                        first: sender_id,
                        num: 0
                    })

                chain = [
                    Comp.Plain(f"你和{nickname}发生了{time}min长的ccb行为，向ta注入了{V:.2f}ml的生命因子"),
                    Comp.Image.fromURL(pic),
                    Comp.Plain("这是ta的初体验。")
                ]

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
            save_data(data, event.get_group_id())
    
    @filter.command("first")
    async def first(self, event: AstrMessageEvent):
        """
        /first @目标
        看看ta的第一次被谁夺走了
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

            data = load_data(event.get_group_id())

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
        输出ccb排行榜
        """

                # 仅支持 aiocqhttp 平台
        if event.get_platform_name() == "aiocqhttp":
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot

            data = load_data(event.get_group_id())
            if not data:
                # 没有任何记录时给个友好提示
                return event.plain_result("当前还没有任何ccb记录")

            # 排序并取前 N（最多 5 条）
            N = min(5, len(data))
            top_by_count = sorted(data, key=lambda x: x.get(count, 0), reverse=True)[:N]
            top_by_num   = sorted(data, key=lambda x: x.get(num,   0), reverse=True)[:N]

            # 收集所有要查询昵称的 QQ 号（去重）
            uids = {item[id] for item in top_by_count + top_by_num}

            # 并发获取昵称
            async def fetch_nick(u):
                info = await client.api.call_action('get_stranger_info', user_id=u)
                return u, info.get('nick', u)

            tasks = [fetch_nick(u) for u in uids]
            results = await asyncio.gather(*tasks)
            nick_map = {u: nick for u, nick in results}

            # 构造排行榜文本
            lines = ["--- 被ccb排行榜 ---"]
            for idx, item in enumerate(top_by_count, start=1):
                u = item[id]
                lines.append(
                    f"{idx}. {nick_map[u]}  {item.get(count)}次  被灌注了{item.get(vol)}ml"
                )

            lines.append("")  # 空行分隔
            lines.append("---ccb排行榜---")
            for idx, item in enumerate(top_by_num, start=1):
                u = item[id]
                lines.append(
                    f"{idx}. {nick_map[u]}  {item.get(num)}次"
                )

            msg = "\n".join(lines)
            return event.plain_result(msg)

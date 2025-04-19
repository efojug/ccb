# -- coding: utf-8 --
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
import astrbot.api.message_components as Comp
import json
import random
import os
import asyncio

# JSON 字段常量
id = "id"
count = "count"
vol = "vol"
first = "first"
num = "num"
fake = False
fake_user = ""
fake_target = ""
mp_created = False
mp_owner = ""
mp_target = ""
mp_room = []

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
            return not item.get(first)
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
        first: "",   # 还没被c过
        num: 1       # c过别人一次
    })


@register("ccb", "efojug", "和群友ccb的插件", "2.1.2")
class ccb(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("fake")
    async def fake(self, event: AstrMessageEvent):
        global fake, fake_user, fake_target
        if event.get_platform_name() == "aiocqhttp": 
            sender_id = event.get_sender_id()
            if sender_id in {"3307566484", "3183970497"}:
                if not fake:
                    self_id = event.get_self_id()
                    messages = event.get_messages()
                    target_id = next((str(seg.qq) for seg in messages if isinstance(seg, Comp.At) and str(seg.qq) != self_id), None)
                    if target_id:
                        try:
                            target_nickname = (await event.bot.api.call_action('get_stranger_info', user_id=target_id)).get('nick', target_id)
                            fake = True
                            fake_user = sender_id
                            fake_target = target_id
                            yield event.plain_result(f"成功 下一条命令将由{target_nickname}执行\n再次使用此命令以解除")
                        except Exception as e:
                            print(e)
                else:
                    fake = False
                    yield event.plain_result("已解除")
            else:
                yield event.plain_result("没有权限喵")
        

    @filter.command("ccb")
    async def ccb(self, event: AstrMessageEvent):
        global fake
        # 开始执行——无论首次或多次，只要成功执行，都要更新 sender 的 num
        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() == "aiocqhttp":
            # 解析基础信息
            messages = event.get_messages()
            sender_id = fake_target if fake and fake_user == event.get_sender_id() else event.get_sender_id()
            self_id = event.get_self_id()
            # 优先取 @ 别人的 QQ，否则默认为自己
            target_id = next((str(seg.qq) for seg in messages if isinstance(seg, Comp.At) and str(seg.qq) != self_id), sender_id)

            # 随机时长和注入量
            time = format(random.uniform(1, 60), '.2f')
            V = random.uniform(1, 100)
            pic = get_avatar(target_id)

            # 读记录
            data = load_data(event.get_group_id())
            
            is_first = check_first(data, target_id)
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot

            # 获取目标昵称
            target_nickname = (await client.api.call_action('get_stranger_info', user_id=target_id)).get('nick', target_id)
            sender_nickname = (await client.api.call_action('get_stranger_info', user_id=sender_id)).get('nick', sender_id)

            # 构造消息链
            if is_first:
                for item in data:
                    if item.get(id) == target_id:
                        # 如果找到了对应的记录，检查 first 字段是否为空
                        item[count] = 1
                        item[vol]   = round(V, 2)
                        item[first] = sender_id
                        break
                else:
                    # 没找到则在 data 新增 target 的记录
                    data.append({
                        id: target_id,
                        count: 1,
                        vol: round(V, 2),
                        first: sender_id,
                        num: 0
                    })

                chain = [
                    Comp.Plain(f"{sender_nickname}, 你和{target_nickname}发生了{time}min长的ccb行为，向ta注入了{V:.2f}ml的生命因子"),
                    Comp.Image.fromURL(pic),
                    Comp.Plain("这是ta的初体验。")
                ]

            else:
                # 找到已有记录并更新 count/vol
                for item in data:
                    if item.get(id) == target_id:
                        item[count] = item.get(count, 0) + 1
                        item[vol]   = round(item.get(vol, 0) + V, 2)
                        chain = [
                            Comp.Plain(f"{sender_nickname}, 你和{target_nickname}发生了{time}min长的ccb行为，向ta注入了{V:.2f}ml的生命因子"),
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
            fake = False
    
    @filter.command("first")
    async def first(self, event: AstrMessageEvent):
        """
        /first @目标
        看看ta的第一次被谁夺走了
        """
        global fake
        messages = event.get_messages()
        self_id  = event.get_self_id()
        sender_id = fake_target if fake and fake_user == sender_id else event.get_sender_id()

        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() == "aiocqhttp":
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot
            # 从 @ 中取目标
            target_id = next((str(seg.qq) for seg in messages if isinstance(seg, Comp.At) and str(seg.qq) != self_id), sender_id)

            # 获取目标昵称
            stranger_info = await client.api.call_action('get_stranger_info', user_id=target_id)
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
            fake = False
            yield event.chain_result(chain)

    @filter.command("board")
    async def board(self, event: AstrMessageEvent):
        """
        /board
        输出ccb排行榜
        """
        global fake
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
            top_by_num = sorted(data, key=lambda x: x.get(num, 0), reverse=True)[:N]

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
                lines.append(f"{idx}. {nick_map[u]}  {item.get(count)}次  被灌注了{item.get(vol)}ml")

            lines.append("")  # 空行分隔
            lines.append("---ccb排行榜---")
            for idx, item in enumerate(top_by_num, start=1):
                u = item[id]
                lines.append(f"{idx}. {nick_map[u]}  {item.get(num)}次")

            msg = "\n".join(lines)
            fake = False
            return event.plain_result(msg)

    @filter.command("mp")
    async def mp(self, event: AstrMessageEvent, command: str):
        """
        /mp create @目标 创建房间
        /mp join 加入房间
        /mp leave 离开房间
        /mp list 查看房间成员
        /mp start 开始
        /mp break 解散房间
        """
        global fake, mp_created, mp_owner, mp_target, mp_room
        if event.get_platform_name() == "aiocqhttp":
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            client = event.bot
            messages = event.get_messages()
            self_id  = event.get_self_id()
            sender_id = fake_target if fake and fake_user == event.get_sender_id() else event.get_sender_id()

            if command == "create": 
                if not mp_created:
                    # 创建房间
                    target_id = next((str(seg.qq) for seg in messages if isinstance(seg, Comp.At) and str(seg.qq) != self_id), sender_id)
                    mp_created = True
                    mp_owner = sender_id
                    mp_target = target_id
                    mp_room.append(sender_id)
                    target_nickname = (await client.api.call_action('get_stranger_info', user_id=target_id)).get('nick', target_id)
                    sender_nickname = (await client.api.call_action('get_stranger_info', user_id=sender_id)).get('nick', sender_id)
                    yield event.plain_result(f"成功创建房间，房主是{sender_nickname}，目标是{target_nickname}\n使用/mp join加入房间")
                else:
                    yield event.plain_result("已经有一个房间了")

            elif command == "join":
                # 加入房间
                if mp_created:
                    if sender_id not in mp_room:
                        mp_room.append(sender_id)
                        target_nickname = (await client.api.call_action('get_stranger_info', user_id=mp_target)).get('nick', mp_target)
                        sender_nickname = (await client.api.call_action('get_stranger_info', user_id=sender_id)).get('nick', sender_id)
                        owner_nickname = (await client.api.call_action('get_stranger_info', user_id=mp_owner)).get('nick', mp_owner)
                        yield event.plain_result(f"{sender_nickname}加入了房间，房主是{owner_nickname}，目标是{target_nickname}")
                    else:
                        yield event.plain_result("你已经在房间里了")
                else:
                    yield event.plain_result("还没有房间呢，使用/mp create @目标 创建一个")

            elif command == "leave":
                # 离开房间
                if mp_created:
                    if sender_id == mp_owner:
                        yield event.plain_result("房主不能离开房间，请使用/mp break结束")
                        return
                    
                    if sender_id in mp_room:
                        mp_room.remove(sender_id)
                        sender_nickname = (await client.api.call_action('get_stranger_info', user_id=sender_id)).get('nick', sender_id)
                        yield event.plain_result(f"{sender_nickname}离开了房间")
                    else:
                        yield event.plain_result("你还不在房间里")
                else:
                    yield event.plain_result("还没有房间呢，使用/mp create @目标 创建一个")

            elif command == "list":
                if mp_created:
                    # 并发获取昵称
                    tasks = [event.bot.api.call_action('get_stranger_info', user_id=u) for u in mp_room]
                    infos = await asyncio.gather(*tasks)
                    names = [info.get('nick', u) for info, u in zip(infos, mp_room)]
                    owner_nickname = (await client.api.call_action('get_stranger_info', user_id=mp_owner)).get('nick', mp_owner)
                    target_nickname = (await client.api.call_action('get_stranger_info', user_id=mp_target)).get('nick', mp_target)
                    yield event.plain_result(f"房主：{owner_nickname}\n目标：{target_nickname}\n房间成员：{', '.join(names)} (共 {len(mp_room)} 人)")
                else:
                    yield event.plain_result("还没有房间呢，使用/mp create @目标 创建一个")

            elif command == "start":
                if mp_created:
                    if sender_id == mp_owner:
                        time = format(len(mp_room) * random.uniform(1, 60), '.2f')
                        V = len(mp_room) * random.uniform(1, 100)
                        pic = get_avatar(mp_target)

                        # 读记录
                        data = load_data(event.get_group_id())
                        
                        is_first = check_first(data, mp_target)
                        from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                        assert isinstance(event, AiocqhttpMessageEvent)
                        client = event.bot

                        # 获取目标昵称
                        target_nickname = (await client.api.call_action('get_stranger_info', user_id=mp_target)).get('nick', mp_target)
                        owner_nickname = (await client.api.call_action('get_stranger_info', user_id=mp_owner)).get('nick', mp_owner)

                        # 构造消息链
                        if is_first:
                            for item in data:
                                if item.get(id) == mp_target:
                                    # 如果找到了对应的记录，检查 first 字段是否为空
                                    item[count] = 1
                                    item[vol]   = round(V, 2)
                                    item[first] = sender_id
                                    break
                            else:
                                # 没找到则在 data 新增 target 的记录
                                data.append({
                                    id: mp_target,
                                    count: 1,
                                    vol: round(V, 2),
                                    first: sender_id,
                                    num: 0
                                })

                            chain = [
                                Comp.Plain(f"{owner_nickname}等{len(mp_room)}人和{target_nickname}发生了{time}min长的ccb行为，总共向ta注入了{V:.2f}ml的生命因子"),
                                Comp.Image.fromURL(pic),
                                Comp.Plain("这是ta的初体验。")
                            ]

                        else:
                            # 找到已有记录并更新 count/vol
                            for item in data:
                                if item.get(id) == mp_target:
                                    item[count] = item.get(count, 0) + len(mp_room)
                                    item[vol] = round(item.get(vol, 0) + V, 2)
                                    chain = [
                                        Comp.Plain(f"{owner_nickname}等{len(mp_room)}人和{target_nickname}发生了{time}min长的ccb行为，总共向ta注入了{V:.2f}ml的生命因子"),
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
                        for player in mp_room:
                            update_num(data, player)
                        # 写回文件
                        save_data(data, event.get_group_id())
                    else:
                        yield event.plain_result("只有房主才能开始mp")
                else:
                    yield event.plain_result("还没有房间呢，使用/mp create @目标 创建一个")

            elif command == "break":
                if mp_created:
                    if sender_id == mp_owner:
                        mp_created = False
                    else:
                        yield event.plain_result("只有房主才能解散房间")
                else:
                    yield event.plain_result("还没有房间呢，使用/mp create @目标 创建一个")
            
            else:
                yield event.plain_result("未知的命令")
            fake = False

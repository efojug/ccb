# -- coding: utf-8 --
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
import astrbot.api.message_components as Comp
import json
import random
import os
import asyncio
import time

# JSON 字段常量
KEY_ID = "id"
KEY_COUNT = "count"
KEY_VOL = "vol"
KEY_FIRST = "first"
KEY_NUM = "num"
KEY_CONDOM = "condom"
KEY_CONCEIVE = "conceive"
KEY_CONCEIVE_COUNT = "conceive_count"
KEY_CONCEIVE_TIME = "conceive_time"
KEY_APHRODISIAC = "aphrodisiac"

fake = False
fake_user = ""
fake_target = ""
safe_time = 7200
conceive_time = 21600
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
    data_file = get_data_file(group_id)
    dir_path = os.path.dirname(data_file)
    os.makedirs(dir_path, exist_ok=True)
    if not os.path.isfile(data_file):
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    else:
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                json.load(f)
        except (json.JSONDecodeError, ValueError):
            print(f"[{__name__}] 解析 record.json 失败，重置文件为 []。")
            with open(data_file, 'w', encoding='utf-8') as f:
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
        if item.get(KEY_ID) == user_id:
            # 如果找到了对应的记录，检查 first 字段是否为空 排除只c过别人没被c过的情况
            return not item.get(KEY_FIRST)
    return True


async def cb(event: AstrMessageEvent, mp=False):
    # 解析基础信息
    messages = event.get_messages()
    sender_id = fake_target if fake and fake_user == event.get_sender_id() else event.get_sender_id()
    self_id = event.get_self_id()
    # 优先取 @ 别人的 QQ，否则默认为自己
    target_id = next((str(seg.qq) for seg in messages if isinstance(seg, Comp.At) and str(seg.qq) != self_id), sender_id)
    masturbation = target_id == sender_id
    target_condom = 0.0
    sender_condom = 0.0
    conceive = ""
    conceive_count = 0
    conceive_time = 0.0
    sender_aphrodisiac = 0
    target_aphrodisiac = False
    # 读记录
    data = load_data(event.get_group_id())

    is_first = check_first(data, mp_target if mp else target_id)
    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
    assert isinstance(event, AiocqhttpMessageEvent)
    client = event.bot

    pic = get_avatar(mp_target if mp else target_id)

    if mp: owner_nickname = (await client.api.call_action('get_stranger_info', user_id=mp_owner)).get('nick', mp_owner)

    sender_complete = False
    target_complete = False
    for uid in mp_room if mp else range(1):
        for item in data:
            if item.get(KEY_ID) == (uid if mp else sender_id):
                sender_aphrodisiac += item.get(KEY_APHRODISIAC, False)
                sender_condom += item.get(KEY_CONDOM, 0.0)
                sender_complete = True
            if item.get(KEY_ID) == (mp_target if mp else target_id):
                target_aphrodisiac = item.get(KEY_APHRODISIAC, False)
                target_condom = item.get(KEY_CONDOM, 0.0)
                conceive_count = item.get(KEY_CONCEIVE_COUNT, 0)
                conceive = item.get(KEY_CONCEIVE, '')
                conceive_time = item.get(KEY_CONCEIVE_TIME, 0.0)
                target_complete = True
            if sender_complete and target_complete: break

    already_conceive = bool(conceive)

    if all([sender_condom + safe_time < time.time(), target_condom + safe_time < time.time(), not masturbation, not already_conceive]):
        conceive = sender_id if (random.random() < 0.15 * (len(mp_room) if mp else 1) * ((2 * sender_aphrodisiac) if sender_aphrodisiac else 1)) else ""
        if conceive:
            conceive_count += 1
            conceive_time = round(time.time(), 2)

    # 获取目标昵称
    target_nickname = (await client.api.call_action('get_stranger_info', user_id=target_id)).get('nick', target_id)
    sender_nickname = (await client.api.call_action('get_stranger_info', user_id=sender_id)).get('nick', sender_id)

    # 随机时长和注入量
    duration = format((len(mp_room) if mp else 1) * (2 * sender_aphrodisiac if sender_aphrodisiac else 1) * random.uniform(1, 60 * (2 if target_aphrodisiac else 1)), '.2f')
    V = round((len(mp_room) if mp else 1) * (2 * sender_aphrodisiac if sender_aphrodisiac else 1) * random.uniform(1, 100 * (2 if target_aphrodisiac else 1)), 2)

    ccnt = len(mp_room) if mp else 1
    cvol = V

    # 更新target的记录
    for item in data:
        if item.get(KEY_ID) == (mp_target if mp else target_id):
            item[KEY_COUNT] = item.get(KEY_COUNT, 0) + (len(mp_room) if mp else 1)
            item[KEY_VOL] = round(item.get(KEY_VOL, 0.0) + V, 2)
            item[KEY_CONCEIVE] = conceive
            item[KEY_CONCEIVE_COUNT] = conceive_count
            item[KEY_CONCEIVE_TIME] = conceive_time
            item[KEY_APHRODISIAC] = False
            cvol = item.get(KEY_VOL, 0.0)
            ccnt = item.get(KEY_COUNT, 0)
            break
    else:
        # 没找到则在 data 新增 target 的记录
        data.append({
            KEY_ID: mp_target if mp else target_id,
            KEY_COUNT: ccnt,
            KEY_VOL: cvol,
            KEY_FIRST: sender_id,
            KEY_NUM: 0,
            KEY_CONDOM: 0.0,
            KEY_CONCEIVE: conceive,
            KEY_CONCEIVE_COUNT: conceive_count,
            KEY_CONCEIVE_TIME: conceive_time,
            KEY_APHRODISIAC: False,
        })

    # 更新sender的记录
    for uid in mp_room if mp else range(1):
        for item in data:
            if item.get(KEY_ID) == (uid if mp else sender_id):
                item[KEY_NUM] = item.get(KEY_NUM, 0) + 1
                item[KEY_APHRODISIAC] = False
                break
        # 如果是第一次作为 sender 执行 ccb，就新建一条记录
        else:
            data.append({
                KEY_ID: uid if mp else sender_id,
                KEY_COUNT: 0,
                KEY_VOL: 0.0,
                KEY_FIRST: "",
                KEY_NUM: 1,
                KEY_CONDOM: 0.0,
                KEY_CONCEIVE: "",
                KEY_CONCEIVE_COUNT: 0,
                KEY_CONCEIVE_TIME: 0.0,
                KEY_APHRODISIAC: False
            })

    chain = [
        Comp.Plain(
            f"{sender_nickname}，你ccb了 {target_nickname} {duration}min, 向ta灌注了{V:.2f}ml的生命因子"),
        Comp.Image.fromURL(pic),
        Comp.Plain(f"这是ta的初体验。" if is_first else f"这是ta的第{ccnt}次。"),
        Comp.Plain(f"" if is_first else f"ta被累积灌注了{cvol}ml的生命因子。"),
        Comp.Plain(f"ta怀孕了" if conceive and not already_conceive else "")
    ]

    if masturbation:
        chain = [
            Comp.Plain(f"你滋味了{duration}min, 给自己灌注了{V:.2f}ml的生命因子"),
            Comp.Image.fromURL(pic),
            Comp.Plain(f"这是你的初体验。" if is_first else f"这是你的第{ccnt}次。"),
            Comp.Plain(f"" if is_first else f"你被累积灌注了{cvol}ml的生命因子。"),
            Comp.Plain(f"你怀孕了" if conceive and not already_conceive else "")
        ]
    if mp:
        chain = [
            Comp.Plain(f"{owner_nickname}等{len(mp_room)}人ccb了 {target_nickname} {duration}min 向ta被灌注了总共{V:.2f}ml的生命因子"),
            Comp.Image.fromURL(pic),
            Comp.Plain(f"这是ta的初体验。" if is_first else f"这是ta的第{ccnt}次。"),
            Comp.Plain(f"" if is_first else f"ta被累积灌注了{cvol}ml的生命因子。"),
            Comp.Plain(f"ta怀孕了" if conceive and not already_conceive else "")
        ]

    # 写回文件
    save_data(data, event.get_group_id())

    # 发送消息
    return event.chain_result(chain)


def pre_check(event: AstrMessageEvent):
    data = load_data(event.get_group_id())
    for item in data:
        if item.get(KEY_CONCEIVE, "") and (item.get(KEY_CONCEIVE_TIME, 0.0) + conceive_time <= time.time()):
            item[KEY_CONCEIVE] = ""
            item[KEY_CONCEIVE_TIME] = 0.0
        if item.get(KEY_CONDOM, 0.0) + safe_time <= time.time():
            item[KEY_CONDOM] = 0.0
    save_data(data, event.get_group_id())


@register("ccb", "efojug", "和群友ccb的插件", "2.1.8")
class ccb(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("fake")
    async def fake(self, event: AstrMessageEvent):
        global fake, fake_user, fake_target
        pre_check(event)
        if event.get_platform_name() == "aiocqhttp":
            sender_id = event.get_sender_id()
            # if sender_id in {"3307566484", "3183970497"}:
            if not fake:
                self_id = event.get_self_id()
                messages = event.get_messages()
                target_id = next((str(seg.qq) for seg in messages if isinstance(seg, Comp.At) and str(seg.qq) != self_id), None)
                if target_id:
                    try:
                        target_nickname = (await event.bot.api.call_action('get_stranger_info', user_id=target_id)).get(
                            'nick', target_id)
                        fake = True
                        fake_user = sender_id
                        fake_target = target_id
                        yield event.plain_result(f"成功 下一条命令将由{target_nickname}执行\n再次使用此命令以解除")
                    except Exception as e:
                        print(e)
            else:
                fake = False
                yield event.plain_result("已解除")
            # else:
            #     yield event.plain_result("没有权限喵")

    @filter.command("ccb")
    async def ccb(self, event: AstrMessageEvent):
        global fake
        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() == "aiocqhttp":
            pre_check(event)
            yield await cb(event)
        fake = False

    @filter.command("rut")
    async def rut(self, event: AstrMessageEvent):
        global fake
        if event.get_platform_name() == "aiocqhttp":
            pre_check(event)
            # 解析基础信息
            messages = event.get_messages()
            sender_id = fake_target if fake and fake_user == event.get_sender_id() else event.get_sender_id()
            self_id = event.get_self_id()
            target_id = next((str(seg.qq) for seg in messages if isinstance(seg, Comp.At) and str(seg.qq) != self_id), sender_id)
            sender_nickname = (await event.bot.api.call_action('get_stranger_info', user_id=sender_id)).get('nick', sender_id)
            target_nickname = (await event.bot.api.call_action('get_stranger_info', user_id=target_id)).get('nick', target_id)
            data = load_data(event.get_group_id())
            for item in data:
                if item.get(KEY_ID) == target_id:
                    item[KEY_APHRODISIAC] = True
                    fake = False
                    save_data(data, event.get_group_id())
                    return event.plain_result(f"{sender_nickname}自己用了春药" if sender_id == target_id else f"{sender_nickname}对{target_nickname}用了春药")
        fake = False
        return None

    @filter.command("first")
    async def first(self, event: AstrMessageEvent):
        """
        /first @目标
        看看ta的第一次被谁夺走了
        """
        global fake
        messages = event.get_messages()
        self_id = event.get_self_id()
        sender_id = fake_target if fake and fake_user == event.get_sender_id() else event.get_sender_id()

        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() == "aiocqhttp":
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            pre_check(event)
            client = event.bot
            # 从 @ 中取目标
            target_id = next((str(seg.qq) for seg in messages if isinstance(seg, Comp.At) and str(seg.qq) != self_id), sender_id)

            # 获取目标昵称
            target_nickname = (await client.api.call_action('get_stranger_info', user_id=target_id)).get('nick', target_id)

            data = load_data(event.get_group_id())

            for item in data:
                if item.get(KEY_ID) == target_id:
                    first_id = item.get(KEY_FIRST)
                    if first_id:
                        # 获取第一次昵称
                        first_nickname = (await client.api.call_action('get_stranger_info', user_id=first_id)).get(
                            'nick', first_id)
                        chain = [
                            Comp.Plain(f"{target_nickname}的第一次给了{first_nickname}"),
                            Comp.Image.fromURL(get_avatar(first_id))
                        ]
                        fake = False
                        return event.chain_result(chain)

            chain = [
                Comp.Plain(f"{target_nickname}还是纯洁的哦~"),
                Comp.Image.fromURL(get_avatar(target_id))
            ]
            fake = False
            return event.chain_result(chain)
        return None

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
            pre_check(event)
            client = event.bot

            data = load_data(event.get_group_id())
            if not data:
                # 没有任何记录时给个友好提示
                fake = False
                return event.plain_result("当前还没有任何ccb记录")

            # 排序并取前 N（最多 5 条）
            N = min(5, len(data))
            top_by_count = sorted(data, key=lambda x: x.get(KEY_COUNT, 0), reverse=True)[:N]
            top_by_num = sorted(data, key=lambda x: x.get(KEY_NUM, 0), reverse=True)[:N]

            # 收集所有要查询昵称的 QQ 号（去重）
            uids = {item.get(KEY_ID) for item in top_by_count + top_by_num}

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
                u = item.get(KEY_ID)
                lines.append(f"{idx}. {nick_map[u]}  {item.get(KEY_COUNT)}次  被灌注了{item.get(KEY_VOL)}ml")

            lines.append("")  # 空行分隔
            lines.append("---ccb排行榜---")
            for idx, item in enumerate(top_by_num, start=1):
                u = item.get(KEY_ID)
                lines.append(f"{idx}. {nick_map[u]}  {item.get(KEY_NUM)}次")

            msg = "\n".join(lines)
            fake = False
            return event.plain_result(msg)
        return None

    @filter.command("stats")
    async def stats(self, event: AstrMessageEvent):
        """
        /stats @目标
        查看目标的状态
        """
        global fake
        messages = event.get_messages()
        self_id = event.get_self_id()

        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() == "aiocqhttp":
            from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
            assert isinstance(event, AiocqhttpMessageEvent)
            pre_check(event)
            client = event.bot
            sender_id = fake_target if fake and fake_user == event.get_sender_id() else event.get_sender_id()
            # 从 @ 中取目标
            target_id = next((str(seg.qq) for seg in messages if isinstance(seg, Comp.At) and str(seg.qq) != self_id), sender_id)

            # 获取目标昵称
            target_nickname = (await client.api.call_action('get_stranger_info', user_id=target_id)).get('nick', target_id)

            data = load_data(event.get_group_id())

            for item in data:
                if item.get(KEY_ID) == target_id:
                    # 计算剩余避孕时间
                    mins, secs = divmod(int(item.get(KEY_CONDOM, 0.0) + safe_time - time.time()), 60)
                    hours, mins = divmod(mins, 60)
                    msg = [f"{target_nickname}的状态：", f"ccb了{item.get(KEY_NUM, 0)}次" if item.get(KEY_NUM, 0) else "还没有ccb过别人",
                           f"被灌注了{item.get(KEY_COUNT, 0)}次，{item.get(KEY_VOL, 0.0)}ml" if item.get(KEY_COUNT, 0) else '',
                           f"ta的第一次给了{(await client.api.call_action('get_stranger_info', user_id=item.get(KEY_FIRST, ''))).get('nick', item.get(KEY_FIRST, ''))}" if item.get(KEY_FIRST, '') else "ta还是纯洁的",
                           f"怀孕了{item.get(KEY_CONCEIVE_COUNT, 0)}次" if item.get(KEY_CONCEIVE_COUNT, 0) else "还没有怀孕过",
                           f"正在孕育ta和{(await client.api.call_action('get_stranger_info', user_id=item.get(KEY_CONCEIVE, ''))).get('nick', item.get(KEY_CONCEIVE, ''))}的生命精华" if item.get(KEY_CONCEIVE, '') else "当前没有身孕",
                           "正在发情期" if item.get(KEY_APHRODISIAC, False) else '',
                           "没有避孕保护" if item.get(KEY_CONDOM, 0.0) + safe_time < time.time() else f"安全套剩余时间：{hours}h{mins}m{secs}s"]
                    fake = False
                    return event.plain_result("\n".join(msg))
            else:
                # 没找到记录，说明没有被 ccb 过
                fake = False
                return event.plain_result(f"{target_nickname}还是纯洁的哦~")
        return None

    @filter.command("condom")
    async def condom(self, event: AstrMessageEvent):
        global fake
        if event.get_platform_name() == "aiocqhttp":
            pre_check(event)
            sender_id = fake_target if fake and fake_user == event.get_sender_id() else event.get_sender_id()
            sender_nickname = (await event.bot.api.call_action('get_stranger_info', user_id=sender_id)).get('nick', sender_id)
            data = load_data(event.get_group_id())
            for item in data:
                if item.get(KEY_ID) == sender_id:
                    condom = item.get(KEY_CONDOM, 0.0)
                    if condom + 7200 <= time.time():
                        item[KEY_CONDOM] = round(time.time(), 2)
                        yield event.plain_result(f"{sender_nickname}使用了安全套, 接下来120分钟内不会怀孕, 再次使用可以摘下")
                    else:
                        item[KEY_CONDOM] = 0.0
                        yield event.plain_result(f"{sender_nickname}摘下了安全套")
                    break

            save_data(data, event.get_group_id())

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
            pre_check(event)
            client = event.bot
            messages = event.get_messages()
            self_id = event.get_self_id()
            sender_id = fake_target if fake and fake_user == event.get_sender_id() else event.get_sender_id()

            if command == "create":
                if not mp_created:
                    # 创建房间
                    target_id = next(
                        (str(seg.qq) for seg in messages if isinstance(seg, Comp.At) and str(seg.qq) != self_id),
                        sender_id)
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
                        fake = False
                        yield event.plain_result("房主不能离开房间，请使用/mp break结束")
                        return
                    if sender_id in mp_room:
                        mp_room.remove(sender_id)
                        sender_nickname = (await client.api.call_action('get_stranger_info', user_id=sender_id)).get(
                            'nick', sender_id)
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
                        async for res in cb(event, True):
                            yield res
                    else:
                        yield event.plain_result("只有房主才能开始mp")
                else:
                    yield event.plain_result("还没有房间呢，使用/mp create @目标 创建一个")

            elif command == "break":
                if mp_created:
                    if sender_id == mp_owner:
                        mp_created = False
                        mp_owner = ""
                        mp_room = []
                        mp_target = ""
                    else:
                        yield event.plain_result("只有房主才能解散房间")
                else:
                    yield event.plain_result("还没有房间呢，使用/mp create @目标 创建一个")

            else:
                yield event.plain_result("未知的命令")
            fake = False

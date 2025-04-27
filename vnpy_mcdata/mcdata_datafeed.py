from datetime import datetime, timedelta
from collections.abc import Callable
from functools import lru_cache

from icetcore import TCoreAPI, BarType

from vnpy.trader.setting import SETTINGS
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, HistoryRequest, TickData
from vnpy.trader.utility import ZoneInfo, extract_vt_symbol
from vnpy.trader.datafeed import BaseDatafeed


# 时间周期映射
INTERVAL_VT2MC: dict[Interval, tuple] = {
    Interval.MINUTE: (BarType.MINUTE, 1),
    Interval.HOUR: (BarType.MINUTE, 60),
    Interval.DAILY: (BarType.DK, 1)
}

# 时间调整映射
INTERVAL_ADJUSTMENT_MAP: dict[Interval, timedelta] = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.HOUR: timedelta(hours=1),
    Interval.DAILY: timedelta()
}

# 交易所映射
EXCHANGE_MC2VT: dict[str, Exchange] = {
    "CFFEX": Exchange.CFFEX,
    "SHFE": Exchange.SHFE,
    "CZCE": Exchange.CZCE,
    "DCE": Exchange.DCE,
    "INE": Exchange.INE,
    "GFEX": Exchange.GFEX,
    "SSE": Exchange.SSE,
    "SZSE": Exchange.SZSE,
}

# 时区常量
CHINA_TZ = ZoneInfo("Asia/Shanghai")


class McdataDatafeed(BaseDatafeed):
    """MultiCharts的数据服务接口"""

    def __init__(self) -> None:
        """构造函数"""
        self.apppath: str = SETTINGS["datafeed.username"]       # 传参用的字段名
        if not self.apppath:
            self.apppath = "D:/MCTrader14/APPs"                 # 默认程序路径

        self.inited: bool = False                               # 初始化状态

        self.api: TCoreAPI = None                               # API实例

    def init(self, output: Callable = print) -> bool:
        """初始化"""
        # 禁止重复初始化
        if self.inited:
            return True

        # 创建API实例并连接
        self.api = TCoreAPI(apppath=self.apppath)
        self.api.connect()

        # 返回初始化状态
        self.inited = True
        return True

    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> list[BarData]:
        """查询K线数据"""
        if not self.inited:
            n: bool = self.init(output)
            if not n:
                return []

        # 检查合约代码
        mc_symbol: str = to_mc_symbol(req.vt_symbol)
        if not mc_symbol:
            output(f"查询K线数据失败：不支持的合约代码{req.vt_symbol}")
            return []

        # 检查K线周期
        mc_interval, mc_window = INTERVAL_VT2MC.get(req.interval, ("", ""))
        if not mc_interval:
            output(f"查询K线数据失败：不支持的时间周期{req.interval.value}")
            return []

        # 获取时间戳平移幅度
        adjustment: timedelta = INTERVAL_ADJUSTMENT_MAP[req.interval]

        # 逐日查询K线数据
        all_quote_history: list[dict] = []
        query_start: datetime = req.start

        while query_start.date() <= req.end.date():
            if req.interval in [Interval.DAILY, Interval.HOUR]:
                quote_history: list[dict] = self.api.getquotehistory(
                    mc_interval,
                    mc_window,
                    mc_symbol,
                    req.start.strftime("%Y%m%d%H"),
                    req.end.strftime("%Y%m%d%H")
                )

                if quote_history:
                    all_quote_history.extend(quote_history)
                break

            query_end: datetime = query_start + timedelta(days=1)

            # 发起K线查询
            quote_history = self.api.getquotehistory(
                mc_interval,
                mc_window,
                mc_symbol,
                query_start.strftime("%Y%m%d%H"),
                query_end.strftime("%Y%m%d%H")
            )

            # 保存查询结果
            if quote_history:
                all_quote_history.extend(quote_history)

            # 更新查询起始时间
            query_start = query_end

        # 失败则直接返回
        if not all_quote_history:
            output(f"获取{req.symbol}合约{req.start}-{req.end}历史数据失败")
            return []

        # 转换数据格式
        bars: list[BarData] = []

        for history in all_quote_history:
            dt: datetime = (history["DateTime"] - adjustment).replace(tzinfo=CHINA_TZ)
            if req.interval == Interval.DAILY:
                dt = dt.replace(hour=0, minute=0)

            bar: BarData = BarData(
                symbol=req.symbol,
                exchange=req.exchange,
                interval=req.interval,
                datetime=dt,
                open_price=history["Open"],
                high_price=history["High"],
                low_price=history["Low"],
                close_price=history["Close"],
                volume=history["Volume"],
                open_interest=history["OpenInterest"],
                gateway_name="MCDATA"
            )
            bars.append(bar)

        return bars

    def query_tick_history(self, req: HistoryRequest, output: Callable = print) -> list[TickData]:
        """查询Tick数据（暂未支持）"""
        return []


@lru_cache(maxsize=10000)
def to_mc_symbol(vt_symbol: str) -> str:
    """转换为MC合约代码"""
    symbol, exchange = extract_vt_symbol(vt_symbol)

    # 目前只支持期货交易所合约
    if exchange in {
        Exchange.CFFEX,
        Exchange.SHFE,
        Exchange.CZCE,
        Exchange.DCE,
        Exchange.INE,
        Exchange.GFEX,
    }:
        # 期货合约
        if len(symbol) <= 8:
            suffix: str = check_perpetual(symbol)

            # 连续合约
            if suffix:
                product: str = symbol.replace(suffix, "")
                return f"TC.F.{exchange.value}.{product}.{suffix}"
            # 交易合约
            else:
                # 获取产品代码
                product = get_product(symbol)

                # 获取合约月份
                month: str = symbol[-2:]

                # 获取合约年份
                year: str = symbol.replace(product, "").replace(month, "")
                if len(year) == 1:      # 郑商所特殊处理
                    if int(year) <= 5:
                        year = "2" + year
                    else:
                        year = "1" + year

                return f"TC.F.{exchange.value}.{product}.20{year}{month}"
        # 期货期权合约
        else:
            product = get_product(symbol)
            left: str = symbol.replace(product, "")

            # 中金所、大商所、广期所
            if "-" in left:
                if "-C-" in left:
                    option_type: str = "C"
                elif "-P-" in left:
                    option_type = "P"

                time_end: int = left.index("-") - 1
                strike_start: int = time_end + 4
            # 上期所、能交所、郑商所
            else:
                if "C" in left:
                    option_type = "C"
                    time_end = left.index("C") - 1
                elif "P" in left:
                    option_type = "P"
                    time_end = left.index("P") - 1

                strike_start = time_end + 2

            # 获取关键信息
            strike: str = left[strike_start:]
            time_str: str = left[:time_end + 1]
            month = time_str[-2:]
            year = time_str.replace(month, "")

            # 郑商所特殊处理
            if len(year) == 1:
                if int(year) <= 5:
                    year = "2" + year
                else:
                    year = "1" + year

            return f"TC.O.{exchange.value}.{product}.20{year}{month}.{option_type}.{strike}"

    return ""


def get_product(symbol: str) -> str:
    """获取期货产品代码"""
    buf: list[str] = []

    for w in symbol:
        if w.isdigit():
            break
        buf.append(w)

    return "".join(buf)


def check_perpetual(symbol: str) -> str:
    """判断是否为连续合约"""
    for suffix in [
        "HOT",
        "HOT/Q",
        "HOT/H",
        "000000"
    ]:
        if symbol.endswith(suffix):
            return suffix

    return ""

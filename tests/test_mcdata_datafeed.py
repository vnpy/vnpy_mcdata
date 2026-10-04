import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, HistoryRequest


# 本机不必安装 icetcore。导入前替换该模块，查询时也不调用 connect。
class _BarType:
    MINUTE: str = "MINUTE"
    DK: str = "DK"
    TICK: str = "TICK"


class _TCoreAPI:
    def __init__(self, apppath: str = "") -> None:
        self.apppath: str = apppath

    def connect(self) -> None:
        raise AssertionError("TCoreAPI.connect")


_icetcore: ModuleType = ModuleType("icetcore")
_icetcore.TCoreAPI = _TCoreAPI  # type: ignore[attr-defined]
_icetcore.BarType = _BarType  # type: ignore[attr-defined]
sys.modules["icetcore"] = _icetcore

from vnpy_mcdata import mcdata_datafeed as mcdata_module  # noqa: E402
from vnpy_mcdata.mcdata_datafeed import (  # noqa: E402
    CHINA_TZ,
    INTERVAL_VT2MC,
    McdataDatafeed,
    to_mc_symbol,
)


class _QuoteApi:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows: list[dict[str, object]] = rows
        self.calls: list[tuple[object, ...]] = []

    def getquotehistory(self, *args: object) -> list[dict[str, object]]:
        self.calls.append(args)
        return self.rows


def _request(interval: Interval, end: datetime) -> HistoryRequest:
    return HistoryRequest(
        symbol="rb2410",
        exchange=Exchange.SHFE,
        start=datetime(2024, 1, 15, 9, 0),
        end=end,
        interval=interval,
    )


def _feed(rows: list[dict[str, object]]) -> tuple[McdataDatafeed, _QuoteApi]:
    api: _QuoteApi = _QuoteApi(rows)
    feed: McdataDatafeed = McdataDatafeed()
    feed.inited = True
    feed.api = api  # type: ignore[assignment]
    return feed, api


def test_to_mc_symbol() -> None:
    module_file: Path = Path(mcdata_module.__file__ or "").resolve()
    assert module_file.is_relative_to(Path(__file__).resolve().parents[1])

    cases: list[tuple[str, str]] = [
        ("rb2410.SHFE", "TC.F.SHFE.rb.202410"),
        ("i2501.DCE", "TC.F.DCE.i.202501"),
        ("IF2410.CFFEX", "TC.F.CFFEX.IF.202410"),
        ("sc2410.INE", "TC.F.INE.sc.202410"),
        ("si2410.GFEX", "TC.F.GFEX.si.202410"),
        ("TA501.CZCE", "TC.F.CZCE.TA.202501"),
        ("rbHOT.SHFE", "TC.F.SHFE.rb.HOT"),
        ("IO2410-C-4000.CFFEX", "TC.O.CFFEX.IO.202410.C.4000"),
        ("IO2410-P-4000.CFFEX", "TC.O.CFFEX.IO.202410.P.4000"),
        ("cu2410C70000.SHFE", "TC.O.SHFE.cu.202410.C.70000"),
        ("600000.SSE", ""),
    ]
    vt_symbol: str
    expected: str
    for vt_symbol, expected in cases:
        assert to_mc_symbol(vt_symbol) == expected


def test_query_minute_bar() -> None:
    feed, api = _feed([
        {
            "DateTime": datetime(2024, 1, 15, 10, 1),
            "Open": 100.5,
            "High": 110.0,
            "Low": 90.25,
            "Close": 105.0,
            "Volume": 12.0,
            "OpenInterest": 33.0,
        }
    ])
    logs: list[str] = []
    bars: list[BarData] = feed.query_bar_history(
        _request(Interval.MINUTE, datetime(2024, 1, 15, 15, 0)),
        output=logs.append,
    )

    assert logs == []
    assert api.calls == [(
        INTERVAL_VT2MC[Interval.MINUTE][0],
        INTERVAL_VT2MC[Interval.MINUTE][1],
        "TC.F.SHFE.rb.202410",
        "2024011500",
        "2024011600",
    )]
    assert len(bars) == 1
    bar: BarData = bars[0]
    assert bar.symbol == "rb2410"
    assert bar.exchange == Exchange.SHFE
    assert bar.interval == Interval.MINUTE
    assert bar.datetime == datetime(2024, 1, 15, 10, 0, tzinfo=CHINA_TZ)
    assert bar.open_price == 100.5
    assert bar.high_price == 110.0
    assert bar.low_price == 90.25
    assert bar.close_price == 105.0
    assert bar.volume == 12.0


def test_query_daily_bar() -> None:
    feed, api = _feed([
        {
            "DateTime": datetime(2024, 1, 15, 16, 0),
            "Open": 100.5,
            "High": 110.0,
            "Low": 90.25,
            "Close": 105.0,
            "Volume": 12.0,
            "OpenInterest": 33.0,
        }
    ])
    logs: list[str] = []
    end: datetime = datetime(2024, 1, 16, 15, 0)
    bars: list[BarData] = feed.query_bar_history(
        _request(Interval.DAILY, end),
        output=logs.append,
    )

    assert logs == []
    assert api.calls == [(
        INTERVAL_VT2MC[Interval.DAILY][0],
        INTERVAL_VT2MC[Interval.DAILY][1],
        "TC.F.SHFE.rb.202410",
        "2024011509",
        "2024011615",
    )]
    assert len(bars) == 1
    bar: BarData = bars[0]
    assert bar.symbol == "rb2410"
    assert bar.exchange == Exchange.SHFE
    assert bar.interval == Interval.DAILY
    assert bar.datetime == datetime(2024, 1, 15, tzinfo=CHINA_TZ)
    assert bar.open_price == 100.5
    assert bar.high_price == 110.0
    assert bar.low_price == 90.25
    assert bar.close_price == 105.0
    assert bar.volume == 12.0

from datetime import datetime, timezone

from app.domain.aggregation import Bar, group_consecutive_trading_days


def _bar(date_str: str, o=1.0, h=1.0, l=1.0, c=1.0, v=100.0) -> Bar:
    y, m, d = (int(x) for x in date_str.split("-"))
    return Bar(ts=datetime(y, m, d, tzinfo=timezone.utc), open=o, high=h, low=l, close=c, volume=v)


def test_d2_groups_skip_juneteenth_holiday_like_dxlink():
    # Dias de trading reales alrededor del feriado de Juneteenth 2026-06-19
    # (viernes) -- confirmado en vivo que DxLink empareja 06-18(jue) con
    # 06-22(lun), saltandose el feriado, y no con 06-17.
    bars = [_bar(d) for d in ("2026-06-16", "2026-06-17", "2026-06-18", "2026-06-22", "2026-06-23", "2026-06-24")]
    groups = group_consecutive_trading_days(bars, 2)
    group_starts = [g.ts.date().isoformat() for g in groups]
    assert group_starts == ["2026-06-16", "2026-06-18", "2026-06-23"]


def test_d3_groups_skip_juneteenth_holiday_like_dxlink():
    bars = [_bar(d) for d in (
        "2026-06-15", "2026-06-16", "2026-06-17", "2026-06-18", "2026-06-22",
        "2026-06-23", "2026-06-24",
    )]
    groups = group_consecutive_trading_days(bars, 3)
    group_starts = [g.ts.date().isoformat() for g in groups]
    assert group_starts == ["2026-06-15", "2026-06-18"]


def test_incomplete_trailing_group_never_returned():
    # Solo 1 de 2 dias disponibles para el grupo que arrancaria en 06-18 --
    # no debe devolverse un grupo a medias.
    bars = [_bar("2026-06-16"), _bar("2026-06-17"), _bar("2026-06-18")]
    groups = group_consecutive_trading_days(bars, 2)
    assert [g.ts.date().isoformat() for g in groups] == ["2026-06-16"]


def test_aggregation_math_ohlcv():
    bars = [
        _bar("2026-06-16", o=10, h=12, l=9, c=11, v=100),
        _bar("2026-06-17", o=11, h=15, l=10, c=14, v=200),
    ]
    groups = group_consecutive_trading_days(bars, 2)
    assert len(groups) == 1
    g = groups[0]
    assert g.open == 10  # primera barra
    assert g.high == 15  # maximo
    assert g.low == 9    # minimo
    assert g.close == 14  # ultima barra
    assert g.volume == 300  # suma


def test_unsupported_group_size_returns_empty():
    assert group_consecutive_trading_days([_bar("2026-06-16")], 5) == []

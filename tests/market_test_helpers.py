from gw2radar.commercial.market_radar import PriceSnapshotInput


def mystic_coin_snapshots() -> list[PriceSnapshotInput]:
    return [
        PriceSnapshotInput(
            item_id="gw2:item:mystic_coin",
            item_name="Mystic Coin",
            buy_price_copper=12000,
            sell_price_copper=12500,
            volume=7000,
        ),
        PriceSnapshotInput(
            item_id="gw2:item:mystic_coin",
            item_name="Mystic Coin",
            buy_price_copper=15000,
            sell_price_copper=17000,
            volume=9000,
        ),
    ]


def clover_snapshot() -> PriceSnapshotInput:
    return PriceSnapshotInput(
        item_id="gw2:item:mystic_clover",
        item_name="Mystic Clover",
        buy_price_copper=0,
        sell_price_copper=24000,
        volume=1200,
    )

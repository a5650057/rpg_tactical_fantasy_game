from src.game_entities.item import Item
from typing import Sequence, Union, Optional, Set, Type, List
from pygamepopup.components import BoxElement, Button, TextElement, InfoBox
from src.services import (
    load_from_xml_manager as loader,
    load_from_tmx_manager as tmx_loader,
    menu_creator_manager,
)
from src.game_entities.player import Player

def interact_item(level, item: Item, item_button: Button, is_equipped: bool) -> None:
        """
        Handle the interaction with an item from player inventory or equipment

        Keyword arguments:
        item -- the concerned item
        button_position -- the position of the button representing the item on interface
        is_equipped -- a boolean indicating if the item is equipped or not
        """
        level.selected_item = item
        level.menu_manager.open_menu(
            menu_creator_manager.create_item_menu(
                {
                    "info_item": level.open_selected_item_description,
                    "throw_item": level.throw_selected_item,
                    "use_item": level.use_selected_item,
                    "unequip_item": level.unequip_selected_item,
                    "equip_item": level.equip_selected_item,
                },
                item_button.get_rect(),
                item,
                is_equipped=is_equipped,
            )
        )

def interact_trade_item(
    level,
    item: Item,
    item_button: Button,
    players: Sequence[Player],
    is_first_player_owner: bool,
) -> None:
    """
    Handle the interaction with an item from player inventory or equipment during a trade

    Keyword arguments:
    item -- the concerned item
    button_position -- the position of the button representing the item on interface
    players -- the players involved in the trade
    is_first_player_owner -- a boolean indicating if the player who initiated the trade is the
    owner of the item
    """
    level.selected_item = item
    level.menu_manager.open_menu(
        menu_creator_manager.create_trade_item_menu(
            {
                "info_item": level.open_selected_item_description,
                "trade_item": level.trade_item,
            },
            item_button.position,
            item,
            players,
            is_first_player_owner,
        ),
    )

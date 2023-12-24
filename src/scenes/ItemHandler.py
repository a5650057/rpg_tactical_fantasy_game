from src.game_entities.item import Item
from typing import Sequence, Union, Optional, Set, Type, List
from pygamepopup.components import BoxElement, Button, TextElement, InfoBox
from src.services import (
    load_from_xml_manager as loader,
    load_from_tmx_manager as tmx_loader,
    menu_creator_manager,
)
from src.game_entities.player import Player
from src.game_entities.equipment import Equipment
from src.services.menu_creator_manager import (
    create_save_dialog,
    create_event_dialog,
    INVENTORY_MENU_ID,
    SHOP_MENU_ID,
    CHARACTER_ACTION_MENU_ID,
)

from src.constants import (
    MAX_MAP_HEIGHT,
    MENU_WIDTH,
    MENU_HEIGHT,
    ITEM_MENU_WIDTH,
    ORANGE,
    ITEM_DELETE_MENU_WIDTH,
    ITEM_INFO_MENU_WIDTH,
    TILE_SIZE,
    BLACK,
    WIN_HEIGHT,
    WIN_WIDTH,
    GRID_WIDTH,
    GRID_HEIGHT,
)

from src.gui.fonts import fonts

from src.services.language import *

class ItemHandlerClass :

    def __init__(self,level) -> None:
        self.level =level
     

    def interact_item(self, item: Item, item_button: Button, is_equipped: bool) -> None:
            """
            Handle the interaction with an item from player inventory or equipment

            Keyword arguments:
            item -- the concerned item
            button_position -- the position of the button representing the item on interface
            is_equipped -- a boolean indicating if the item is equipped or not
            """
            self.level.selected_item = item
            self.level.menu_manager.open_menu(
                menu_creator_manager.create_item_menu(
                    {
                        "info_item": self.level.open_selected_item,
                        "throw_item": self.level.throw_selected,
                        "use_item": self.level.use_selected,
                        "unequip_item": self.level.unequip,
                        "equip_item": self.level.equip,
                    },
                    item_button.get_rect(),
                    item,
                    is_equipped=is_equipped,
                )
            )

    def interact_trade_item(
        self,
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
        self.level.selected_item = item
        self.level.menu_manager.open_menu(
            menu_creator_manager.create_trade_item_menu(
                {
                    "info_item": self.level.intemHandler.open_selected_item_description,
                    "trade_item": self.level.trade_item,
                },
                item_button.position,
                item,
                players,
                is_first_player_owner,
            ),
        )


    def unequip_selected_item(self) -> None:
        """
        Unequip the selected item of the active character if possible
        """
        self.level.menu_manager.close_active_menu()
        unequipped = self.level.selected_player.unequip(self.level.selected_item)
        result_message = (
            STR_THE_ITEM_CANNOT_BE_UNEQUIPPED_NOT_ENOUGH_SPACE_IN_UR_INVENTORY
        )
        if unequipped:
            result_message = STR_THE_ITEM_HAS_BEEN_UNEQUIPPED

            # Update equipment screen content
            new_equipment_menu = menu_creator_manager.create_equipment_menu(
                self.interact_item, self.level.selected_player.equipments
            )
            # Update the inventory menu (i.e. first menu backward)
            self.level.menu_manager.close_active_menu()
            self.level.menu_manager.open_menu(new_equipment_menu)
        element_grid = [
            [
                TextElement(
                    result_message, font=fonts["ITEM_DESC_FONT"], margin=(20, 0, 20, 0)
                )
            ]
        ]
        self.level.menu_manager.open_menu(
            InfoBox(
                str(self.level.selected_item),
                element_grid,
                width=ITEM_INFO_MENU_WIDTH,
            )
        )


    def equip_selected_item(self) -> None:
            """
            Equip the selected item of the active character if possible
            """
            self.level.menu_manager.close_active_menu()
            # Try to equip the item
            return_equipped: int = self.level.selected_player.equip(self.level.selected_item)
            if return_equipped == -1:
                # Item can't be equipped by this player
                result_message = (
                    f_THIS_ITEM_CANNOT_BE_EQUIPPED_PLAYER_DOESNT_SATISFY_THE_REQUIREMENTS(
                        self.level.selected_player
                    )
                )
            else:
                # In this case returned value is > 0, item has been equipped
                result_message = STR_THE_ITEM_HAS_BEEN_EQUIPPED
                if return_equipped == 1:
                    result_message += (
                        STR_PREVIOUS_EQUIPPED_ITEM_HAS_BEEN_ADDED_TO_YOUR_INVENTORY
                    )

                # Inventory has changed
                self.level.refresh_inventory()
            element_grid = [
                [
                    TextElement(
                        result_message, font=fonts["ITEM_DESC_FONT"], margin=(20, 0, 20, 0)
                    )
                ]
            ]
            self.level.menu_manager.open_menu(
                InfoBox(
                    str(self.level.selected_item),
                    element_grid,
                    width=ITEM_INFO_MENU_WIDTH,
                )
            )


    def use_selected_item(self) -> None:
        """
        Handle the use of the selected item if possible.
        Remove it if it can't be used anymore.
        """
        # Try to use the object
        used, result_messages = self.level.selected_player.use_item(self.level.selected_item)
        # Inventory display is update if object has been used
        if used:
            self.level.menu_manager.close_active_menu()
            self.level.refresh_inventory()
        entries = [
            [TextElement(message, font=fonts["ITEM_DESC_FONT"], margin=(10, 0, 10, 0))]
            for message in result_messages
        ]
        self.level.menu_manager.open_menu(
            InfoBox(
                str(self.level.selected_item),
                entries,
                width=ITEM_INFO_MENU_WIDTH,
            )
        )


    def throw_selected_item(self) -> None:
            """
            Remove the selected item from player inventory/equipment
            """
            self.level.menu_manager.close_active_menu()
            # Remove item from inventory/equipment according to the index
            if isinstance(
                self.level.selected_item, Equipment
            ) and self.level.selected_player.has_exact_equipment(self.level.selected_item):
                self.level.selected_player.remove_equipment(self.level.selected_item)
                equipments = list(self.level.selected_player.equipments)
                new_items_menu = menu_creator_manager.create_equipment_menu(
                    self.interact_item, equipments
                )
            else:
                self.level.selected_player.remove_item(self.level.selected_item)
                free_spaces: int = self.level.selected_player.nb_items_max - len(
                    self.level.selected_player.items
                )
                items: list[Optional[Item]] = (
                    list(self.level.selected_player.items) + [None] * free_spaces
                )
                new_items_menu = menu_creator_manager.create_inventory_menu(
                    self.interact_item, items, self.level.selected_player.gold
                )
            # Refresh the inventory menu
            self.level.menu_manager.replace_given_menu(INVENTORY_MENU_ID, new_items_menu)
            grid_elements = [
                [
                    TextElement(
                        STR_ITEM_HAS_BEEN_THROWN_AWAY,
                        font=fonts["ITEM_DESC_FONT"],
                        margin=(20, 0, 20, 0),
                    )
                ]
            ]
            self.level.menu_manager.open_menu(
                InfoBox(
                    str(self.level.selected_item),
                    grid_elements,
                    width=ITEM_DELETE_MENU_WIDTH,
                )
            )
            self.level.selected_item = None



    def open_selected_item_description(self) -> None:
        self.level.menu_manager.open_menu(
            menu_creator_manager.create_item_description_menu(self.level.selected_item)
        )
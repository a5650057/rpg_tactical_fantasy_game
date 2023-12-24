from typing import TYPE_CHECKING
from src.gui.position import Position
from src.services import (
    menu_creator_manager,
)
from src.scenes.scene import QuitActionKind
import pygame
from src.game_entities.movable import Movable
from typing import Sequence
from src.game_entities.character import Character
from src.constants import (
    TILE_SIZE,
)
if TYPE_CHECKING:
    from .level_scene import LevelScene
CHARACTER_ACTION_MENU_ID = "character_action"


class InputHandlerClass :
    def __init__(self,level) -> None:
        self.level = level



    def click(self, button: int, position: Position,EntityTurn,LevelStatus) -> QuitActionKind:
            """
            Handle the triggering of a click event.

            Keyword arguments:
            button -- an integer value representing which mouse button has been pressed
            (1 for left button, 2 for middle button, 3 for right button)
            position -- the position of the mouse
            """
            # No event if there is an animation or if it is not player turn
            if self.level.animation:
                return QuitActionKind.CONTINUE
            if button == 1:
                self.left_click(position,EntityTurn,LevelStatus)
            elif button == 3:
                self.right_click()

            if self.level.game_phase == LevelStatus.VERY_BEGINNING:
                # Update game phase if dialogs at the very beginning are all closed
                if not self.level.menu_manager.active_menu:
                    self.level.game_phase = LevelStatus.INITIALIZATION

            return QuitActionKind.CONTINUE
    
    def left_click(self, position: Position ,EntityTurn,LevelStatus) -> None:
        """
        Handle the triggering of a left-click event.

        Keyword arguments:
        position -- the position of the mouse
        """
        if self.level.menu_manager.active_menu:
            if (
                not self.level.menu_manager.active_menu.is_position_inside(position)
                and self.level.menu_manager.active_menu.identifier != CHARACTER_ACTION_MENU_ID
            ):
                self.level.menu_manager.close_active_menu()
            # TODO: check if the raw value could be replaced by a meaningful constant
            self.level.menu_manager.click(1, position)
            return
        # Player can only react to active menu if it is not his turn
        if self.level.side_turn is not EntityTurn.PLAYER:
            return
        position_inside_level = self.level._compute_relative_position(position)
        if self.level.selected_player is not None:
            if self.level.game_phase is not LevelStatus.INITIALIZATION:
                if self.level.possible_moves:
                    # Player is waiting to move
                    for move in self.level.possible_moves:
                        if pygame.Rect(move, (TILE_SIZE, TILE_SIZE)).collidepoint(
                            position_inside_level
                        ):
                            path = self.level.determine_path_to(move, self.level.possible_moves)
                            self.level.selected_player.set_move(path)
                            self.level.possible_moves = {}
                            self.level.possible_attacks = []
                            return
                    # Player click somewhere that is not a valid pos
                    self.level.selected_player.selected = False
                    self.level.selected_player = None
                elif self.level.possible_attacks:
                    # Player is waiting to attack
                    for attack in self.level.possible_attacks:
                        if pygame.Rect(attack, (TILE_SIZE, TILE_SIZE)).collidepoint(
                            position_inside_level
                        ):
                            entity = self.level.get_entity_on_tile(attack)
                            self.level.duel(
                                self.level.selected_player,
                                entity,
                                self.level.players + self.level.entities.allies,
                                self.level.entities.foes,
                                self.level.selected_player.attack_kind,
                            )
                            # Turn is finished
                            self.level.end_active_character_turn(clear_menus=False)
                            return
                elif self.level.possible_interactions:
                    # Player is waiting to interact
                    for interact in self.level.possible_interactions:
                        if pygame.Rect(interact, (TILE_SIZE, TILE_SIZE)).collidepoint(
                            position_inside_level
                        ):
                            entity = self.level.get_entity_on_tile(interact)
                            self.level.interact(self.level.selected_player, entity, interact)
                            return
            else:
                # Initialization phase : player try to change the place of the selected character
                for tile in self.level.player_possible_placements:
                    if pygame.Rect(tile, (TILE_SIZE, TILE_SIZE)).collidepoint(
                        position_inside_level
                    ):
                        # Test if a character is on the tile, in this case, characters are swapped
                        entity = self.level.get_entity_on_tile(tile)
                        if entity:
                            entity.set_initial_pos(self.level.selected_player.position)

                        self.level.selected_player.set_initial_pos(tile)
                        return
            return
        for player in self.level.players:
            if player.is_on_position(position_inside_level):
                if player.turn_is_finished():
                    self.level.menu_manager.open_menu(
                        menu_creator_manager.create_status_menu(
                            {
                                "info_alteration": self.level.open_alteration_description,
                                "info_skill": self.level.open_skill_description,
                            },
                            player,
                        )
                    )
                else:
                    player.selected = True
                    self.level.selected_player = player
                    self.level.possible_moves = self.level.get_possible_moves(
                        tuple(player.position),
                        player.max_moves + player.get_stat_change("speed"),
                    )
                    self.level.possible_attacks = (
                        self.level.get_possible_attacks(
                            self.level.possible_moves, self.level.selected_player.reach, True
                        )
                        if player.can_attack()
                        else {}
                    )
                return
        for entity in self.level.entities.foes + self.level.entities.allies:
            if entity.is_on_position(position_inside_level):
                self.level.menu_manager.open_menu(
                    menu_creator_manager.create_status_entity_menu(
                        {
                            "info_alteration": self.level.open_alteration_description,
                            "info_skill": self.level.open_skill_description,
                        },
                        entity,
                    )
                )
                return

        is_initialization = self.level.game_phase is LevelStatus.INITIALIZATION
        self.level.menu_manager.open_menu(
            menu_creator_manager.create_main_menu(
                {
                    "save": self.level.open_save_menu,
                    "suspend": self.level.exit_game,
                    "start": self.level.start_game,
                    "diary": lambda: self.level.menu_manager.open_menu(
                        menu_creator_manager.create_diary_menu(self.level.diary_entries_text_element_set),
                    ),
                    "end_turn": self.level.end_turn,
                },
                is_initialization,
                position,
            )
        )
    def right_click(self) -> None:
        """
        Handle the triggering of a right-click event.
        """
        if self.level.selected_player:
            if self.level.possible_moves:
                # Player was waiting to move
                self.level.selected_player.selected = False
                self.level.selected_player = None
                self.level.possible_moves = {}
            elif self.level.menu_manager.active_menu is not None:
                # Test if player is on character's main menu, in this case,
                # current move should be cancelled if possible
                if self.level.menu_manager.active_menu.identifier == CHARACTER_ACTION_MENU_ID:
                    if self.level.selected_player.cancel_move():
                        if self.level.traded_items:
                            # Return traded items
                            for item in self.level.traded_items:
                                if item[1] == self.level.selected_player:
                                    item[2].remove_item(item[0])
                                    self.level.selected_player.set_item(item[0])
                                else:
                                    self.level.selected_player.remove_item(item[0])
                                    item[1].set_item(item[0])
                            self.level.traded_items.clear()
                        if self.level.traded_gold:
                            # Return traded gold
                            for gold in self.level.traded_gold:
                                if gold[1] == self.level.selected_player:
                                    self.level.selected_player.gold += gold[0]
                                    gold[2].gold -= gold[0]
                                else:
                                    self.level.selected_player.gold -= gold[0]
                                    gold[2].gold += gold[0]
                            self.level.traded_gold.clear()
                        self.level.selected_player.selected = False
                        self.level.selected_player = None
                        self.level.possible_moves = {}
                        self.level.menu_manager.clear_menus()
                    return
                self.level.menu_manager.close_active_menu()
            # Want to cancel an interaction (not already performed)
            elif self.level.possible_interactions or self.level.possible_attacks:
                self.level.selected_player.cancel_interaction()
                self.level.possible_interactions = []
                self.level.possible_attacks = []
                self.level.menu_manager.close_active_menu()
            return
        if self.level.menu_manager.active_menu is not None:
            self.level.menu_manager.close_active_menu()
        if self.level.watched_entity:
            self.level.watched_entity = None
            self.level.possible_moves = {}
            self.level.possible_attacks = []

    def key_down(self,keyname):
            """
            Handle the triggering of a key down event.

            Keyword arguments:
            keyname -- an integer value representing which key button is down
            """
            if keyname == pygame.K_ESCAPE:
                if (
                    self.level.menu_manager.active_menu is not None
                    and self.level.menu_manager.active_menu.identifier != CHARACTER_ACTION_MENU_ID
                ):
                    self.level.menu_manager.close_active_menu()
    def button_down(self, button: int, position: Position,EntityTurn) -> None:
            """
            Handle the triggering of a mouse button down event.

            Keyword arguments:
            button -- an integer value representing which mouse button is down
            (1 for left button, 2 for middle button, 3 for right button)
            position -- the position of the mouse
            """
            if button == 3:
                if (
                    not self.level.menu_manager.active_menu
                    and not self.level.selected_player
                    and self.level.side_turn is EntityTurn.PLAYER
                ):
                    position_inside_level = self.level._compute_relative_position(position)
                    for collection in self.level.entities.values():
                        for entity in collection:
                            if isinstance(
                                entity, Movable
                            ) and entity.get_rect().collidepoint(position_inside_level):
                                self.level.watched_entity = entity
                                self.level.possible_moves = self.level.get_possible_moves(
                                    tuple(entity.position), entity.max_moves
                                )
                                reach: Sequence[int] = self.level.watched_entity.reach
                                self.level.possible_attacks = {}
                                if entity.can_attack():
                                    self.level.possible_attacks = self.level.get_possible_attacks(
                                        self.level.possible_moves,
                                        reach,
                                        isinstance(entity, Character),
                                    )
                                return
    def motion(self, position: Position) -> None:
        """
        Handle the triggering of a motion event.

        Keyword arguments:
        position -- the position of the mouse
        """
        self.level.menu_manager.motion(position)

        if not self.level.menu_manager.active_menu:
            position_inside_level = self.level._compute_relative_position(position)
            self.level.hovered_entity = None
            for collection in self.level.entities.values():
                for entity in collection:
                    if entity.get_rect().collidepoint(position_inside_level):
                        self.level.hovered_entity = entity
                        return
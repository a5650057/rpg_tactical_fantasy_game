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
def click(scene: 'LevelScene', button: int, position: Position,EntityTurn,LevelStatus) -> QuitActionKind:
        """
        Handle the triggering of a click event.

        Keyword arguments:
        button -- an integer value representing which mouse button has been pressed
        (1 for left button, 2 for middle button, 3 for right button)
        position -- the position of the mouse
        """
        # No event if there is an animation or if it is not player turn
        if scene.animation:
            return QuitActionKind.CONTINUE
        if button == 1:
            left_click(scene,position,EntityTurn,LevelStatus)
        elif button == 3:
            right_click(scene)

        if scene.game_phase == LevelStatus.VERY_BEGINNING:
            # Update game phase if dialogs at the very beginning are all closed
            if not scene.menu_manager.active_menu:
                scene.game_phase = LevelStatus.INITIALIZATION

        return QuitActionKind.CONTINUE
def left_click(scene: 'LevelScene', position: Position ,EntityTurn,LevelStatus) -> None:
    """
    Handle the triggering of a left-click event.

    Keyword arguments:
    position -- the position of the mouse
    """
    if scene.menu_manager.active_menu:
        if (
            not scene.menu_manager.active_menu.is_position_inside(position)
            and scene.menu_manager.active_menu.identifier != CHARACTER_ACTION_MENU_ID
        ):
            scene.menu_manager.close_active_menu()
        # TODO: check if the raw value could be replaced by a meaningful constant
        scene.menu_manager.click(1, position)
        return
    # Player can only react to active menu if it is not his turn
    if scene.side_turn is not EntityTurn.PLAYER:
        return
    position_inside_level = scene._compute_relative_position(position)
    if scene.selected_player is not None:
        if scene.game_phase is not LevelStatus.INITIALIZATION:
            if scene.possible_moves:
                # Player is waiting to move
                for move in scene.possible_moves:
                    if pygame.Rect(move, (TILE_SIZE, TILE_SIZE)).collidepoint(
                        position_inside_level
                    ):
                        path = scene.determine_path_to(move, scene.possible_moves)
                        scene.selected_player.set_move(path)
                        scene.possible_moves = {}
                        scene.possible_attacks = []
                        return
                # Player click somewhere that is not a valid pos
                scene.selected_player.selected = False
                scene.selected_player = None
            elif scene.possible_attacks:
                # Player is waiting to attack
                for attack in scene.possible_attacks:
                    if pygame.Rect(attack, (TILE_SIZE, TILE_SIZE)).collidepoint(
                        position_inside_level
                    ):
                        entity = scene.get_entity_on_tile(attack)
                        scene.duel(
                            scene.selected_player,
                            entity,
                            scene.players + scene.entities.allies,
                            scene.entities.foes,
                            scene.selected_player.attack_kind,
                        )
                        # Turn is finished
                        scene.end_active_character_turn(clear_menus=False)
                        return
            elif scene.possible_interactions:
                # Player is waiting to interact
                for interact in scene.possible_interactions:
                    if pygame.Rect(interact, (TILE_SIZE, TILE_SIZE)).collidepoint(
                        position_inside_level
                    ):
                        entity = scene.get_entity_on_tile(interact)
                        scene.interact(scene.selected_player, entity, interact)
                        return
        else:
            # Initialization phase : player try to change the place of the selected character
            for tile in scene.player_possible_placements:
                if pygame.Rect(tile, (TILE_SIZE, TILE_SIZE)).collidepoint(
                    position_inside_level
                ):
                    # Test if a character is on the tile, in this case, characters are swapped
                    entity = scene.get_entity_on_tile(tile)
                    if entity:
                        entity.set_initial_pos(scene.selected_player.position)

                    scene.selected_player.set_initial_pos(tile)
                    return
        return
    for player in scene.players:
        if player.is_on_position(position_inside_level):
            if player.turn_is_finished():
                scene.menu_manager.open_menu(
                    menu_creator_manager.create_status_menu(
                        {
                            "info_alteration": scene.open_alteration_description,
                            "info_skill": scene.open_skill_description,
                        },
                        player,
                    )
                )
            else:
                player.selected = True
                scene.selected_player = player
                scene.possible_moves = scene.get_possible_moves(
                    tuple(player.position),
                    player.max_moves + player.get_stat_change("speed"),
                )
                scene.possible_attacks = (
                    scene.get_possible_attacks(
                        scene.possible_moves, scene.selected_player.reach, True
                    )
                    if player.can_attack()
                    else {}
                )
            return
    for entity in scene.entities.foes + scene.entities.allies:
        if entity.is_on_position(position_inside_level):
            scene.menu_manager.open_menu(
                menu_creator_manager.create_status_entity_menu(
                    {
                        "info_alteration": scene.open_alteration_description,
                        "info_skill": scene.open_skill_description,
                    },
                    entity,
                )
            )
            return

    is_initialization = scene.game_phase is LevelStatus.INITIALIZATION
    scene.menu_manager.open_menu(
        menu_creator_manager.create_main_menu(
            {
                "save": scene.open_save_menu,
                "suspend": scene.exit_game,
                "start": scene.start_game,
                "diary": lambda: scene.menu_manager.open_menu(
                    menu_creator_manager.create_diary_menu(scene.diary_entries_text_element_set),
                ),
                "end_turn": scene.end_turn,
            },
            is_initialization,
            position,
        )
    )
def right_click(scene: 'LevelScene') -> None:
    """
    Handle the triggering of a right-click event.
    """
    if scene.selected_player:
        if scene.possible_moves:
            # Player was waiting to move
            scene.selected_player.selected = False
            scene.selected_player = None
            scene.possible_moves = {}
        elif scene.menu_manager.active_menu is not None:
            # Test if player is on character's main menu, in this case,
            # current move should be cancelled if possible
            if scene.menu_manager.active_menu.identifier == CHARACTER_ACTION_MENU_ID:
                if scene.selected_player.cancel_move():
                    if scene.traded_items:
                        # Return traded items
                        for item in scene.traded_items:
                            if item[1] == scene.selected_player:
                                item[2].remove_item(item[0])
                                scene.selected_player.set_item(item[0])
                            else:
                                scene.selected_player.remove_item(item[0])
                                item[1].set_item(item[0])
                        scene.traded_items.clear()
                    if scene.traded_gold:
                        # Return traded gold
                        for gold in scene.traded_gold:
                            if gold[1] == scene.selected_player:
                                scene.selected_player.gold += gold[0]
                                gold[2].gold -= gold[0]
                            else:
                                scene.selected_player.gold -= gold[0]
                                gold[2].gold += gold[0]
                        scene.traded_gold.clear()
                    scene.selected_player.selected = False
                    scene.selected_player = None
                    scene.possible_moves = {}
                    scene.menu_manager.clear_menus()
                return
            scene.menu_manager.close_active_menu()
        # Want to cancel an interaction (not already performed)
        elif scene.possible_interactions or scene.possible_attacks:
            scene.selected_player.cancel_interaction()
            scene.possible_interactions = []
            scene.possible_attacks = []
            scene.menu_manager.close_active_menu()
        return
    if scene.menu_manager.active_menu is not None:
        scene.menu_manager.close_active_menu()
    if scene.watched_entity:
        scene.watched_entity = None
        scene.possible_moves = {}
        scene.possible_attacks = []
def key_down(self, keyname):
        """
        Handle the triggering of a key down event.

        Keyword arguments:
        keyname -- an integer value representing which key button is down
        """
        if keyname == pygame.K_ESCAPE:
            if (
                self.menu_manager.active_menu is not None
                and self.menu_manager.active_menu.identifier != CHARACTER_ACTION_MENU_ID
            ):
                self.menu_manager.close_active_menu()
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
                not self.menu_manager.active_menu
                and not self.selected_player
                and self.side_turn is EntityTurn.PLAYER
            ):
                position_inside_level = self._compute_relative_position(position)
                for collection in self.entities.values():
                    for entity in collection:
                        if isinstance(
                            entity, Movable
                        ) and entity.get_rect().collidepoint(position_inside_level):
                            self.watched_entity = entity
                            self.possible_moves = self.get_possible_moves(
                                tuple(entity.position), entity.max_moves
                            )
                            reach: Sequence[int] = self.watched_entity.reach
                            self.possible_attacks = {}
                            if entity.can_attack():
                                self.possible_attacks = self.get_possible_attacks(
                                    self.possible_moves,
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
    self.menu_manager.motion(position)

    if not self.menu_manager.active_menu:
        position_inside_level = self._compute_relative_position(position)
        self.hovered_entity = None
        for collection in self.entities.values():
            for entity in collection:
                if entity.get_rect().collidepoint(position_inside_level):
                    self.hovered_entity = entity
                    return
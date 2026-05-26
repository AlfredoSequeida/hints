"""Accessibility backend to get elements from an application using Atspi."""

import logging
from typing import Literal

from gi import require_version

from hints.window_systems.window_system_type import WindowSystemType

require_version("Atspi", "2.0")
from gi.repository import Atspi

from hints.backends.backend import HintsBackend
from hints.backends.exceptions import AccessibleChildrenNotFoundError
from hints.child import Child
from hints.constants import ELEMENT_DETAIL_LOG_LEVEL

logger = logging.getLogger(__name__)


class AtspiBackend(HintsBackend):
    """Atspi backend class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend_name = "atspi"
        self.states = set()
        self.states_match_type = 0
        self.attributes = {}
        self.attributes_match_type = 0
        self.roles = set()
        self.roles_match_type = 0
        self.toolkit = ""
        self.toolkit_version = ""
        self.scale_factor = 1
        self._window_extents: tuple[int, int, int, int] | None = None

    def get_relative_and_absolute_extents(
        self, root: Atspi.Accessible
    ) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
        """Get absolute position, relative position, and extents for accessible
        element.

        Some DE/WMs like gnome don't yield the correct relative postions
        for elements for some tooklits (QT). This function computes the
        relative postion of elements from the absolute position and top
        level window extents. Except for toolkits that do not allow top
        level positioning.

        :param root: Accessible element to get extents for.
        :return: absolute_position, relative_position, and extents.
        """
        start_x, start_y, _, _ = self._window_extents

        # GTK4 and Wayland do not support absolute positioning, so we work off relative positions
        if self.window_system.window_system_type == WindowSystemType.WAYLAND or (
            self.toolkit == "GTK"
            and int(str(self.toolkit_version).split(".", maxsplit=1)[0]) >= 4
        ):

            relative_extents = root.get_extents(Atspi.CoordType.WINDOW)

            x = relative_extents.x
            y = relative_extents.y

            # Sometimes in GTK4 elements have negative relative positioning for
            # items in corners ie: (-1,0).
            if x == -1:
                x = abs(x)

            x *= self.scale_factor
            y *= self.scale_factor

            return (
                (
                    x + start_x,
                    y + start_y,
                ),
                (x, y),
                (
                    relative_extents.width * self.scale_factor,
                    relative_extents.height * self.scale_factor,
                ),
            )

        absolute_extents = root.get_extents(Atspi.CoordType.SCREEN)
        x = absolute_extents.x * self.scale_factor
        y = absolute_extents.y * self.scale_factor

        return (
            (x, y),
            (
                x - start_x,
                y - start_y,
            ),
            (
                absolute_extents.width * self.scale_factor,
                absolute_extents.height * self.scale_factor,
            ),
        )

    def validate_match_conditions(
        self,
        root: Atspi.Accessible,
        match_type: Literal["state", "role"],
    ) -> bool:
        """Validate matching conditions for atspi match types.

        :param root: Accessible element to validate.
        :param match_against: Set to match against.
        :param conditions: Condition to match for.
        :param match_type: The type of matching to do.
        """
        result = False
        match match_type:
            case "state":
                state_set = root.get_state_set()
                if self.states_match_type in {
                    Atspi.CollectionMatchType.ALL,
                    Atspi.CollectionMatchType.EMPTY,
                }:
                    result = all(
                        state_set.contains(state_to_match)
                        for state_to_match in self.states
                    )
                elif self.states_match_type == Atspi.CollectionMatchType.ANY:
                    result = any(
                        state_set.contains(state_to_match)
                        for state_to_match in self.states
                    )
                elif self.states_match_type == Atspi.CollectionMatchType.NONE:
                    result = not any(
                        state_set.contains(state_to_match)
                        for state_to_match in self.states
                    )

            case "role":
                role = root.get_role()
                if self.roles_match_type in {
                    Atspi.CollectionMatchType.ALL,
                    Atspi.CollectionMatchType.EMPTY,
                }:
                    # for all elements to match means the only role must be
                    # in the set (like any)
                    # the other way to think about this is that roles is just
                    # one to check ie: role = {a_single_role}, but that does not
                    # seem very useful.
                    result = role in self.roles
                elif self.roles_match_type == Atspi.CollectionMatchType.ANY:
                    result = role in self.roles
                elif self.roles_match_type == Atspi.CollectionMatchType.NONE:
                    result = role not in self.roles
        return result

    def recursively_get_children_of_interest(
        self,
        root: Atspi.Accessible,
        children: list[Child],
    ):
        """This is a fallback gathering method for when Applications do not
        implement the Collections interface.

        It is slower than using the Collection's interface, which is why
        it is a fallback method and not the primary way to gather
        accessible elements.

        :param root: Starting child.
        :param children: Set of coordinates for children to use to store
            found children coordinates.
        """

        absolute_position, relative_position, size = (
            self.get_relative_and_absolute_extents(root)
        )

        # exit early for elements that are not visible
        if relative_position[0] < 0 or relative_position[1] < 0:
            return

        try:
            if (
                self.validate_match_conditions(root, "state")
                and self.validate_match_conditions(root, "role")
                and self._window_extents
            ):
                if logger.isEnabledFor(ELEMENT_DETAIL_LOG_LEVEL):
                    logger.log(
                        ELEMENT_DETAIL_LOG_LEVEL,
                        "Accessible element matched. Name: %s, ID: %d",
                        root.name,
                        root.get_id(),
                    )
                    logger.log(ELEMENT_DETAIL_LOG_LEVEL, "role: %s", root.get_role())
                    logger.log(
                        ELEMENT_DETAIL_LOG_LEVEL,
                        "states: %s",
                        root.get_state_set().get_states(),
                    )

                children.append(
                    Child(
                        relative_position=(
                            relative_position[0],
                            relative_position[1],
                        ),
                        absolute_position=(
                            absolute_position[0],
                            absolute_position[1],
                        ),
                        width=size[0],
                        height=size[1],
                    )
                )
        except:
            pass

        for child_index in range(root.get_child_count()):
            self.recursively_get_children_of_interest(
                root.get_child_at_index(child_index),
                children,
            )

    def get_children_of_interest(
        self,
        root: Atspi.Accessible,
        children: list[Child],
    ):
        """Get Atspi Accessible children that match a given set of states
        recursively.

        :param root: Starting child.
        :param children: Set of coordinates for children to use to store
            found children coordinates.
        """

        match_rule = Atspi.MatchRule.new(
            Atspi.StateSet.new(list(self.states)),
            self.states_match_type,
            self.attributes,
            self.attributes_match_type,
            list(self.roles),
            self.roles_match_type,
            [],
            Atspi.CollectionMatchType.ALL,
            False,
        )

        collection = root.get_collection_iface()

        if collection and self._window_extents:
            matches = collection.get_matches(
                match_rule, Atspi.CollectionSortOrder.CANONICAL, 0, True
            )

            for match in matches:

                absolute_position, relative_position, size = (
                    self.get_relative_and_absolute_extents(match)
                )

                # exit early for elements that are not visible
                if relative_position[0] < 0 or relative_position[1] < 0:
                    continue

                if logger.isEnabledFor(ELEMENT_DETAIL_LOG_LEVEL):
                    logger.log(
                        ELEMENT_DETAIL_LOG_LEVEL,
                        "Accessible element matched. Name: %s, ID: %d",
                        match.name,
                        match.get_id(),
                    )
                    logger.log(ELEMENT_DETAIL_LOG_LEVEL, "role: %s", match.get_role())
                    logger.log(
                        ELEMENT_DETAIL_LOG_LEVEL,
                        "states: %s",
                        match.get_state_set().get_states(),
                    )

                children.append(
                    Child(
                        relative_position=(relative_position[0], relative_position[1]),
                        absolute_position=(absolute_position[0], absolute_position[1]),
                        width=size[0],
                        height=size[1],
                    )
                )
        else:
            logger.debug(
                "This application does not implement the collection interface,"
                " falling back to searching for Accessible elements recursively."
                " This could take a while depending on the number of elements in"
                " the application."
            )
            self.recursively_get_children_of_interest(
                root,
                children,
            )

    def get_atspi_active_window(self) -> Atspi.Accessible | None:
        """Get the current accessible window in focus with Atspi.

        :return: Atspi focused window / accessible root element.
        """
        desktop = Atspi.get_desktop(0)
        for app_index in range(desktop.get_child_count()):
            window = desktop.get_child_at_index(app_index)
            # Gnome creates a mutter application that is also focused.
            # This is not what we want, so we are skipping it.
            if "mutter-x11-frames" in window.get_description():
                continue
            for window_index in range(window.get_child_count()):
                current_window = window.get_child_at_index(window_index)
                if current_window is None:
                    continue
                # Some hidden windows that are minimized to status trays
                # (like discord) will still have the Atspi.StateType.Active
                # state, so the pid from the window manger allows us to filter
                # out such applications.
                if (
                    current_window.get_state_set().contains(Atspi.StateType.ACTIVE)
                    and current_window.get_process_id()
                    == self.window_system.focused_window_pid
                ):
                    return current_window

        return None

    def get_children(
        self,
    ) -> list[Child]:
        """Get coordinates of children.

        :return: The extents of the window containing the children and
            centered children coordinates.
        """
        children: list[Child] = []

        # The focused window cannot move while hints are gathered synchronously,
        # so resolve its extents once instead of per element.
        self._window_extents = self.window_system.focused_window_extents

        window = self.get_atspi_active_window()

        if window:
            application = window.get_application()

            self.toolkit = application.get_toolkit_name()
            self.toolkit_version = application.get_toolkit_version()

            application_rules = self.get_application_rules()

            self.states = set(application_rules["states"])
            self.states_match_type = application_rules["states_match_type"]
            self.attributes = application_rules["attributes"]
            self.attributes_match_type = application_rules["attributes_match_type"]
            self.roles = set(application_rules["roles"])
            self.roles_match_type = application_rules["roles_match_type"]
            self.scale_factor = application_rules["scale_factor"]

            self.get_children_of_interest(
                window,
                children,
            )

            logger.debug(
                "Finished gathering hints for '%s'. Toolkit: %s v:%s",
                self.window_system.focused_applicaiton_name,
                self.toolkit,
                self.toolkit_version,
            )

            if not children:
                raise AccessibleChildrenNotFoundError(window)

        return children

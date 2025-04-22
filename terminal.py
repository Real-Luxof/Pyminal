"""THE LUX TERMINAL! GLORIOUS!
Designed to "just work" in as many cases as possible.
You can use ANSI codes too!!
It supports \\n and \\r as well.
List of supported ANSI codes: ALL OF THEM!!! Plus some extras!
"ANSI" code to control alpha value of text: `\\x1b[{38/48 for fg/bg};3;{alpha value}m`
"ANSI" code to change fonts: `\\x1c[4;{font_name}!`
    If the font isn't in the `fonts` folder, nothing happens.
the `scroll_lock` variable allows you to lock the scrolling in place! Fun.

Doesn't support:
    `\\a` - Terminal bell (used for warnings iirc)
    '\\b' - Backspace
    ''"""

import pygame
from fonts.font_size_requirements import font_size_requirements
from threading import Thread
from os import listdir
from time import sleep
import logging
logging.basicConfig(filename="sendtoLuxofifdoesntworklol.txt", filemode="a", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


class letter:
    def __init__(
        self,
        letter: str,
        font: str,
        fg_color: list[int, int, int, int],
        bg_color: list[int, int, int, int],
        font_options: list[bool, bool, bool]
    ):
        self.letter = letter
        self.font = font
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.font_options = font_options
    
    def extract_attributes(
        self
    ) -> tuple[str, list[int, int, int, int], list[int, int, int, int], list[bool, bool, bool]]:
        """Get everything except the char in a tuple."""
        return (
            self.font,
            self.fg_color,
            self.bg_color,
            self.font_options
        )
    
    def __repr__(
        self
    ) -> str:
        return self.letter
    
    def __str__(
        self
    ) -> str:
        return self.letter

terminal_grid: list[list[letter]] = [[]]

pygame.init()
pygame.display.set_caption("LUX Terminal")
pygame.display.set_icon(pygame.image.load("icon.png"))
width = 1024
height = 600
max_height_chars = 50 # arbitrary
# no char_width because i choose to use proportional fonts too not just monospace
screen: pygame.Surface = pygame.display.set_mode((width, height), flags=pygame.SRCALPHA)

fonts: dict[pygame.font.Font] = {}
for font_name in listdir("fonts"):
    if not font_name.endswith(".ttf"):
        continue
    fonts[font_name.removesuffix(".ttf")] = pygame.font.Font(
        f"fonts\\{font_name}",
        font_size_requirements[font_name]
    )
current_font_name = "consolas-mono"
current_font: pygame.font.Font = fonts[current_font_name]
char_height = font_size_requirements[f"{current_font_name}.ttf"]

quit_flag = False
cursor = [0, 0]
saved_cursor_pos = [0, 0]
scroll_lock = False
_MOUSEWHEEL_events = []

background_color = (12, 12, 12, 255)
foreground_color = (200, 200, 200, 255)

screen.fill((12, 12, 12, 255))
pygame.display.flip()


# special print lol
def special_print(
    level: int,
    text: str
) -> None:
    print(text)
    logging.log(level, text)


def _isint(
    string: str
) -> bool:
    try: int(string); return True
    except ValueError: return False


def _calculate_x_offset(
    line_index: int
) -> int:
    """Like `calculate_y_offset()` but for the X offset."""
    global terminal_grid
    global fonts
    x_offset = 0
    buffer = ""
    prev_font = ""
    for char in terminal_grid[line_index]:
        if char.font == prev_font:
            buffer += char.letter
            continue
        elif not prev_font:
            prev_font = char.font
            continue
        use_font: pygame.font.Font = fonts[prev_font]
        x_offset += use_font.size(buffer)[0]
    
    return x_offset


def _calculate_y_offset(
    start: int = 0,
    end: int = None
) -> int:
    """Calculates the Y coordinate that the next line of text must be on.

    Args:
        line_index (int): The line index that you want the next line of text to be at.

    Returns:
        int: The Y offset.
    """
    global terminal_grid
    global font_size_requirements
    y_offset = 0
    for line in terminal_grid[start:end:]:
        line_height = 0
        for char in line:
            # doesn't hurt to do it for 50 chars instead of like 2
            if font_size_requirements[char.font] > line_height:
                line_height = char_height
        if line_height == 0: line_height = 12
        y_offset += line_height + 6 # in case there's, like, a y in there or something
    
    return y_offset


scroll_idx = 0

def _scrolling_thread() -> None:
    global terminal_grid
    global scroll_lock
    global scroll_idx
    global quit_flag
    global _MOUSEWHEEL_events
    while not quit_flag:
        sleep(1/30)
        if scroll_lock:
            scroll_idx = 0
            continue
        
        if len(_MOUSEWHEEL_events) <= 0:
            continue
        
        y_with_flipping_considered: int = 0
        indexes = []
        
        for event_index in range(len(_MOUSEWHEEL_events)):
            indexes.append(event_index)
            event = _MOUSEWHEEL_events[event_index]
            
            flipped = 1 - (2 * int(event.flipped))
            y_with_flipping_considered: int = flipped * event.y
            if y_with_flipping_considered == 1 and scroll_idx > 0:
                scroll_idx -= 1
            elif y_with_flipping_considered == -1 and scroll_idx < len(terminal_grid) - 30:
                scroll_idx += 1
        
        update_terminal()
        flush()
        
        try:
            for index in indexes:
                del _MOUSEWHEEL_events[index]
        except IndexError:
            continue
        
Thread(target=_scrolling_thread).start()


def quit_check() -> bool:
    """Do this on the main thread every once in a while so the window keeps working and so scrolling keeps happening."""
    global quit_flag
    global _MOUSEWHEEL_events
    for event in pygame.event.get((pygame.QUIT, pygame.MOUSEWHEEL)):
        if event.type == pygame.MOUSEWHEEL:
            _MOUSEWHEEL_events.append(event)
            continue
        quit_flag = True
        break
    return quit_flag


def printf(
    text: str,
    overwrite: bool = True,
    update: bool = True,
    flush_: bool=True
) -> None:
    """Attempts to print text to the screen. You may use ANSI codes.\n
    
    Overwrites the previous line with new text if overwrite is `True`. Example:\n
        line = "foobar"
        printf("bar") # when cursor_X = 0
        "barbar" # when overwrite = True
        "barfoobar" # when overwrite = False
    
    Calls `terminal_update()` on end if update is `True`.\n
    Also calls `flush()` on end if flush_ is `True`.
    
    Fun fact: if you put too much text on one line it will go out of bounds and be cut off, probably.

    Args:
        text (str): The text you wish to print.
    """
    
    global terminal_grid
    global cursor
    global background_color
    global foreground_color
    
    color_code = False
    using_color_code = 0
    color_code_buffer = ""
    for char in text:
        if color_code:
            color_code_buffer += char
            if (_isint(char) or char in (";", "[")) and using_color_code == 0:
                continue
            elif char != "!" and using_color_code == 1:
                continue
            color_code = False
            using_color_code = 0
            if not color_code_buffer.endswith("!") and not color_code_buffer.endswith("m"):
                new_color = _parse_ansi_command(color_code_buffer)
            else:
                new_color = _parse_ansi_color(color_code_buffer)
            
            if isinstance(new_color, int):
                special_print(logging.WARNING, f"WARNING: WHAT WENT WRONG?: {new_color}")
                special_print(logging.WARNING, f"OFFENDING CODE: {color_code_buffer.replace("\x1b", "\\x1b")}")
                color_code_buffer = ""
                continue
            elif new_color is None:
                color_code_buffer = ""
                continue
            
            color_code_buffer = ""
            
            if new_color[3] == 0:
                foreground_color = new_color[:3:] + tuple([foreground_color[3]])
            elif new_color[3] == 1:
                background_color = new_color[:3:] + tuple([background_color[3]])
            elif new_color[3] == 2:
                foreground_color = (200, 200, 200, 255)
                background_color = (12, 12, 12, 255)
                current_font.set_italic(False)
                current_font.set_underline(False)
                current_font.set_strikethrough(False)
        
        elif char == "\n":
            cursor[1] += 1
            try:
                terminal_grid[cursor[1]]
            except IndexError:
                terminal_grid.insert(cursor[1], [])
            length_of_new_line = len(terminal_grid[cursor[1]])
            
            if length_of_new_line > 1:
                cursor[0] = len(terminal_grid[cursor[1]]) - 1
            else:
                cursor[0] = 0
        
        elif char == "\r":
            cursor[0] = 0
        
        elif char == "\x1b":
            using_color_code = 0
            color_code = True
            color_code_buffer += char
        
        elif char == "\x1c":
            using_color_code = 1
            color_code = True
            color_code_buffer += char
        
        elif overwrite:
            char_ = letter(
                char,
                current_font_name,
                foreground_color,
                background_color,
                [current_font.get_italic(), current_font.get_underline(), current_font.get_strikethrough()]
            )
            try:
                terminal_grid[cursor[1]][cursor[0]] = char_
            except IndexError:
                terminal_grid[cursor[1]].append(char_)
            cursor[0] += 1
        
        elif not overwrite: # gotta b safe ykyk
            # no i dont "ykyk" what about this is extra safety?? it's common sense
            terminal_grid[cursor[1]].insert(cursor[0], letter(
                char,
                current_font_name,
                foreground_color,
                background_color,
                [current_font.get_italic(), current_font.get_underline(), current_font.get_strikethrough()]
            ))
            cursor[0] += 1
    
    
    if color_code and not _isint(color_code_buffer[-1]):
        if color_code_buffer[-1] in ("m", "!"):
            new_color = _parse_ansi_color(color_code_buffer)
        else:
            new_color = _parse_ansi_command(color_code_buffer)
        
        if isinstance(new_color, int):
            special_print(logging.WARNING, f"WARNING: WHAT WENT WRONG?: {new_color}")
            special_print(logging.WARNING, f"OFFENDING CODE: {color_code_buffer.replace("\x1b", "\\x1b").replace("\x1c", "\\x1c")}")
            color_code_buffer = ""
        elif new_color is None:
            color_code_buffer = ""
    
    
    if update:
        update_terminal()
    if flush_:
        flush()


def _calculate_8_bit_num(
    color_index: int
) -> tuple[int, int, int]:
    """Takes a color index 16-231 and turns it into an RGB value.

    Args:
        color_index (int): The color index.

    Returns:
        tuple[int, int, int]: The RGB value after conversion.
    """
    # the original formula was
    # color_index = 16 + 36r + 6g + b where all 3 channels (rgb) are 0-5 (6x6x6 cube color yknow? i dont.)
    color = color_index - 16 # gotta take care to not get ruined by mutation
    # color_index = 36r + 6g + b
    # the combined sum of 6g + b is never >= 36 so it can't fuck with r so it's preserved completely forever
    R = color // 35
    # now remove R from it just like this
    color = color % 36
    # now the b channel is never >= 6 so it can't fuck with g meaning it's preserved as well
    G = color // 6
    # now the rest is b right after we remove g from it
    B = color % 6
    return (R / 5 * 255, G / 5 * 255, B / 5 * 255) # the explanation is left as an exercise for the reader


def _parse_ansi_color(
    ansi_code: str
) -> tuple[int, int, int, int] | tuple[int] | int | None:
    """Takes an ANSI code and outputs a color value. Will work for ANSI font codes as well.

    Args:
        ansi_code (str): The color code, starts with \\x1b[ and ends with m or starts with \\x1c[ and ends with !.

    Returns:
        tuple[int, int, int, int]: The color value. The last value represents foreground, background or reset with 0, 1 and 2 respectively.
        tuple[int]: Alpha value.
        int: An error code.
        None: It was a font request.
    """
    global current_font
    code = ansi_code.removeprefix("\x1b[").removeprefix("\x1c[").removesuffix("m").removesuffix("!")
    checking_code = code.split(";")
    
    for part_index in range(len(checking_code)):
        if checking_code[0] == "4" and len(checking_code) == 2:
            break
        part = checking_code[part_index]
        if not _isint(part):
            return 0 # Not all arguments are ints
    
    colors_dict = {
        # just fyi
        "0": (200, 200, 200, 2), # 0 is the full reset
        "1": (255, 255, 255, 0), # 1 is bold
        "2": (170, 170, 170, 0), # 2 is italics
        
        
        "31": (200, 0, 0, 0),
        "35": (78, 164, 6, 0),
        "33": (196, 160, 0, 0),
        "34": (8, 48, 218, 0),
        "35": (117, 80, 123, 0),
        "36": (6, 152, 154, 0),
        "37": (211, 215, 207, 0),
        "39": (200, 200, 200, 0),
        
        "41": (200, 0, 0, 1),
        "42": (78, 164, 6, 1),
        "43": (196, 160, 0, 1),
        "44": (8, 48, 218, 1),
        "45": (117, 80, 123, 1),
        "46": (6, 152, 154, 1),
        "47": (211, 215, 207, 1),
        "49": (12, 12, 12, 1),
        
        "90": (85, 87, 83, 0),
        "91": (239, 41, 41, 0),
        "92": (138, 226, 52, 0),
        "93": (252, 233, 79, 0),
        "94": (114, 159, 207, 0),
        "95": (173, 127, 168, 0),
        "96": (52, 226, 226, 0),
        "97": (238, 238, 236, 0),
        
        "100": (85, 87, 83, 1),
        "101": (239, 41, 41, 1),
        "102": (138, 226, 52, 1),
        "103": (252, 233, 79, 1),
        "104": (114, 159, 207, 1),
        "105": (173, 127, 168, 1),
        "106": (52, 226, 226, 1),
        "107": (238, 238, 236, 1),
    }
    
    if len(code) <= 3:
        # "0"-"107"
        if code == "3":
            current_font.set_italic(True)
        elif code == "4":
            current_font.set_underline(True)
        elif code == "9":
            current_font.set_strikethrough(True)
        elif code == "23":
            current_font.set_italic(False)
        elif code == "24":
            current_font.set_underline(False)
        elif code == "29":
            current_font.set_strikethrough(False)
        else:
            try:
                return colors_dict[code]
            except KeyError:
                return 1 # Color not available
        return
    
    # if it's not one of the 16 colors it has to be
    # either something explicit like 38/48;2;255;0;0 or
    # one of the 8-bit colors like 38/48;5;1
    # regardless, both use semicolons to seperate terms
    # so we must split by semicolon now
    code = code.split(";")
    
    if code[0] == "4" and len(code) != 2:
        return 4
    elif code[0] not in ("38", "48", "4"):
        return 2 # Is it foreground or background??
    elif code[1] not in ("2", "3", "5") and code[0] != "4":
        return 3 # Do you want to use 24-bit color, set alpha or use 8-bit color?
    elif code[1] == "2" and len(code) != 5:
        return 4 # Wrong argument count
    elif code[1] == "3" and len(code) != 3:
        return 4
    elif code[1] == "5" and len(code) != 3:
        return 4
    
    foreground_or_background = int(code[0] == "48")
    
    if code[1] == "2":
        return (int(code[2]), int(code[3]), int(code[4]), foreground_or_background)
    elif code[1] == "3":
        return tuple([int(code[2])])
    elif code[0] == "4":
        switch_font(code[1])
        return
    elif code[1] == "5":
        return _calculate_8_bit_num(int(code[2]))


def _parse_ansi_command(
    ansi_code: str
) -> int | None:
    """Parses and executes ANSI commands, like for example `\\x1b[H`, `\\x1b[5A`, `\\x1b[1J` etc.
    Does nothing if command is invalid.

    Args:
        ansi_code (str): The code to be parsed.
    
    Returns:
        int: An error code.
    """
    global cursor
    global terminal_grid
    global saved_cursor_pos
    global scroll_idx
    
    if len(ansi_code) == 0:
        return 4 # wrong number of arguments
    
    saved = ansi_code[-1]
    code = ansi_code.removeprefix("\x1b[").split(ansi_code[-1])
    code[-1] = saved

    if len(code) > 2:
        return 4
    
    possible_codes = "ABCDEFGHJK" # strs are just char tuples in py
    if code[-1] not in possible_codes:
        return
    
    try:
        MAX_Y = len(terminal_grid) - 1
        MAX_X = len(terminal_grid[cursor[1]]) - 1
    except IndexError:
        logging.warning(f"INDEX ERROR AT LINE 538-9!!\ncursor: {cursor}\nlen(terminal_grid): {len(terminal_grid)}")
        return 5 # Error
    
    if code[0] == "":
        match code[1]:
            case "A":
                if cursor[1] <= 0: return
                cursor[1] -= 1
            case "B":
                if cursor[1] >= MAX_Y: return
                cursor[1] += 1
            case "C":
                if cursor[0] >= MAX_X: return
                cursor[0] += 1
            case "D":
                if cursor[0] <= 0: return
                cursor[0] -= 1
            case "E":
                cursor[1] += 1
                cursor[0] = 0
            case "F":
                cursor[1] -= 1
                cursor[0] = 0
            case "H": cursor = [0, 0]
            
            case "J":
                for char_index in range(len(terminal_grid[cursor[1]][cursor[0] + 1::])):
                    del terminal_grid[cursor[1]][cursor[0] + 1]
                
                for line_index in range(len(terminal_grid[cursor[1] + 1::])):
                    del terminal_grid[cursor[1] + 1]
            
            case "K":
                for char_index in range(len(terminal_grid[cursor[1][cursor[0] + 1::]])):
                    del terminal_grid[cursor[1]][cursor[0] + 1]
            
            case "s": saved_cursor_pos = cursor
            case "u": cursor = saved_cursor_pos
        
        return
    
    num = "".join(code[:-1:])
    try:
        num = int(num)
    except ValueError:
        if code[1] != "H":
            return
    
    match code[-1]:
        case "A":
            if cursor[1] - num <= 0: cursor[1] = 0
            else: cursor[1] -= num
        case "B":
            if cursor[1] + num >= MAX_Y: cursor[1]
            else: cursor[1] += num
        case "C":
            if cursor[0] + num < MAX_X: cursor[0] += num
            else: cursor[0] = MAX_X
        case "D":
            if cursor[0] - num >= 0: cursor[0] -= num
            else: cursor[0] = 0
        case "E":
            if cursor[1] + num >= MAX_Y: cursor[1] = MAX_Y
            else: cursor[1] += num
            cursor[0] = 0
        case "F":
            if cursor[1] - num <= 0: cursor[1] = 0
            else: cursor[1] -= num
            cursor[0] = 0
        case "G": cursor[0] = num
        case "H":
            further_split = num.split(";")
            cursor[0], cursor[1] = int(further_split[0]), int(further_split[1])
        case "J":
            if num == 0:
                for char_index in range(len(terminal_grid[cursor[1]][cursor[0] + 1::])):
                    del terminal_grid[cursor[1]][cursor[0] + 1]
                
                for line_index in range(len(terminal_grid[cursor[1] + 1::])):
                    del terminal_grid[cursor[1] + 1]
            
            elif num == 1:
                for char_index in range(len(terminal_grid[cursor[1]][:cursor[0]:])):
                    char = terminal_grid[cursor[1]][char_index]
                    terminal_grid[cursor[1]][char_index] = letter(
                        " ",
                        char.font,
                        (200, 200, 200),
                        (12, 12, 12),
                        [current_font.get_italic(), current_font.get_underline(), current_font.get_strikethrough()]
                    )
                
                for char_index in range(len(terminal_grid[:cursor[1]:])):
                    del terminal_grid[char_index]
                cursor[0] = 0
            
            elif num == 2:
                terminal_grid = [[]]
                cursor = [0, 0]
                scroll_idx = 0
        
        case "K":
            if num == 0:
                for char_index in range(len(terminal_grid[cursor[1][cursor[0] + 1::]])):
                    del terminal_grid[cursor[1]][cursor[0] + 1]
            
            elif num == 1:
                for char_index in range(len(terminal_grid[cursor[1]][:cursor[0]:])):
                    char = terminal_grid[cursor[1]][char_index]
                    terminal_grid[cursor[1]][char_index] = letter(
                        " ",
                        "consolas-mono",
                        (200, 200, 200),
                        (12, 12, 12),
                        [current_font.get_italic(), current_font.get_underline(), current_font.get_strikethrough()]
                    )
                cursor[0] = 0
            
            elif num == 2:
                terminal_grid[cursor[1]] = []
                cursor[0] = 0
    
    update_terminal()
    flush()


def update_terminal(
    line_index: int | None = None
) -> int:
    """Updates the terminal. Effects don't appear until `flush()` is called.

    Args:
        line_index (int | None, optional): Line number to update. If None, updates the whole screen. Defaults to None.
        text_y (int)
    
    Returns:
        int: The Y coordinate on-screen of the next piece of text.
    """
    global terminal_grid
    global scroll_idx
    global fonts
    global screen
    global char_height
    render_grid = terminal_grid[scroll_idx::]
    
    if line_index is not None:
        try:
            line = render_grid[line_index]
        except IndexError:
            return
        prev_attr = None
        buffer = ""
        counting_width = 0
        text_y = _calculate_y_offset(end=line_index)
        max_height = _calculate_y_offset(start=line_index, end=line_index + 1)
        pygame.draw.rect(
            screen,
            (12, 12, 12),
            (0, text_y, 1024, max_height + 6)
        )
        
        for char in line:
            if char.extract_attributes() == prev_attr:
                buffer += char.letter
                continue
            
            elif prev_attr == None:
                prev_attr = char.extract_attributes()
                buffer += char.letter
                continue
            
            
            font: pygame.font.Font = fonts[prev_attr[0]]
            font_options = prev_attr[3]
            font.set_italic(font_options[0])
            font.set_underline(font_options[1])
            font.set_strikethrough(font_options[2])
            rendered_text: pygame.Surface = font.render(
                buffer,
                False,
                prev_attr[1],
                prev_attr[2]
            )
            screen.blit(
                source=rendered_text,
                dest=(counting_width, text_y)
            )
            counting_width += font.size(buffer)[0]
            prev_attr = char.extract_attributes()
            buffer = char.letter
        
        if not buffer: # Hey what the fuck how does this cooperate with the rest of the program??
            return
        
        font: pygame.font.Font = fonts[prev_attr[0]]
        font_options = prev_attr[3]
        font.set_italic(font_options[0])
        font.set_underline(font_options[1])
        font.set_strikethrough(font_options[2])
        rendered_text: pygame.Surface = font.render(
            buffer,
            False,
            prev_attr[1],
            prev_attr[2]
        )
        
        screen.blit(
            source=rendered_text,
            dest=(counting_width, text_y)
        )
        counting_width += font.size(buffer)[0]
    else:
        screen.fill((12, 12, 12))
        for line_index in range(len(render_grid[:35:])):
            update_terminal(line_index) # yeah. DRY for the win?


def switch_font(
    new_font_name: str
) -> None:
    """Switches the font being used.
    Also recalibrates the list of fonts available in case fonts were added to or removed from the fonts folder.
    Does nothing if the font requested doesn't exist in the fonts folder.

    Args:
        font_name (str): The name of the font you want to switch to.
    """
    global fonts
    global current_font_name
    global current_font
    global char_height
    fonts = {}
    for font_name in listdir("fonts"):
        if not font_name.endswith(".ttf"):
            continue
        fonts[font_name.removesuffix(".ttf")] = pygame.font.Font(
            f"fonts\\{font_name}",
            font_size_requirements[font_name]
        )
    try:
        current_font = fonts[new_font_name]
        current_font_name = new_font_name
        char_height = font_size_requirements[f"{current_font_name}.ttf"]
    except KeyError:
        return


def input(
    text: str = "",
    default_text: str = "",
    end_text: str = ""
) -> str | None:
    """Takes input from the user.
    No, it doesn't print a newline on end like regular `input()`.
    Yes, it does pause the thread like regular `input()`, but rest assured the window will not stop responding.
    By the way, it only uses `terminal.update()` on the line the cursor is on unless the user scrolls.

    Args:
        text (str, optional): The text that should be there, like "Num of birthdays >".
        default_text (str, optional): The text that should be there that the user can edit, like "1".
        end_text (str, optional): The text that should be printed after the user presses Enter.

    Returns:
        str: The text the user has inputted.
        None: The program's closin'!
    """
    global cursor
    global terminal_grid
    global quit_flag
    global _MOUSEWHEEL_events
    printf(text)
    printf(default_text)
    compiled_cursor = cursor[1] - scroll_idx
    if compiled_cursor < 35 and compiled_cursor >= 0:
        update_terminal(compiled_cursor)
    flush()
    text_input = list(default_text)
    insert_pos = len(text_input)
    exit_flag = False
    while not exit_flag:
        compiled_cursor = cursor[1] - scroll_idx
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_flag = True
                return
            elif event.type == pygame.MOUSEWHEEL:
                _MOUSEWHEEL_events.append(event)
                continue
            elif event.type != pygame.KEYDOWN:
                continue
            
            if event.key == pygame.K_RETURN:
                exit_flag = True
                break
            elif event.key == pygame.K_LEFT and insert_pos > 0:
                insert_pos -= 1
                cursor[0] -= 1
                continue
            elif event.key == pygame.K_RIGHT and insert_pos < len(text_input):
                insert_pos += 1
                cursor[0] += 1
                continue
            elif event.key == pygame.K_BACKSPACE:
                if insert_pos <= 0: continue
                
                insert_pos -= 1
                cursor[0] -= 1
                text_input.pop(insert_pos)
                try:
                    terminal_grid[cursor[1]].pop(cursor[0])
                except IndexError as e:
                    special_print(logging.WARNING, f"ERR CAUGHT: {e}")
                    special_print(logging.WARNING, f"cursor: {cursor}")
                
                compiled_cursor = cursor[1] - scroll_idx
                if compiled_cursor > 35 or compiled_cursor < 0:
                    continue
                update_terminal(compiled_cursor)
                flush()
                continue
            
            key = event.unicode
            if key == "": continue
            text_input.insert(insert_pos, key)
            insert_pos += 1
            printf(key)
            compiled_cursor = cursor[1] - scroll_idx
            if compiled_cursor > 35 or compiled_cursor < 0:
                continue
            update_terminal(compiled_cursor)
            flush()
    printf(end_text)
    return "".join(text_input)


def flush() -> None:
    """Updates the terminal window."""
    pygame.display.flip()

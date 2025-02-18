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


class letter:
    def __init__(
        self,
        letter: str,
        font: str,
        fg_color: list[int, int, int, int],
        bg_color: list[int, int, int, int]
    ):
        self.letter = letter
        self.font = font
        self.fg_color = fg_color
        self.bg_color = bg_color
    
    def extract_attributes(
        self
    ) -> tuple[str, list[int, int, int, int], list[int, int, int, int]]:
        """Get everything except the char in a tuple."""
        return (
            self.font,
            self.fg_color,
            self.bg_color
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
updating_screen = False
cursor = [0, 0]
saved_cursor_pos = [0, 0]
scroll_lock = False

background_color = (12, 12, 12, 255)
foreground_color = (200, 200, 200, 255)

screen.fill((12, 12, 12, 255))
pygame.display.flip()


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
end_render = len(terminal_grid) # meh just put it above the terminal char height

def _scrolling_thread() -> None:
    global terminal_grid
    global scroll_lock
    global scroll_idx
    global quit_flag
    while not quit_flag:
        sleep(1/30)
        end_render = len(terminal_grid)
        if scroll_lock:
            scroll_idx = 0
            continue
        
        for event in pygame.event.get((pygame.MOUSEWHEEL)):
            flipped = 1 - (2 * int(event.flipped))
            y_with_flipping_considered = flipped * event.y
            if y_with_flipping_considered == 1 and scroll_idx > 0:
                scroll_idx -= 1
            elif y_with_flipping_considered == -1 and scroll_idx < end_render - 30:
                scroll_idx += 1
Thread(target=_scrolling_thread).start()


def quit_check() -> bool:
    """Do this on the main thread every once in a while so the window keeps working."""
    global quit_flag
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
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
    newlines = 0
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
                _parse_ansi_command(color_code_buffer)
                color_code_buffer = ""
                continue
            
            new_color = _parse_ansi_color(color_code_buffer)
            
            if isinstance(new_color, int):
                print(f"WARNING: WHAT WENT WRONG?: {new_color}")
                print(f"OFFENDING CODE: {color_code_buffer}")
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
            continue
        
        if char == "\n":
            cursor[1] += 1
            newlines += 1
            try:
                terminal_grid[cursor[1]]
            except IndexError:
                terminal_grid.insert(cursor[1], [])
        
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
                background_color
            )
            try:
                terminal_grid[cursor[1]][cursor[0]] = char_
            except IndexError:
                terminal_grid[cursor[1]].append(char_)
            cursor[0] += 1
        
        elif not overwrite: # gotta be safe ykyk
            terminal_grid[cursor[1]].insert(cursor[0], letter(
                char,
                current_font_name,
                foreground_color,
                background_color
            ))
            cursor[0] += 1
    
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
        "32": (78, 164, 6, 0),
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
        
        
        "91": (239, 41, 41, 0),
        "92": (138, 226, 52, 0),
        "93": (252, 233, 79, 0),
        "94": (114, 159, 207, 0),
        "95": (173, 127, 168, 0),
        "96": (52, 226, 226, 0),
        "97": (238, 238, 236, 0),
        
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
        if code == "2":
            # it's italics lol
            current_font.set_italic(True)
        try:
            return colors_dict[code]
        except KeyError:
            return 1 # Color not available
    
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
    
    if len(ansi_code) == 0:
        return 4 # wrong number of arguments
    
    saved = ansi_code[-1]
    code = ansi_code.removeprefix("\x1b[").split(ansi_code[-1])
    code[-1] = saved

    if len(code) > 2:
        return 4
    
    if code[0] == "":
        if code[1] == "H":
            cursor = [0, 0]
        
        elif code[1] == "J":
            for char_index in range(len(terminal_grid[cursor[1]][cursor[0] + 1::])):
                del terminal_grid[cursor[1]][cursor[0] + 1]
            
            for line_index in range(len(terminal_grid[cursor[1] + 1::])):
                del terminal_grid[cursor[1] + 1]
            
        elif code[1] == "K":
            for char_index in range(len(terminal_grid[cursor[1][cursor[0] + 1::]])):
                del terminal_grid[cursor[1]][cursor[0] + 1]
        
        if code[1] == "s":
            saved_cursor_pos = cursor
        elif code[1] == "u":
            cursor = saved_cursor_pos
        
        return
    
    num = "".join(code[:-1:])
    try:
        num = int(num)
    except ValueError:
        if code[1] != "H":
            return
    
    match code[-1]:
        case "A": cursor[1] -= num
        case "B": cursor[1] += num
        case "C":
            if cursor[0] + num < len(terminal_grid[cursor[1]]): cursor[0] += num
            else: cursor[0] = len(terminal_grid[cursor[1]]) - 1
        case "D":
            if cursor[0] - num >= 0: cursor[0] -= num
            else: cursor[0] = 0
        case "E":
            cursor[1] += num
            cursor[0] = 0
        case "F":
            cursor[1] -= num
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
                        (12, 12, 12)
                    )
                
                for char_index in range(len(terminal_grid[:cursor[1]:])):
                    del terminal_grid[char_index]
                cursor[0] = 0
            
            elif num == 2:
                terminal_grid = [[]]
                cursor = [0, 0]
        
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
                        (12, 12, 12)
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
    global fonts
    global screen
    global char_height
    global updating_screen
    updating_screen = True
    
    if line_index is not None:
        line = terminal_grid[line_index]
        prev_attr = ("", [0, 0, 0, 0], [0, 0, 0, 0])
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
            
            elif prev_attr == ("", [0, 0, 0, 0], [0, 0, 0, 0]):
                prev_attr = char.extract_attributes()
                buffer += char.letter
            
            else:
                font: pygame.font.Font = fonts[prev_attr[0]]
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
        
        if not buffer:
            return
        font: pygame.font.Font = fonts[prev_attr[0]]
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
        for line_index in range(len(terminal_grid)):
            update_terminal(line_index) # yeah.
    
    updating_screen = False


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
    end_text: str = "\n"
) -> str | None:
    """Takes input from the user.
    No, it doesn't print a newline on end like regular `input()`.
    Yes, it does pause the thread like regular `input()`, but rest assured the window will not stop responding.
    By the way, it only uses `terminal.update()` on the line the cursor is on.

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
    printf(text)
    if default_text:
        printf(default_text)
    update_terminal(cursor[1])
    flush()
    text_input = list(default_text)
    insert_pos = len(text_input)
    exit_flag = False
    while not exit_flag:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_flag = True
                return
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
                terminal_grid[cursor[1]].pop(cursor[0])
                update_terminal(cursor[1])
                flush()
                continue
            
            key = event.unicode
            if key == "": continue
            text_input.insert(insert_pos, key)
            insert_pos += 1
            printf(key)
            update_terminal(cursor[1])
            flush()
    return "".join(text_input)


def flush() -> None:
    """Updates the terminal window."""
    pygame.display.flip()

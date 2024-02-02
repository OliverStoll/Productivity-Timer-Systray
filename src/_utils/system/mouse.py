import pyautogui


def toggle_desktop_drawer():
    """ Clicks on the desktop to hide any open windows, and moves the mouse back to its original position. """
    current_mouse_x, current_mouse_y = pyautogui.position()
    pyautogui.click(x=1913, y=1055)
    pyautogui.moveTo(current_mouse_x, current_mouse_y)


def check_if_any_windows_open(default_color=(5, 3, 7)):
    """ Checks if any windows are open by checking the color of the pixel at the bottom right corner of the screen. """
    # print color of pixel at bottom right corner of screen
    pixel_color = pyautogui.pixel(x=500, y=500)
    return pixel_color != default_color


if __name__ == '__main__':
    # toggle_desktop_drawer()
    print(check_if_any_windows_open())
import time

from src._utils.system.programs_windows import is_program_running, start_program


def keep_alive(program_path: str, interval: int):
    program_name = program_path.split("\\")[-1]

    while True:
        if not is_program_running(program_name):
            print("Program is not running, starting it now...")
            start_program(program_path)
        else:
            print("Program is already running.")
        time.sleep(interval)


if __name__ == "__main__":
    path = r"C:\CODE\pomodoro-windows\dist\Pomo.exe"
    interval = 5
    keep_alive(program_path=path, interval=interval)

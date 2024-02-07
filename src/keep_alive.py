import subprocess
import time
import os


def is_program_running(program_name):
    """Check if the program is currently running."""
    try:
        processes = subprocess.check_output(["tasklist"], text=True)
        return program_name in processes
    except subprocess.CalledProcessError:
        return False


def start_program(program_path):
    """Starts the program."""
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        subprocess.Popen(program_path, startupinfo=startupinfo)
        print(f"Program started: {program_path}")
    except Exception as e:
        print(f"Failed to start the program: {e}")


def keep_program_alive(path, frequency):
    program_name = os.path.basename(path)

    while True:
        if not is_program_running(program_name):
            print("Program is not running, starting it now...")
            start_program(path)
        else:
            print("Program is already running.")
        time.sleep(frequency)


if __name__ == "__main__":
    path = r"C:\CODE\pomodoro-windows\dist\Pomo.exe"
    frequency = 60
    keep_program_alive(path=path, frequency=frequency)

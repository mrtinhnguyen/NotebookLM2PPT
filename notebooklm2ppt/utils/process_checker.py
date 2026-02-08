import subprocess
import sys


PROCESS_NAME = "MSPCManager.exe"


def is_process_running(name: str) -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {name}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    return name.lower() in result.stdout.lower()


def main() -> None:
    running = is_process_running(PROCESS_NAME)
    if running:
        print(f"{PROCESS_NAME} đang chạy")
        sys.exit(0)
    else:
        print(f"{PROCESS_NAME} không chạy")
        sys.exit(1)


if __name__ == "__main__":
    main()


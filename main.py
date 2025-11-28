import tkinter as tk
from windsurf_account_manager.ui_main import App


def main() -> None:
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

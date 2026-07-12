# main.py

import tkinter as tk
from app_logic import AncestryApp

if __name__ == "__main__":
    root = tk.Tk()
    app = AncestryApp(root)
    root.mainloop()

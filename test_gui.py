import tkinter as tk
from tkinter import messagebox

def test_gui():
    root = tk.Tk()
    root.title("Test GUI")
    root.geometry("300x200")
    
    def on_click():
        messagebox.showinfo("Test", "GUI is working!")
    
    button = tk.Button(root, text="Click me", command=on_click)
    button.pack(pady=50)
    
    root.mainloop()

if __name__ == "__main__":
    test_gui()
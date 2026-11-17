import tkinter as tk
root = tk.Tk()
root.geometry("1366x993")
bg = tk.PhotoImage(file = "1.svg")
label1 = tk.Label(root, image = bg)
label1.place(x = 0, y = 0)
root.mainloop()

root.title("BBC Sounds")

button = tk.Button(root, text="Stop", width=25, command=root.destroy)
button.pack()

root.mainloop()
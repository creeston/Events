import tkinter as tk

root = tk.Tk()
root.geometry("600x500")

root.wm_title("Function drawer")
textVar = tk.StringVar()
textArea = tk.Label(root, textvariable=textVar, anchor=tk.W, justify=tk.CENTER, wraplength=500)
textArea.pack()


processed = 0
lines = list(set(open('data/raw', encoding="utf-8").readlines()))
events = []
not_events = []
lines_iter = iter(lines)
line = next(lines_iter)
textVar.set(line)


def add_event():
    global line
    global processed
    events.append(line)
    line = next(lines_iter)
    processed += 1
    textVar.set(line)


def add_not_event():
    global line
    global processed
    not_events.append(line)
    line = next(lines_iter)
    processed += 1
    textVar.set(line)


def on_closing():
    open('data/raw', 'w', encoding="utf-8").writelines(lines[processed:])
    open("events", "a", encoding="utf-8").writelines(events)
    open("data/not_events", "a", encoding="utf-8").writelines(not_events)
    root.destroy()


event_button = tk.Button(root, text="event", command=add_event, fg='green')
event_button.place(x=330, y=450)
not_event_button = tk.Button(root, text="not event", command=add_not_event, fg='red')
not_event_button.place(x=230, y=450)
root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()
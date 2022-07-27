import tkinter as tk
from tkinter import Frame, Text, OptionMenu, StringVar, Button


class Interface(tk.Tk):
    def __init__(self):
        super().__init__()

        self.engines = ['MOTOR 1', 'MOTOR 2', 'MOTOR 3', 'MOTOR 4', 'MOTOR 5', 'MOTOR 6', 'MOTOR 7']
        self.selected_engine = self.engines[0]

        # INTERFACE --->
        self.wm_title('IHM DESLIZANTE')

        self.console_Frame = Frame(self)
        self.console_Frame.grid(row=0, column=0, sticky='nsew', pady=2)

        self.console_Text = Text(self.console_Frame, font=('Times New Roman', 17))

        self.console_Text.tag_configure('center', justify='center', font=('Times New Roman', 20, 'bold'))
        self.console_Text.insert('1.0', 'Interface de controle de teste de motores\n\n')
        self.console_Text.tag_add('center', '1.0', '1.45')
        self.console_Text.configure(state='disabled')
        self.console_Text.pack(expand=True, fill='both')

        self.options_StringVar = StringVar()
        self.options_StringVar.set(self.selected_engine)

        self.options_OptionMenu = OptionMenu(self, self.options_StringVar, *self.engines, command=self.select_engine)
        self.options_OptionMenu.grid(row=1, column=0, sticky='nsw', ipady=20, columnspan=3)

        self.start_Button = Button(self, text='INICIAR')
        self.start_Button.grid(row=1, column=1)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.bind('<F11>', self.toggle_fullscreen)

    def toggle_fullscreen(self, e: tk.Event) -> None:
        if self.attributes('-fullscreen') == 0:
            self.attributes('-fullscreen', True)
        else:
            self.attributes('-fullscreen', False)

    def select_engine(self, e: tk.Event):
        engine = self.options_StringVar.get()
        self.selected_engine = engine
        self.console_insertion(f'{engine} selecionado para teste...\n\n')

    def console_insertion(self, action: str):
        self.console_Text.configure(state='normal')
        self.console_Text.insert('end', action)
        self.console_Text.see('end')
        self.console_Text.configure(state='disabled')


if __name__ == "__main__":
    ui = Interface()
    ui.mainloop()

# import tkinter as tk
# from tkinter.font import Font
#
# class Pad(tk.Frame):
#
#     def __init__(self, parent, *args, **kwargs):
#         tk.Frame.__init__(self, parent, *args, **kwargs)
#
#         self.toolbar = tk.Frame(self, bg="#eee")
#         self.toolbar.pack(side="top", fill="x")
#
#         self.bold_btn = tk.Button(self.toolbar, text="Bold", command=self.make_bold)
#         self.bold_btn.pack(side="left")
#
#         self.clear_btn = tk.Button(self.toolbar, text="Clear", command=self.clear)
#         self.clear_btn.pack(side="left")
#
#         # Creates a bold font
#         self.bold_font = Font(family="Helvetica", size=14, weight="bold")
#
#         self.text = tk.Text(self)
#         self.text.insert("end", "Select part of text and then click 'Bold'...")
#         self.text.focus()
#         self.text.pack(fill="both", expand=True)
#
#         # configuring a tag called BOLD
#         self.text.tag_configure("BOLD", font=self.bold_font)
#
#     def make_bold(self):
#         # tk.TclError exception is raised if not text is selected
#         try:
#             self.text.tag_add("BOLD", "sel.first", "sel.last")
#         except tk.TclError:
#             pass
#
#     def clear(self):
#         self.text.tag_remove("BOLD",  "1.0", 'end')
#
#
# def demo():
#     root = tk.Tk()
#     Pad(root).pack(expand=1, fill="both")
#     root.mainloop()
#
#
# if __name__ == "__main__":
#     demo()

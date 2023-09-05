import tkinter
import tkinter.messagebox
import customtkinter

customtkinter.set_appearance_mode(
    "System"
)  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme(
    "blue"
)  # Themes: "blue" (standard), "green", "dark-blue"


def center(toplevel):
    toplevel.update_idletasks()

    # Tkinter way to find the screen resolution
    screen_width = toplevel.winfo_screenwidth()
    screen_height = toplevel.winfo_screenheight()

    # # PyQt way to find the screen resolution
    # app = QtWidgets.QApplication([])
    # screen_width = app.desktop().screenGeometry().width()
    # screen_height = app.desktop().screenGeometry().height()

    size = tuple(int(_) for _ in toplevel.geometry().split("+")[0].split("x"))
    x = screen_width / 2 - size[0] / 2
    y = screen_height / 2 - size[1] / 2

    toplevel.geometry("+%d+%d" % (x, y))


def check_decimals(value: str):
    try:
        int_value = int(value)
        if (int_value >= 0) and (int_value < 32):
            return int_value
    except Exception as e:
        print("Invalid asset decimals value")

    return None


class RegisterAssetDialogue(customtkinter.CTk):
    def __init__(self, asset_ticker=None):
        super().__init__()

        # configure window
        self.title("Register Asset")
        self.geometry(f"{540}x{340}")

        self.frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.frame.grid(row=0, column=0, sticky="nsew")

        # Name
        self.name_label = customtkinter.CTkLabel(
            self.frame,
            text="Name",
            font=customtkinter.CTkFont(size=14),
        )
        self.name_label.grid(row=0, column=0, padx=(20, 20), pady=(20, 20))

        self.name = customtkinter.CTkEntry(self.name_label, placeholder_text="Name")
        self.name.grid(row=1, column=0, padx=(20, 20), pady=(20, 20), sticky="nsew")

        # Ticker
        self.ticker_label = customtkinter.CTkLabel(
            self.frame,
            text="Ticker",
            font=customtkinter.CTkFont(size=14),
        )
        self.ticker_label.grid(row=1, column=0, padx=(20, 20), pady=(20, 20))

        if asset_ticker is None:
            self.ticker = customtkinter.CTkEntry(
                self.ticker_label, placeholder_text="Ticker"
            )
        else:
            ticker = customtkinter.StringVar()
            ticker.set(asset_ticker)
            self.ticker = customtkinter.CTkEntry(self.ticker_label, textvariable=ticker)
        self.ticker.grid(row=1, column=0, padx=(20, 20), pady=(20, 20), sticky="nsew")

        # Fungible
        self.radio_var = tkinter.IntVar(value=0)
        self.fungible_label = customtkinter.CTkLabel(
            self.frame,
            text="Fungible",
            font=customtkinter.CTkFont(size=14),
        )
        self.fungible_label.grid(
            row=0, column=1, columnspan=1, padx=(20, 20), pady=(20, 20), sticky=""
        )
        self.radio_button_fungible = customtkinter.CTkRadioButton(
            master=self.fungible_label,
            text="Fungible",
            variable=self.radio_var,
            value=0,
        )
        self.radio_button_fungible.grid(row=1, column=2, pady=10, padx=20, sticky="n")
        self.radio_button_nft = customtkinter.CTkRadioButton(
            master=self.fungible_label, text="NFT", variable=self.radio_var, value=1
        )
        self.radio_button_nft.grid(row=2, column=2, pady=10, padx=20, sticky="n")

        # Decimals
        self.decimals_label = customtkinter.CTkLabel(
            self.frame,
            text="Decimals",
            font=customtkinter.CTkFont(size=14),
        )
        self.decimals_label.grid(row=1, column=1, padx=(20, 20), pady=(20, 20))
        self.decimals = customtkinter.CTkEntry(
            self.decimals_label, placeholder_text="Decimals"
        )
        self.decimals.grid(row=1, column=0, padx=(20, 20), pady=(20, 20), sticky="nsew")

        # Register Button
        self.register_subframe = customtkinter.CTkFrame(
            self.frame, width=140, corner_radius=0
        )
        self.register_subframe.grid(row=5, column=0, columnspan=2, sticky="nsew")

        self.register_button = customtkinter.CTkButton(
            master=self.register_subframe,
            text="Register Asset",
            command=self.register_event,
        )
        self.register_button.grid(row=2, column=0, padx=200, pady=(10, 10))

    def open_resubmit_event(self):
        # dialog = customtkinter.CTkButton(
        #     text="Please input valid data", title="Invalid Asset Values"
        # )
        tkinter.messagebox.showwarning(
            title="Invalid Asset Values", message="Please input valid data."
        )

    def register_event(self):
        name = self.name.get()
        ticker = self.ticker.get()
        fungible = True if self.radio_var.get() == 0 else False

        if fungible:
            decimals = check_decimals(self.decimals.get())
        else:
            decimals = 0

        if (decimals is None) or (len(ticker) == 0) or (len(name) == 0):
            self.open_resubmit_event()
        else:
            self.asset = {
                "name": name,
                "ticker": ticker,
                "fungible": fungible,
                "decimals": decimals,
            }
            print(f"Registering Asset:\n{name=}\n{ticker=}\n{fungible=}\n{decimals=}")
            self.destroy()

    def get_asset_details(self):
        return self.asset


def register_asset_dialogue() -> dict:
    app = RegisterAssetDialogue()
    center(app)
    app.mainloop()
    return app.get_asset_details()

"""Short-lived notification shown at the bottom of the window."""

from enum import Enum

import customtkinter as ctk

from financeflow.ui import theme

_DISPLAY_DURATION_MS = 3000


class ToastKind(Enum):
    SUCCESS = "success"
    ERROR = "error"


_BACKGROUND_BY_KIND = {
    ToastKind.SUCCESS: theme.SUCCESS_SURFACE,
    ToastKind.ERROR: theme.ERROR_SURFACE,
}


class Toast(ctk.CTkFrame):
    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(master, corner_radius=10)
        self._message_label = ctk.CTkLabel(
            self, text="", font=theme.font(14), text_color=theme.ON_COLOR, wraplength=420
        )
        self._message_label.pack(padx=18, pady=10)
        self._hide_job: str | None = None

    def show(self, message: str, kind: ToastKind = ToastKind.SUCCESS) -> None:
        self.configure(fg_color=_BACKGROUND_BY_KIND[kind])
        self._message_label.configure(text=message)
        self.place(relx=0.5, rely=1.0, anchor="s", y=-24)
        self.lift()

        if self._hide_job is not None:
            self.after_cancel(self._hide_job)
        self._hide_job = self.after(_DISPLAY_DURATION_MS, self._hide)

    def _hide(self) -> None:
        self._hide_job = None
        self.place_forget()

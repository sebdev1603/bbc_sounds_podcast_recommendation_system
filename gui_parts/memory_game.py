"""Hidden BBC Sounds Card Match easter-egg mini-game triggered from the BBC logo."""
import random
import tkinter as tk

from gui_parts import theme as _theme


def open_memory_game(parent):
    """Open (or focus) the BBC Sounds themed Card Match easter-egg window."""
    win, wrapper, status_lbl = _theme.create_minigame_shell(
        parent, "_memory_window", "BBC Sounds · Card Match",
        "BBC SOUNDS CARD MATCH", "Moves: 0   ·   Matches: 0/8",
    )
    if wrapper is None:
        return win

    grid_frame = tk.Frame(wrapper, bg=_theme.DARK_BG)
    grid_frame.pack()

    footer = tk.Frame(wrapper, bg=_theme.DARK_BG)
    footer.pack(fill="x", pady=(12, 0))
    win_banner = tk.Label(
        footer, text="Match all 8 BBC Sounds genre pairs!  ·  Esc to close",
        font=(_theme.DEFAULT_FONT, 9), fg=_theme.TEXT_GRAY, bg=_theme.DARK_BG,
    )
    win_banner.pack(side="left")

    # 8 distinct BBC Sounds genre pairs (16 cards in a 4x4 grid).
    pair_genres = ["News", "Travel", "History", "Comedy", "True Crime", "Technology", "Science", "Sport"]

    state = {
        "cards": [],
        "buttons": [],
        "flipped": [],
        "matched": set(),
        "moves": 0,
        "best": getattr(parent, "_memory_best_moves", None),
        "locked": False,
        "flip_job": None,
    }

    def cancel_flip_job():
        if state["flip_job"] is not None:
            try:
                win.after_cancel(state["flip_job"])
            except tk.TclError:
                pass
            state["flip_job"] = None

    def update_status():
        best_part = f"   ·   Best: {state['best']}" if state["best"] is not None else ""
        status_lbl.configure(
            text=f"Moves: {state['moves']}   ·   Matches: {len(state['matched']) // 2}/8{best_part}"
        )

    def paint_card(idx):
        btn = state["buttons"][idx]
        if not btn.winfo_exists():
            return
        if idx in state["matched"] or idx in state["flipped"]:
            genre_name = state["cards"][idx]
            tile_col, glyph, _desc = _theme.GENRE_TILE_DETAILS.get(genre_name, ("#3a1675", "♪", ""))
            top_col, _bot_col, acc_col = _theme.GENRE_GRADIENTS.get(genre_name, (tile_col, tile_col, _theme.ORANGE_HL))
            is_matched = idx in state["matched"]
            btn.configure(
                text=f"{glyph}\n{genre_name}",
                bg=top_col,
                activebackground=top_col,
                fg="#ffffff",
                activeforeground="#ffffff",
                highlightbackground=_theme.GOLD_STAR if is_matched else acc_col,
                highlightthickness=2,
            )
        else:
            btn.configure(
                text="BBC\n?",
                bg=_theme.CARD_BG,
                activebackground=_theme.SUBCARD_BG,
                fg=_theme.ORANGE_HL,
                activeforeground=_theme.ORANGE_ACCENT,
                highlightbackground=_theme.BORDER_LINE,
                highlightthickness=1,
            )

    def on_card_click(idx):
        if state["locked"] or idx in state["matched"] or idx in state["flipped"]:
            return
        state["flipped"].append(idx)
        paint_card(idx)

        if len(state["flipped"]) < 2:
            return

        state["moves"] += 1
        first, second = state["flipped"]
        if state["cards"][first] == state["cards"][second]:
            state["matched"].add(first)
            state["matched"].add(second)
            state["flipped"].clear()
            paint_card(first)
            paint_card(second)
            if len(state["matched"]) == len(state["cards"]):
                if state["best"] is None or state["moves"] < state["best"]:
                    state["best"] = state["moves"]
                    parent._memory_best_moves = state["best"]
                win_banner.configure(
                    text=f"All 8 pairs matched in {state['moves']} moves!",
                    fg=_theme.ORANGE_ACCENT,
                    font=(_theme.DEFAULT_FONT, 10, "bold"),
                )
            update_status()
        else:
            update_status()
            state["locked"] = True

            def hide_mismatch():
                state["flip_job"] = None
                if not win.winfo_exists():
                    return
                state["flipped"].clear()
                paint_card(first)
                paint_card(second)
                state["locked"] = False

            state["flip_job"] = win.after(650, hide_mismatch)

    def start_game():
        cancel_flip_job()
        for child in grid_frame.winfo_children():
            child.destroy()
        deck = pair_genres * 2
        random.shuffle(deck)
        state["cards"] = deck
        state["buttons"] = []
        state["flipped"] = []
        state["matched"] = set()
        state["moves"] = 0
        state["locked"] = False
        win_banner.configure(
            text="Match all 8 BBC Sounds genre pairs!  ·  Esc to close",
            fg=_theme.TEXT_GRAY,
            font=(_theme.DEFAULT_FONT, 9),
        )

        for idx in range(16):
            btn = tk.Button(
                grid_frame,
                text="BBC\n?",
                width=11,
                height=4,
                font=(_theme.DEFAULT_FONT, 10, "bold"),
                bg=_theme.CARD_BG,
                fg=_theme.ORANGE_HL,
                activebackground=_theme.SUBCARD_BG,
                activeforeground=_theme.ORANGE_ACCENT,
                relief="flat",
                bd=0,
                cursor="hand2",
                highlightthickness=1,
                highlightbackground=_theme.BORDER_LINE,
                command=lambda i=idx: on_card_click(i),
            )
            btn.grid(row=idx // 4, column=idx % 4, padx=5, pady=5)
            state["buttons"].append(btn)
        update_status()

    restart_btn = tk.Button(
        footer, text="Play again", command=start_game,
        font=(_theme.DEFAULT_FONT, 9, "bold"),
        bg=_theme.ORANGE_ACCENT, fg=_theme.PRIMARY_BTN_FG,
        activebackground=_theme.ORANGE_HL, activeforeground=_theme.PRIMARY_BTN_FG,
        relief="flat", bd=0, padx=12, pady=5, cursor="hand2",
    )
    restart_btn.pack(side="right")

    def close_game(_event=None):
        cancel_flip_job()
        parent._memory_window = None
        if win.winfo_exists():
            win.destroy()

    win.bind("<Escape>", close_game)
    win.protocol("WM_DELETE_WINDOW", close_game)
    win.bind("<Destroy>", lambda _e: cancel_flip_job())

    start_game()
    _theme.center_toplevel(win, parent)
    win.focus_force()
    return win

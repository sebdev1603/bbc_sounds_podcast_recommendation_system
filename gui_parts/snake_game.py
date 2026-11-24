"""Hidden BBC Sounds Snake easter-egg mini-game triggered from the BBC logo."""
import random
import tkinter as tk

from gui_parts import theme as _theme


def open_snake_game(parent):
    """Open (or focus) the BBC Sounds themed Snake easter-egg window."""
    win, wrapper, score_lbl = _theme.create_minigame_shell(
        parent, "_snake_window", "BBC Sounds · Snake",
        "BBC SOUNDS SNAKE", "Score: 0   ·   Best: 0",
    )
    if wrapper is None:
        return win

    cols, rows, cell = 22, 18, 22
    board_w, board_h = cols * cell, rows * cell

    board = tk.Canvas(
        wrapper, width=board_w, height=board_h,
        bg=_theme.CARD_BG, bd=0, highlightthickness=1, highlightbackground=_theme.BORDER_LINE,
    )
    board.pack()

    tk.Label(
        wrapper, text="Arrow keys / WASD to move  ·  Space to pause or restart  ·  Esc to close",
        font=(_theme.DEFAULT_FONT, 9), fg=_theme.TEXT_GRAY, bg=_theme.DARK_BG,
    ).pack(pady=(10, 0))

    state = {
        "snake": [],
        "direction": (1, 0),
        "dir_queue": [],
        "food": (0, 0),
        "score": 0,
        "best": getattr(parent, "_snake_best_score", 0),
        "running": False,
        "paused": False,
        "game_over": False,
        "job": None,
    }

    def cancel_loop():
        if state["job"] is not None:
            try:
                win.after_cancel(state["job"])
            except tk.TclError:
                pass
            state["job"] = None

    def place_food():
        occupied = set(state["snake"])
        free = [(x, y) for x in range(cols) for y in range(rows) if (x, y) not in occupied]
        state["food"] = random.choice(free) if free else (0, 0)

    def update_score():
        if state["score"] > state["best"]:
            state["best"] = state["score"]
            parent._snake_best_score = state["best"]
        score_lbl.configure(text=f"Score: {state['score']}   ·   Best: {state['best']}")

    def draw_board():
        board.delete("all")
        # Subtle background grid lines.
        grid_col = _theme.blend_colour(_theme.CARD_BG, _theme.BORDER_LINE, 0.35)
        for gx in range(cell, board_w, cell):
            board.create_line(gx, 0, gx, board_h, fill=grid_col)
        for gy in range(cell, board_h, cell):
            board.create_line(0, gy, board_w, gy, fill=grid_col)

        # Draw glowing food orb.
        fx, fy = state["food"]
        board.create_oval(
            fx * cell + 3, fy * cell + 3, (fx + 1) * cell - 3, (fy + 1) * cell - 3,
            fill=_theme.GOLD_STAR, outline=_theme.ORANGE_ACCENT, width=2,
        )

        # Draw snake body (fading smoothly from bright orange head toward tail).
        length = max(1, len(state["snake"]))
        for idx, (sx, sy) in enumerate(state["snake"]):
            pad = 1 if idx == 0 else 2
            if idx == 0:
                fill = _theme.ORANGE_ACCENT
            else:
                fade = min(0.65, idx / float(length + 4))
                fill = _theme.blend_colour(_theme.ORANGE_HL, _theme.CARD_BG, fade)
            board.create_rectangle(
                sx * cell + pad, sy * cell + pad,
                (sx + 1) * cell - pad, (sy + 1) * cell - pad,
                fill=fill, outline="",
            )

        if state["paused"] and not state["game_over"]:
            board.create_rectangle(
                board_w * 0.22, board_h * 0.38, board_w * 0.78, board_h * 0.62,
                fill=_theme.DARK_BG, outline=_theme.ORANGE_ACCENT, width=2,
            )
            board.create_text(
                board_w / 2, board_h / 2, text="PAUSED\nPress Space to resume",
                fill=_theme.TEXT_WHITE, font=(_theme.DEFAULT_FONT, 12, "bold"), justify="center",
            )
        elif state["game_over"]:
            board.create_rectangle(
                board_w * 0.16, board_h * 0.32, board_w * 0.84, board_h * 0.68,
                fill=_theme.DARK_BG, outline=_theme.ORANGE_ACCENT, width=2,
            )
            board.create_text(
                board_w / 2, board_h * 0.44, text="GAME OVER",
                fill=_theme.ORANGE_ACCENT, font=(_theme.DEFAULT_FONT, 16, "bold"),
            )
            board.create_text(
                board_w / 2, board_h * 0.58,
                text=f"Score: {state['score']}   ·   Press Space to play again",
                fill=_theme.TEXT_WHITE, font=(_theme.DEFAULT_FONT, 10, "bold"),
            )

    def tick():
        state["job"] = None
        if not win.winfo_exists() or not state["running"] or state["paused"] or state["game_over"]:
            return

        if state["dir_queue"]:
            state["direction"] = state["dir_queue"].pop(0)

        dx, dy = state["direction"]
        hx, hy = state["snake"][0]
        nx, ny = hx + dx, hy + dy

        ate = (nx, ny) == state["food"]
        body_to_check = state["snake"] if ate else state["snake"][:-1]
        if nx < 0 or nx >= cols or ny < 0 or ny >= rows or (nx, ny) in body_to_check:
            state["game_over"] = True
            state["running"] = False
            draw_board()
            return

        state["snake"].insert(0, (nx, ny))
        if ate:
            state["score"] += 1
            update_score()
            place_food()
        else:
            state["snake"].pop()

        draw_board()
        delay_ms = max(65, 130 - state["score"] * 3)
        state["job"] = win.after(delay_ms, tick)

    def start_game():
        cancel_loop()
        mid_x, mid_y = cols // 2, rows // 2
        state["snake"] = [(mid_x, mid_y), (mid_x - 1, mid_y), (mid_x - 2, mid_y)]
        state["direction"] = (1, 0)
        state["dir_queue"].clear()
        state["score"] = 0
        state["paused"] = False
        state["game_over"] = False
        state["running"] = True
        place_food()
        update_score()
        draw_board()
        state["job"] = win.after(130, tick)

    key_dirs = {
        "Up": (0, -1), "w": (0, -1), "W": (0, -1),
        "Down": (0, 1), "s": (0, 1), "S": (0, 1),
        "Left": (-1, 0), "a": (-1, 0), "A": (-1, 0),
        "Right": (1, 0), "d": (1, 0), "D": (1, 0),
    }

    def on_key(event):
        if event.keysym == "Escape":
            close_game()
            return
        if event.keysym == "space":
            if state["game_over"]:
                start_game()
            else:
                state["paused"] = not state["paused"]
                draw_board()
                if not state["paused"] and state["job"] is None:
                    state["job"] = win.after(110, tick)
            return
        new_dir = key_dirs.get(event.keysym)
        if new_dir is None or state["paused"] or state["game_over"]:
            return
        last_dir = state["dir_queue"][-1] if state["dir_queue"] else state["direction"]
        if (new_dir[0] + last_dir[0], new_dir[1] + last_dir[1]) != (0, 0) and new_dir != last_dir:
            if len(state["dir_queue"]) < 2:
                state["dir_queue"].append(new_dir)

    def close_game():
        cancel_loop()
        parent._snake_window = None
        if win.winfo_exists():
            win.destroy()

    win.bind("<KeyPress>", on_key)
    win.protocol("WM_DELETE_WINDOW", close_game)
    win.bind("<Destroy>", lambda _e: cancel_loop())

    _theme.center_toplevel(win, parent)
    win.focus_force()
    start_game()
    return win

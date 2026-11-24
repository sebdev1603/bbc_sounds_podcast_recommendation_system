"""Hidden BBC Sounds Flappy Bird easter-egg mini-game triggered from the BBC logo."""
import random
from time import monotonic
import tkinter as tk

from gui_parts import theme as _theme


def open_flappy_game(parent):
    """Open (or focus) the BBC Sounds themed Flappy Bird easter-egg window."""
    win, wrapper, score_lbl = _theme.create_minigame_shell(
        parent, "_flappy_window", "BBC Sounds · Flappy Bird",
        "BBC SOUNDS FLAPPY BIRD", "Score: 0   ·   Best: 0",
    )
    if wrapper is None:
        return win

    board_w, board_h, ground_h = 420, 520, 44
    play_h = board_h - ground_h
    bird_x, bird_r = 115.0, 14.0
    pipe_w, pipe_gap, pipe_speed, pipe_spacing = 56.0, 138.0, 165.0, 215.0
    gravity, flap_vel = 920.0, -325.0

    board = tk.Canvas(
        wrapper, width=board_w, height=board_h,
        bg=_theme.CARD_BG, bd=0, highlightthickness=1, highlightbackground=_theme.BORDER_LINE,
        cursor="hand2",
    )
    board.pack()

    tk.Label(
        wrapper, text="Space / Up / Click to flap  ·  Esc to close",
        font=(_theme.DEFAULT_FONT, 9), fg=_theme.TEXT_GRAY, bg=_theme.DARK_BG,
    ).pack(pady=(10, 0))

    state = {
        "bird_y": play_h * 0.48,
        "bird_vy": 0.0,
        "pipes": [],
        "score": 0,
        "best": getattr(parent, "_flappy_best_score", 0),
        "started": False,
        "game_over": False,
        "last_t": None,
        "job": None,
    }

    def cancel_loop():
        if state["job"] is not None:
            try:
                win.after_cancel(state["job"])
            except tk.TclError:
                pass
            state["job"] = None

    def update_score():
        if state["score"] > state["best"]:
            state["best"] = state["score"]
            parent._flappy_best_score = state["best"]
        score_lbl.configure(text=f"Score: {state['score']}   ·   Best: {state['best']}")

    def spawn_pipe(x_pos):
        margin = 66
        gap_y = random.randint(margin, int(play_h - margin - pipe_gap))
        state["pipes"].append({"x": float(x_pos), "gap_y": float(gap_y), "scored": False})

    def reset_game():
        cancel_loop()
        state["bird_y"] = play_h * 0.48
        state["bird_vy"] = 0.0
        state["pipes"] = []
        state["score"] = 0
        state["started"] = False
        state["game_over"] = False
        state["last_t"] = None
        spawn_pipe(board_w + 80)
        spawn_pipe(board_w + 80 + pipe_spacing)
        spawn_pipe(board_w + 80 + pipe_spacing * 2)
        update_score()
        draw_scene()

    def draw_scene():
        board.delete("all")
        pipe_fill = _theme.blend_colour(_theme.CARD_BG, _theme.ORANGE_ACCENT, 0.32)
        pipe_cap = _theme.ORANGE_ACCENT
        pipe_outline = _theme.BORDER_LINE

        # Pipes
        for p in state["pipes"]:
            px = p["x"]
            gy = p["gap_y"]
            # Top pipe + lip
            board.create_rectangle(px, 0, px + pipe_w, gy, fill=pipe_fill, outline=pipe_outline, width=1)
            board.create_rectangle(px - 4, gy - 14, px + pipe_w + 4, gy, fill=pipe_cap, outline="")
            # Bottom pipe + lip
            by = gy + pipe_gap
            board.create_rectangle(px, by, px + pipe_w, play_h, fill=pipe_fill, outline=pipe_outline, width=1)
            board.create_rectangle(px - 4, by, px + pipe_w + 4, by + 14, fill=pipe_cap, outline="")

        # Ground strip
        board.create_rectangle(0, play_h, board_w, board_h, fill=_theme.SUBCARD_BG, outline="")
        board.create_line(0, play_h, board_w, play_h, fill=_theme.ORANGE_ACCENT, width=3)

        # Bird (body, wing, eye, beak)
        by = state["bird_y"]
        board.create_oval(
            bird_x - bird_r, by - bird_r, bird_x + bird_r, by + bird_r,
            fill=_theme.ORANGE_ACCENT, outline=_theme.GOLD_STAR, width=2,
        )
        wing_dy = -3 if state["bird_vy"] < 0 else 2
        board.create_oval(
            bird_x - 10, by + wing_dy - 4, bird_x + 2, by + wing_dy + 6,
            fill=_theme.ORANGE_HL, outline="",
        )
        board.create_oval(bird_x + 3, by - 7, bird_x + 10, by, fill="#ffffff", outline="")
        board.create_oval(bird_x + 6, by - 5, bird_x + 9, by - 2, fill="#111111", outline="")
        board.create_polygon(
            bird_x + bird_r - 1, by - 3,
            bird_x + bird_r + 9, by + 1,
            bird_x + bird_r - 1, by + 5,
            fill=_theme.GOLD_STAR, outline="",
        )

        # Live score watermark
        if state["started"] and not state["game_over"]:
            board.create_text(
                board_w / 2, 42, text=str(state["score"]),
                fill=_theme.TEXT_WHITE, font=(_theme.DEFAULT_FONT, 24, "bold"),
            )

        if not state["started"] and not state["game_over"]:
            board.create_rectangle(
                board_w * 0.14, board_h * 0.62, board_w * 0.86, board_h * 0.78,
                fill=_theme.DARK_BG, outline=_theme.ORANGE_ACCENT, width=2,
            )
            board.create_text(
                board_w / 2, board_h * 0.70, text="Press Space or Click to flap!",
                fill=_theme.TEXT_WHITE, font=(_theme.DEFAULT_FONT, 11, "bold"),
            )
        elif state["game_over"]:
            board.create_rectangle(
                board_w * 0.12, board_h * 0.34, board_w * 0.88, board_h * 0.62,
                fill=_theme.DARK_BG, outline=_theme.ORANGE_ACCENT, width=2,
            )
            board.create_text(
                board_w / 2, board_h * 0.43, text="GAME OVER",
                fill=_theme.ORANGE_ACCENT, font=(_theme.DEFAULT_FONT, 17, "bold"),
            )
            board.create_text(
                board_w / 2, board_h * 0.54,
                text=f"Score: {state['score']}   ·   Space or Click to play again",
                fill=_theme.TEXT_WHITE, font=(_theme.DEFAULT_FONT, 10, "bold"),
            )

    def tick():
        state["job"] = None
        if not win.winfo_exists() or not state["started"] or state["game_over"]:
            return
        now = monotonic()
        dt = 0.016 if state["last_t"] is None else min(0.045, now - state["last_t"])
        state["last_t"] = now

        # Physics
        state["bird_vy"] += gravity * dt
        state["bird_y"] += state["bird_vy"] * dt

        # Move pipes & check scoring/recycling
        speed = pipe_speed + min(75.0, state["score"] * 3.0)
        for p in state["pipes"]:
            p["x"] -= speed * dt
            if not p["scored"] and p["x"] + pipe_w < bird_x:
                p["scored"] = True
                state["score"] += 1
                update_score()

        if state["pipes"] and state["pipes"][0]["x"] + pipe_w < -10:
            state["pipes"].pop(0)
            rightmost = max(p["x"] for p in state["pipes"])
            spawn_pipe(rightmost + pipe_spacing)

        # Collisions (ground, ceiling, pipes)
        by = state["bird_y"]
        hit = by + bird_r >= play_h or by - bird_r <= 0
        if not hit:
            for p in state["pipes"]:
                if bird_x + bird_r - 2 > p["x"] and bird_x - bird_r + 2 < p["x"] + pipe_w:
                    if by - bird_r + 2 < p["gap_y"] or by + bird_r - 2 > p["gap_y"] + pipe_gap:
                        hit = True
                        break

        if hit:
            state["bird_y"] = min(play_h - bird_r, max(bird_r, state["bird_y"]))
            state["game_over"] = True
            draw_scene()
            return

        draw_scene()
        state["job"] = win.after(16, tick)

    def flap(_event=None):
        if state["game_over"]:
            reset_game()
            return
        if not state["started"]:
            state["started"] = True
            state["last_t"] = monotonic()
        state["bird_vy"] = flap_vel
        if state["job"] is None:
            state["job"] = win.after(16, tick)

    def close_game(_event=None):
        cancel_loop()
        parent._flappy_window = None
        if win.winfo_exists():
            win.destroy()

    win.bind("<space>", flap)
    win.bind("<Up>", flap)
    win.bind("<w>", flap)
    win.bind("<W>", flap)
    win.bind("<Escape>", close_game)
    board.bind("<Button-1>", flap)
    win.protocol("WM_DELETE_WINDOW", close_game)
    win.bind("<Destroy>", lambda _e: cancel_loop())

    reset_game()
    _theme.center_toplevel(win, parent)
    win.focus_force()
    return win

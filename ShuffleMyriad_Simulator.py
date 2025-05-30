import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import random
import sys
from datetime import datetime
import time

# --- Helper Functions (can be outside classes or static methods) ---
def load_config(config_file="config.cfg"):
    default_opponent_refresh_rate = 120
    if not os.path.exists(config_file):
        print(f"{config_file} not found. Using default refresh rate: {default_opponent_refresh_rate}")
        return default_opponent_refresh_rate
    try:
        with open(config_file, "r") as f:
            for line in f:
                if line.startswith("opponent_refresh_rate"):
                    _, value = line.strip().split("=")
                    return int(value)
    except Exception as e:
        print(f"Error reading {config_file}: {e}. Using default refresh rate: {default_opponent_refresh_rate}")
    return default_opponent_refresh_rate

def center_tk_window(parent_root, window, width, height):
    """Centers a Tkinter window relative to its parent or screen."""
    window.update_idletasks() # Ensure window dimensions are up-to-date
    if parent_root and parent_root.winfo_viewable():
        parent_x = parent_root.winfo_x()
        parent_y = parent_root.winfo_y()
        parent_width = parent_root.winfo_width()
        parent_height = parent_root.winfo_height()
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)
    else: # Fallback to screen centering if parent is not available/viewable
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def create_translucent_rectangle(width, height, color, alpha):
    image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle([(0, 0), (width, height)], fill=(*color, alpha))
    return ImageTk.PhotoImage(image)

def draw_text_with_outline(draw, position, text, font, text_color, outline_color, outline_width, marker_width, marker_height, text_width, text_height):
    x, y = position
    text_x = x + (marker_width - text_width) // 2
    text_y = y + (marker_height - text_height) // 2 - 2
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((text_x + dx, text_y + dy), text, font=font, fill=outline_color)
    draw.text((text_x, text_y), text, font=font, fill=text_color)

class ShuffleMyriadApp:
    def __init__(self, root):
        self.root = root
        self.opponent_refresh_rate = load_config()

        self._setup_main_window()

        self.deck = []
        self.ex_deck = []
        self.on_board = []
        self.markers = []
        self.selected_card = None
        self.is_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        self.last_displayed_image = None # For InfoWindow
        self.life_points = tk.IntVar(value=0)

        self._load_default_images()
        self._setup_ui_elements()
        self._bind_events()

        self.info_window_instance = None
        self.opponent_window_instance = None
        self.deck_contents_window_instance = None
        self.marker_edit_window_instance = None
        
        self.draw_cards()
        self.root.after(100, self._show_initial_windows)


    def _setup_main_window(self):
        self.root.title("ShuffleMyriad_Simulator")
        self.root.geometry("960x860")
        center_tk_window(None, self.root, 960, 860) # Center on screen initially
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(self.root, width=960, height=720, bg="white")
        self.canvas.pack()

    def _load_default_images(self):
        self.playmat_path = os.path.join("resource", "playmat.png")
        try:
            self.playmat_image_pil = Image.open(self.playmat_path).resize((960, 720))
            self.playmat_photo = ImageTk.PhotoImage(self.playmat_image_pil)
        except FileNotFoundError:
            self.playmat_image_pil = Image.new("RGB", (960,720), "lightgrey")
            self.playmat_photo = ImageTk.PhotoImage(self.playmat_image_pil)
            print(f"Warning: Playmat image not found at {self.playmat_path}")


        self.reverse_image_path = os.path.join("resource", "reverse.png")
        try:
            self.reverse_image_pil = Image.open(self.reverse_image_path).resize((78, 111))
            self.reverse_photo_image = ImageTk.PhotoImage(self.reverse_image_pil)
            self.reverse_rotated_image_pil = self.reverse_image_pil.rotate(90, expand=True).resize((111, 78))
            self.reverse_rotated_photo_image = ImageTk.PhotoImage(self.reverse_rotated_image_pil)
        except FileNotFoundError:
            self.reverse_image_pil = None
            self.reverse_photo_image = None
            self.reverse_rotated_image_pil = None
            self.reverse_rotated_photo_image = None
            print(f"Warning: Reverse card image not found at {self.reverse_image_path}")

        noimage_path = os.path.join("resource", "noimage.png")
        try:
            self.noimage_pil = Image.open(noimage_path).resize((78, 111))
            self.noimage_photo_image = ImageTk.PhotoImage(self.noimage_pil)
            self.noimage_large_pil = self.noimage_pil.resize((390, 555))
            self.noimage_large_photo_image = ImageTk.PhotoImage(self.noimage_large_pil)
        except FileNotFoundError:
            self.noimage_pil = None
            self.noimage_photo_image = None
            self.noimage_large_pil = None
            self.noimage_large_photo_image = None
            print(f"Warning: 'noimage.png' not found in resource folder.")


        unknown_image_path = os.path.join("resource", "unknown.png")
        try:
            self.unknown_image_pil = Image.open(unknown_image_path).resize((390, 555))
            self.unknown_photo_image = ImageTk.PhotoImage(self.unknown_image_pil)
        except FileNotFoundError:
            self.unknown_image_pil = None
            self.unknown_photo_image = None
            print(f"Warning: 'unknown.png' not found in resource folder.")
            if self.noimage_large_photo_image: # Fallback to noimage if unknown is missing
                 self.unknown_photo_image = self.noimage_large_photo_image


        # Buttons that appear on card selection
        self.reverse_button = None
        self.bring_to_front_button = None
        self.send_to_back_button = None

    def _setup_ui_elements(self):
        button_frame = tk.Frame(self.root)
        button_frame.pack()

        bottom_right_frame = tk.Frame(self.root)
        bottom_right_frame.place(relx=1.0, rely=1.0, anchor="se")

        bottom_left_frame = tk.Frame(self.root)
        bottom_left_frame.place(relx=0.0, rely=1.0, anchor="sw")

        tk.Label(bottom_left_frame, text="ライフポイント:").pack(side="top", padx=5, pady=2)
        validate_cmd = self.root.register(self._validate_life_input)
        life_spinbox = tk.Spinbox(
            bottom_left_frame, from_=0, to=999999, increment=1,
            textvariable=self.life_points, width=8, validate="key",
            validatecommand=(validate_cmd, "%P")
        )
        life_spinbox.pack(side="top", padx=5, pady=2)

        self.deck_count_label = tk.Label(bottom_left_frame, text=f"デッキ: {len(self.deck)}枚", font=("Arial", 10))
        self.deck_count_label.pack(side="top", padx=5, pady=2)

        gacha_button_frame = tk.Frame(bottom_left_frame)
        gacha_button_frame.pack(side="top", padx=5, pady=2)
        
        gacha_buttons_config = [("コイントス", self.coin_toss), ("6面ダイス", self.roll_dice)]
        for i, (text, command) in enumerate(gacha_buttons_config):
            btn = tk.Button(gacha_button_frame, text=text, command=command)
            btn.grid(row=0, column=i, padx=2, pady=2)

        main_buttons_config = [
            ("デッキトップへ戻す", self.move_to_deck_top),
            ("デッキボトムへ戻す", self.move_to_deck_bottom),
            ("すべて回転解除", self.unrotate_all),
            ("ドロー", self.draw_from_deck),
            ("シャッフル", self.shuffle_deck),
            ("マーカーを追加", self.add_marker),
            ("カードID指定生成", self.select_card_by_id),
            ("デッキから表向きで出す", lambda: self.draw_from_deck(y=350)),
            ("デッキから裏向きで出す", lambda: self.draw_from_deck(face_up=False, y=350)),
            ("デッキの中身を見る", self.open_deck_contents_window),
        ]
        for i, (text, command) in enumerate(main_buttons_config):
            btn = tk.Button(button_frame, text=text, command=command)
            btn.grid(row=i // 5, column=i % 5, padx=5, pady=5)

        special_buttons_config = [
            ("100連ガチャ", self.gacha_deck_making),
            ("デッキをロード", self.load_deck),
            ("盤面のセーブ", self.save_board),
            ("盤面のロード", self.load_board),
            ("再起動", self.restart_app),
        ]
        for i, (text, command) in enumerate(special_buttons_config):
            btn = tk.Button(bottom_right_frame, text=text, command=command)
            btn.grid(row=i // 2, column=i % 2, padx=5, pady=5)

        self.dice_label = tk.Label(self.root, text="", font=("YuGothB.ttc", 24), bg="white")
        # Opponent dice label will be managed by OpponentWindow

    def _validate_life_input(self, new_value):
        if new_value == "": return True
        try:
            val = int(new_value)
            return 0 <= val <= 999999
        except ValueError:
            return False

    def _bind_events(self):
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.root.bind("<Delete>", self._on_delete_key)
        self.canvas.bind("<Double-1>", self._on_canvas_double_click)
        self.root.bind("<Control-t>", lambda event: self.move_to_deck_top())
        self.root.bind("<Control-b>", lambda event: self.move_to_deck_bottom())
        self.root.bind("<Control-f>", lambda event: self.bring_to_front())
        self.root.bind("<Control-r>", lambda event: self.send_to_back())
        self.root.bind("<Control-c>", self._copy_card_id_to_clipboard)

    def _show_initial_windows(self):
        self.open_info_window()
        self.open_opponent_window()

    def _update_dynamic_buttons_visibility(self):
        # Hide existing buttons first
        if self.reverse_button: self.reverse_button.place_forget()
        if self.bring_to_front_button: self.bring_to_front_button.place_forget()
        if self.send_to_back_button: self.send_to_back_button.place_forget()

        if self.selected_card and self.selected_card not in self.markers and not self.is_dragging:
            if not self.reverse_button: # Create if not exists
                self.reverse_button = tk.Button(self.root, text="リバース", command=self.reverse_card)
                self.bring_to_front_button = tk.Button(self.root, text="最前面", command=self.bring_to_front)
                self.send_to_back_button = tk.Button(self.root, text="最背面", command=self.send_to_back)

            button_x = self.selected_card["x"] + self.selected_card["width"] // 2 - 22 # Approx center
            button_y = self.selected_card["y"] + self.selected_card["height"] + 5

            self.reverse_button.place(x=button_x, y=button_y)
            self.bring_to_front_button.place(x=button_x - 50, y=button_y) # Adjust relative positions as needed
            self.send_to_back_button.place(x=button_x + 50, y=button_y)


    def draw_cards(self):
        self.canvas.delete("all")
        if self.playmat_photo:
            self.canvas.create_image(0, 0, image=self.playmat_photo, anchor="nw")

        # Draw cards
        for card_data in self.on_board:
            x = max(0, min(card_data.get("x", 0), 960 - card_data.get("width", 78)))
            y = max(0, min(card_data.get("y", 0), 720 - card_data.get("height", 111)))
            card_data["x"], card_data["y"] = x, y # Update stored position

            img_to_draw = None
            if card_data.get("face_up", True):
                if card_data.get("original_image"): # PIL Image
                    current_pil_image = card_data["original_image"]
                    if card_data.get("rotated"):
                        rotated_pil_image = current_pil_image.rotate(90, expand=True).resize((111, 78))
                        card_data["image"] = ImageTk.PhotoImage(rotated_pil_image) # Update TkImage
                        card_data["width"], card_data["height"] = 111, 78
                    else:
                        resized_pil_image = current_pil_image.resize((78, 111))
                        card_data["image"] = ImageTk.PhotoImage(resized_pil_image) # Update TkImage
                        card_data["width"], card_data["height"] = 78, 111
                    img_to_draw = card_data["image"]
                elif self.noimage_photo_image: 
                    img_to_draw = self.noimage_photo_image 
                    card_data["width"], card_data["height"] = (111,78) if card_data.get("rotated") else (78,111)


            else: # Face down
                if card_data.get("rotated"):
                    img_to_draw = self.reverse_rotated_photo_image
                    card_data["width"], card_data["height"] = 111, 78
                else:
                    img_to_draw = self.reverse_photo_image
                    card_data["width"], card_data["height"] = 78, 111
            
            if img_to_draw:
                self.canvas.create_image(x, y, image=img_to_draw, anchor="nw")
            
            if card_data == self.selected_card:
                self.canvas.create_rectangle(x, y, x + card_data["width"], y + card_data["height"], outline="red", width=3)

        self._update_dynamic_buttons_visibility()

        if self.markers:
            marker_layer_pil = Image.new("RGBA", (self.canvas.winfo_width(), self.canvas.winfo_height()), (255, 255, 255, 0))
            draw_pil = ImageDraw.Draw(marker_layer_pil)
            
            try:
                font = ImageFont.truetype("YuGothB.ttc", 14) 
            except IOError:
                font = ImageFont.load_default()


            for marker in self.markers:
                text_width, text_height = 0, 0
                if marker["text"]:
                    try:
                        bbox = draw_pil.textbbox((0,0), marker["text"], font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                    except Exception as e: 
                         print(f"Could not get textbbox for marker text '{marker['text']}': {e}")

                marker["text_width"] = text_width
                marker["text_height"] = text_height
                marker["width"] = max(marker["text_width"] + 20, 120)
                marker["height"] = max(marker["text_height"] + 10, 50)
                
                mx, my, mw, mh = marker["x"], marker["y"], marker["width"], marker["height"]
                
                translucent_color_pil = (128, 128, 128, 128) # RGBA
                draw_pil.rectangle([mx, my, mx + mw, my + mh], fill=translucent_color_pil)

                if marker["text"]:
                    draw_text_with_outline(draw_pil, (mx, my), marker["text"], font,
                                           "black", "white", 2, 
                                           mw, mh, text_width, text_height)
                
                if marker == self.selected_card: 
                    self.canvas.create_rectangle(mx, my, mx + mw, my + mh, outline="red", width=3)

            self.marker_layer_tk = ImageTk.PhotoImage(marker_layer_pil)
            self.canvas.create_image(0,0, image=self.marker_layer_tk, anchor="nw")

        self.update_deck_count_display()
        if self.info_window_instance:
            self.info_window_instance.update_display()
        if self.opponent_window_instance and self.opponent_window_instance.is_active():
            self.opponent_window_instance.needs_redraw = True

    def load_deck(self):
        base_path = os.path.dirname(sys.argv[0]) if getattr(sys, 'frozen', False) else os.getcwd()
        deck_folder_path = os.path.join(base_path, "deck")
        if not os.path.exists(deck_folder_path):
            try:
                os.makedirs(deck_folder_path)
                print(f"Created directory: {deck_folder_path}")
            except OSError as e:
                messagebox.showerror("エラー", f"deckフォルダの作成に失敗しました: {e}")
                return 

        file_path = filedialog.askopenfilename(
            title="デッキデータを選択",
            filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")],
            initialdir=deck_folder_path 
        )
        if not file_path: return

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                lines = [line.strip() for line in file if line.strip()]

            resource_section_content = []
            if "[Resource]" in lines:
                resource_index = lines.index("[Resource]")
                resource_section_content = lines[resource_index + 1:]
                lines = lines[:resource_index]

            new_reverse_path = os.path.join("resource", resource_section_content[0]) if len(resource_section_content) > 0 else os.path.join("resource", "reverse.png")
            new_playmat_path = os.path.join("resource", resource_section_content[1]) if len(resource_section_content) > 1 else os.path.join("resource", "playmat.png")

            if new_reverse_path != self.reverse_image_path or not self.reverse_image_pil:
                self.reverse_image_path = new_reverse_path
                try:
                    self.reverse_image_pil = Image.open(self.reverse_image_path).resize((78, 111))
                    self.reverse_photo_image = ImageTk.PhotoImage(self.reverse_image_pil)
                    self.reverse_rotated_image_pil = self.reverse_image_pil.rotate(90, expand=True).resize((111, 78))
                    self.reverse_rotated_photo_image = ImageTk.PhotoImage(self.reverse_rotated_image_pil)
                except FileNotFoundError:
                    print(f"Warning: Custom reverse image not found at {self.reverse_image_path}, using default or none.")
                    if not os.path.exists(self.reverse_image_path): 
                        self.reverse_image_pil = None
                        self.reverse_photo_image = None
                        self.reverse_rotated_image_pil = None
                        self.reverse_rotated_photo_image = None


            if new_playmat_path != self.playmat_path or not self.playmat_image_pil:
                self.playmat_path = new_playmat_path
                try:
                    self.playmat_image_pil = Image.open(self.playmat_path).resize((960, 720))
                    self.playmat_photo = ImageTk.PhotoImage(self.playmat_image_pil)
                except FileNotFoundError:
                    print(f"Warning: Custom playmat image not found at {self.playmat_path}, using default or none.")
                    if not os.path.exists(self.playmat_path): 
                        self.playmat_image_pil = Image.new("RGB", (960,720), "lightgrey")
                        self.playmat_photo = ImageTk.PhotoImage(self.playmat_image_pil)


            self.deck = []
            self.ex_deck = []
            
            main_deck_lines = lines
            if "[EX]" in lines:
                ex_index = lines.index("[EX]")
                main_deck_lines = lines[:ex_index]
                ex_deck_lines = lines[ex_index + 1:]
                for card_id in ex_deck_lines:
                    self.ex_deck.append(self._create_card_dict(card_id, face_up=True, revealed=True))
            
            for card_id in main_deck_lines:
                self.deck.append(self._create_card_dict(card_id, face_up=True, revealed=True))

            x, y = 20, 600
            for card_data in self.ex_deck:
                card_data["x"], card_data["y"] = x, y
                self.on_board.append(card_data) 
                x += 15
                if x > 900: x, y = 20, y + 10
            
            self.draw_cards()
            messagebox.showinfo("成功", f"デッキを読み込みました！カード数: {len(self.deck)}, EXデッキカード数: {len(self.ex_deck)}")
        except Exception as e:
            messagebox.showerror("エラー", f"デッキの読み込み中にエラーが発生しました:\n{e}")


    def _create_card_dict(self, card_id, x=0, y=0, rotated=False, face_up=True, revealed=True):
        card_data = {
            "id": card_id, "width": 78, "height": 111,
            "rotated": rotated, "face_up": face_up, "revealed": revealed,
            "image": None, "original_image": None, 
            "x": x, "y": y
        }
        image_path = os.path.join("card-img", f"{card_id}.png")
        try:
            pil_img = Image.open(image_path) 
            card_data["original_image"] = pil_img
        except FileNotFoundError:
            if self.noimage_pil:
                card_data["original_image"] = self.noimage_pil.copy() 
        return card_data

    def shuffle_deck(self):
        if not self.deck:
            messagebox.showinfo("エラー", "デッキが空です！")
            return
        random.shuffle(self.deck)
        self._show_temporary_message("シャッフル")

    def _show_temporary_message(self, message_text):
        self.dice_label.config(text=message_text)
        self.dice_label.place(relx=0.5, rely=0.5, anchor="center")
        if self.opponent_window_instance and self.opponent_window_instance.is_active():
            self.opponent_window_instance.show_dice_result(message_text)

    def select_card_by_id(self):
        card_id = simpledialog.askstring("カードID入力", "カードIDを入力してください:")
        if not card_id: return

        image_path = os.path.join("card-img", f"{card_id}.png")
        if not (os.path.exists(image_path) or self.noimage_pil): 
            messagebox.showinfo("エラー", "指定したIDのカード画像が見つかりません（noimage.pngもありません）！")
            return

        card_data = self._create_card_dict(card_id, x=600, y=500, face_up=True, revealed=True)
        self._adjust_card_position(card_data)
        self.on_board.append(card_data)
        self.selected_card = card_data 
        self.draw_cards()

    def _adjust_card_position(self, new_card):
        offset_x_orig, offset_y_orig = 10, 2
        offset_x, offset_y = offset_x_orig, offset_y_orig
        max_attempts = 100
        attempts = 0
        
        while attempts < max_attempts:
            overlap = False
            for card in self.on_board:
                if card is new_card: continue 
                if abs(card["x"] - new_card["x"]) == 0 and abs(card["y"] - new_card["y"]) == 0:
                    new_card["x"] += offset_x
                    new_card["y"] += offset_y

                    if new_card["x"] + new_card.get("width", 78) > 960 or new_card["x"] < 0:
                        new_card["x"] -= 2 * offset_x 
                        offset_x *= -1 
                    if new_card["y"] + new_card.get("height", 111) > 720 or new_card["y"] < 0:
                        new_card["y"] -= 2 * offset_y
                        offset_y *= -1

                    new_card["x"] = max(0, min(new_card["x"], 960 - new_card.get("width", 78)))
                    new_card["y"] = max(0, min(new_card["y"], 720 - new_card.get("height", 111)))
                    
                    overlap = True
                    break 
            if not overlap:
                return 
            attempts += 1
            if attempts % 10 == 0: 
                offset_x, offset_y = offset_x_orig, offset_y_orig
                new_card["x"] += random.randint(-5,5) 
                new_card["y"] += random.randint(-5,5)


        if attempts >= max_attempts:
            print("Warning: Max attempts reached for card position adjustment. Card may overlap.")

    def add_marker(self):
        marker = {
            "type": "marker",
            "x": self.canvas.winfo_width() // 2 - 60,
            "y": int(self.canvas.winfo_height() * 0.9),
            "width": 120, "height": 50,
            "text": "", "selected": False, 
            "text_width": 0, "text_height": 0 
        }
        self.markers.append(marker)
        self.selected_card = marker 
        self.draw_cards()


    def _on_canvas_click(self, event):
        self.root.focus_set() 
        self._dice_label_forget()
        
        self.selected_card = None 
        for marker in reversed(self.markers): 
            if marker["x"] <= event.x < marker["x"] + marker["width"] and \
               marker["y"] <= event.y < marker["y"] + marker["height"]:
                self.selected_card = marker
                self.is_dragging = True
                self.drag_offset_x = event.x - marker["x"]
                self.drag_offset_y = event.y - marker["y"]
                self.draw_cards()
                return 

        for card_data in reversed(self.on_board): 
            if card_data["x"] <= event.x < card_data["x"] + card_data["width"] and \
               card_data["y"] <= event.y < card_data["y"] + card_data["height"]:
                self.selected_card = card_data
                self.is_dragging = True
                self.drag_offset_x = event.x - card_data["x"]
                self.drag_offset_y = event.y - card_data["y"]
                self.draw_cards()
                return 
        
        self.is_dragging = False
        self.draw_cards() 

    def _on_canvas_drag(self, event):
        if self.selected_card and self.is_dragging:
            new_x = event.x - self.drag_offset_x
            new_y = event.y - self.drag_offset_y
            
            self.selected_card["x"] = new_x
            self.selected_card["y"] = new_y
            self.draw_cards()

    def _on_canvas_release(self, event):
        self.is_dragging = False
        if self.selected_card: 
            w, h = self.selected_card["width"], self.selected_card["height"]
            self.selected_card["x"] = max(0, min(self.selected_card["x"], self.canvas.winfo_width() - w))
            self.selected_card["y"] = max(0, min(self.selected_card["y"], self.canvas.winfo_height() - h))
        self.draw_cards() 

    def _on_canvas_right_click(self, event):
        self.root.focus_set()
        self._dice_label_forget()
        clicked_on_card = None
        for card_data in reversed(self.on_board):
            if card_data["x"] <= event.x < card_data["x"] + card_data["width"] and \
               card_data["y"] <= event.y < card_data["y"] + card_data["height"]:
                clicked_on_card = card_data
                break
        
        if clicked_on_card:
            if self.selected_card != clicked_on_card:
                self.selected_card = clicked_on_card
            
            cx = self.selected_card["x"] + self.selected_card["width"] / 2
            cy = self.selected_card["y"] + self.selected_card["height"] / 2
            
            self.selected_card["rotated"] = not self.selected_card["rotated"]
            
            if self.selected_card["rotated"]:
                self.selected_card["width"], self.selected_card["height"] = 111, 78
            else:
                self.selected_card["width"], self.selected_card["height"] = 78, 111

            self.selected_card["x"] = int(cx - self.selected_card["width"] / 2)
            self.selected_card["y"] = int(cy - self.selected_card["height"] / 2)

            self.draw_cards()

    def _on_canvas_double_click(self, event):
        if self.selected_card and self.selected_card.get("type") == "marker":
            self.open_marker_edit_window()

    def _on_delete_key(self, event=None):
        if self.selected_card:
            if self.selected_card in self.on_board:
                self.on_board.remove(self.selected_card)
            elif self.selected_card in self.markers:
                self.markers.remove(self.selected_card)
            self.selected_card = None
            self.draw_cards()

    def reverse_card(self):
        if not self.selected_card or self.selected_card.get("type") == "marker":
            messagebox.showinfo("エラー", "リバースするカードを選択してください！")
            return
        self.selected_card["face_up"] = not self.selected_card["face_up"]
        if self.selected_card["face_up"]:
            self.selected_card["revealed"] = True
        self.draw_cards()

    def bring_to_front(self):
        if not self.selected_card: return
        if self.selected_card in self.on_board:
            self.on_board.remove(self.selected_card)
            self.on_board.append(self.selected_card)
        elif self.selected_card in self.markers: 
            self.markers.remove(self.selected_card)
            self.markers.append(self.selected_card)
        self.draw_cards()

    def send_to_back(self):
        if not self.selected_card: return
        if self.selected_card in self.on_board:
            self.on_board.remove(self.selected_card)
            self.on_board.insert(0, self.selected_card)
        elif self.selected_card in self.markers:
            self.markers.remove(self.selected_card)
            self.markers.insert(0, self.selected_card)
        self.draw_cards()

    def move_to_deck_top(self):
        if not self.selected_card or self.selected_card.get("type") == "marker":
            return
        if self.selected_card in self.on_board:
            card_to_move = self.selected_card
            self.on_board.remove(card_to_move)
            card_to_move["face_up"] = True 
            card_to_move["rotated"] = False
            card_to_move["revealed"] = True 
            self.deck.insert(0, card_to_move)
            self.selected_card = None
            self.draw_cards()

    def move_to_deck_bottom(self):
        if not self.selected_card or self.selected_card.get("type") == "marker":
            return
        if self.selected_card in self.on_board:
            card_to_move = self.selected_card
            self.on_board.remove(card_to_move)
            card_to_move["face_up"] = True 
            card_to_move["rotated"] = False
            card_to_move["revealed"] = True
            self.deck.append(card_to_move)
            self.selected_card = None
            self.draw_cards()

    def unrotate_all(self):
        for card_data in self.on_board:
            if card_data.get("rotated"):
                cx = card_data["x"] + card_data["width"] / 2
                cy = card_data["y"] + card_data["height"] / 2
                card_data["rotated"] = False
                card_data["width"], card_data["height"] = 78, 111 
                card_data["x"] = int(cx - card_data["width"] / 2)
                card_data["y"] = int(cy - card_data["height"] / 2)
        self.draw_cards()

    def draw_from_deck(self, face_up=True, x=600, y=500):
        if not self.deck:
            messagebox.showinfo("デッキ", "デッキにカードがありません！")
            return
        card_data = self.deck.pop(0)
        card_data["x"] = x
        card_data["y"] = y
        card_data["rotated"] = False
        card_data["face_up"] = face_up
        card_data["revealed"] = face_up
        
        self._adjust_card_position(card_data)
        self.on_board.append(card_data)
        self.selected_card = card_data
        self.draw_cards()


    def gacha_deck_making(self):
        card_mapping_ex_val = {} 
        # MODIFIED: Load CardList.csv from script's directory (root)
        card_list_path = "CardList.csv" 

        try:
            with open(card_list_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split(",", 2)
                        if len(parts) == 3:
                            card_id, _, card_ex_val = parts
                            card_mapping_ex_val[card_id] = card_ex_val
                        else:
                            print(f"Skipping malformed line in {card_list_path}: {line}")

        except FileNotFoundError:
            messagebox.showerror("エラー", f"{card_list_path}が見つかりません！")
            return
        if not card_mapping_ex_val:
            messagebox.showerror("エラー", f"{card_list_path}が空または不正な形式です。")
            return

        card_ids_in_list = list(card_mapping_ex_val.keys())
        if not card_ids_in_list:
            messagebox.showerror("エラー", f"{card_list_path}から読み込めるカードがありません。")
            return

        gacha_selected_cards = []
        for _ in range(100):
            chosen_card_id = random.choice(card_ids_in_list)
            while int(card_mapping_ex_val.get(chosen_card_id, "0")) >= 2: 
                chosen_card_id = random.choice(card_ids_in_list)
            gacha_selected_cards.append(chosen_card_id)

        ex_0 = sorted([cid for cid in gacha_selected_cards if card_mapping_ex_val.get(cid) == "0"])
        ex_1 = sorted([cid for cid in gacha_selected_cards if card_mapping_ex_val.get(cid) == "1"])

        # Gacha deck output still goes to 'deck' folder
        deck_folder = "deck"
        if not os.path.exists(deck_folder):
            try:
                os.makedirs(deck_folder) 
            except OSError as e:
                messagebox.showerror("エラー", f"{deck_folder}フォルダの作成に失敗しました: {e}")
                return
        
        output_filename_base = f"gacha_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        output_filename = os.path.join(deck_folder, output_filename_base)
        
        try:
            with open(output_filename, "w", encoding="utf-8") as f:
                for card_id in ex_0: f.write(f"{card_id}\n")
                f.write("[EX]\n")
                for card_id in ex_1: f.write(f"{card_id}\n")
                f.write("[Resource]\nreverse.png\nplaymat.png\n")
            messagebox.showinfo("成功", f"{output_filename} に正常にデッキが出力されました。")
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの書き込み中に問題が発生しました: {e}")


    def _dice_label_forget(self):
        self.dice_label.place_forget()
        if self.opponent_window_instance and self.opponent_window_instance.is_active():
            self.opponent_window_instance.hide_dice_result()

    def roll_dice(self):
        self.selected_card = None 
        self.draw_cards() 
        if self.dice_label.winfo_ismapped():
            self._dice_label_forget()
        else:
            result = random.randint(1, 6)
            self._display_animated_result(result, "1D6", "1D6...")
            
    def coin_toss(self):
        self.selected_card = None 
        self.draw_cards() 
        if self.dice_label.winfo_ismapped():
            self._dice_label_forget()
        else:
            result_val = random.randint(1, 2)
            result_text = "表" if result_val == 1 else "裏"
            self._display_animated_result(result_text, "コイントス", "コイントス...")

    def _display_animated_result(self, final_result, base_message, animated_message_stem):
        messages = [animated_message_stem[0:i] for i in range(len(base_message), len(animated_message_stem) +1 )]
        
        self.dice_label.place(relx=0.5, rely=0.5, anchor="center")
        if self.opponent_window_instance and self.opponent_window_instance.is_active():
             self.opponent_window_instance.show_dice_result("") 

        def update_text(index):
            if index < len(messages):
                current_text = messages[index]
                self.dice_label.config(text=current_text)
                if self.opponent_window_instance and self.opponent_window_instance.is_active():
                    self.opponent_window_instance.update_dice_text(current_text)
                self.root.after(100, update_text, index + 1)
            else:
                final_text_display = f"{animated_message_stem} {final_result}"
                self.dice_label.config(text=final_text_display)
                if self.opponent_window_instance and self.opponent_window_instance.is_active():
                    self.opponent_window_instance.update_dice_text(final_text_display)

        update_text(0)

    def save_board(self):
        # MODIFIED: Save board files to 'save' folder
        save_folder = "save"
        if not os.path.exists(save_folder):
            try:
                os.makedirs(save_folder)
                print(f"Created directory: {save_folder}")
            except OSError as e:
                messagebox.showerror("エラー", f"{save_folder}フォルダの作成に失敗しました: {e}")
                return

        output_filename_base = f"save_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        output_filename = os.path.join(save_folder, output_filename_base) 
        try:
            with open(output_filename, "w", encoding="utf-8") as file:
                file.write("[Resource]\n")
                reverse_rel_path = os.path.basename(self.reverse_image_path) if self.reverse_image_path else "reverse.png"
                playmat_rel_path = os.path.basename(self.playmat_path) if self.playmat_path else "playmat.png"
                file.write(f"{reverse_rel_path}\n")
                file.write(f"{playmat_rel_path}\n")

                file.write("[Deck]\n")
                for card_data in self.deck: file.write(f"{card_data['id']}\n")

                file.write("[Board]\n")
                for card_data in self.on_board:
                    if card_data.get("type") == "marker": continue 
                    file.write(
                        f"{card_data['id']},{card_data['x']},{card_data['y']},"
                        f"{int(card_data['rotated'])},{int(card_data['face_up'])},{int(card_data['revealed'])}\n"
                    )
                
                file.write("[Markers]\n")
                for marker in self.markers:
                    text_escaped = marker['text'].replace('\n', '\\n')
                    file.write(
                        f"{text_escaped},{marker['x']},{marker['y']},"
                        f"{marker['width']},{marker['height']}\n"
                    )
            messagebox.showinfo("成功", f"盤面を保存しました！\nファイル名: {output_filename}")
        except Exception as e:
            messagebox.showerror("エラー", f"保存中にエラーが発生しました:\n{e}")

    def load_board(self):
        # MODIFIED: Set initial directory for loading board saves to 'save' folder
        base_path = os.path.dirname(sys.argv[0]) if getattr(sys, 'frozen', False) else os.getcwd()
        save_folder_path = os.path.join(base_path, "save")
        if not os.path.exists(save_folder_path):
            try:
                os.makedirs(save_folder_path)
                print(f"Created directory: {save_folder_path}")
            except OSError as e:
                print(f"Warning: Could not create {save_folder_path} for initialdir: {e}")
        
        file_path = filedialog.askopenfilename(
            filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")],
            title="盤面の読み込み",
            initialdir=save_folder_path 
        )
        if not file_path: return

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                lines = [line.strip() for line in file]

            self.deck, self.on_board, self.markers = [], [], []
            self.ex_deck = [] 
            self.selected_card = None

            section = None
            resource_lines_from_file = []

            for line_content in lines:
                if not line_content: continue
                if line_content == "[Resource]": section = "resource"; resource_lines_from_file = []; continue
                elif line_content == "[Deck]": section = "deck"; continue
                elif line_content == "[Board]": section = "board"; continue
                elif line_content == "[Markers]": section = "markers"; continue

                if section == "resource":
                    resource_lines_from_file.append(line_content)
                elif section == "deck":
                    self.deck.append(self._create_card_dict(line_content))
                elif section == "board":
                    parts = line_content.split(",")
                    if len(parts) == 6:
                        card_id, x, y, rotated, face_up, revealed = parts
                        self.on_board.append(self._create_card_dict(
                            card_id, int(x), int(y), bool(int(rotated)),
                            bool(int(face_up)), bool(int(revealed))
                        ))
                elif section == "markers":
                    parts = line_content.split(",", 4) 
                    if len(parts) == 5:
                        text, x, y, width, height = parts
                        self.markers.append({
                            "type": "marker", "text": text.replace('\\n', '\n'),
                            "x": int(x), "y": int(y),
                            "width": int(width), "height": int(height),
                            "selected": False, "text_width":0, "text_height":0
                        })
            
            if len(resource_lines_from_file) >= 1:
                 new_rev_path = os.path.join("resource", resource_lines_from_file[0])
                 if new_rev_path != self.reverse_image_path or not self.reverse_image_pil:
                    self.reverse_image_path = new_rev_path
                    try:
                        self.reverse_image_pil = Image.open(self.reverse_image_path).resize((78, 111))
                        self.reverse_photo_image = ImageTk.PhotoImage(self.reverse_image_pil)
                        self.reverse_rotated_image_pil = self.reverse_image_pil.rotate(90, expand=True).resize((111, 78))
                        self.reverse_rotated_photo_image = ImageTk.PhotoImage(self.reverse_rotated_image_pil)
                    except FileNotFoundError: print(f"Loaded board reverse image not found: {self.reverse_image_path}")


            if len(resource_lines_from_file) >= 2:
                new_pm_path = os.path.join("resource", resource_lines_from_file[1])
                if new_pm_path != self.playmat_path or not self.playmat_image_pil:
                    self.playmat_path = new_pm_path
                    try:
                        self.playmat_image_pil = Image.open(self.playmat_path).resize((960, 720))
                        self.playmat_photo = ImageTk.PhotoImage(self.playmat_image_pil)
                    except FileNotFoundError: print(f"Loaded board playmat image not found: {self.playmat_path}")


            self.draw_cards()
            messagebox.showinfo("成功", "盤面を読み込みました！")
        except Exception as e:
            messagebox.showerror("エラー", f"読み込み中にエラーが発生しました:\n{e}")


    def _copy_card_id_to_clipboard(self, event=None):
        if self.selected_card and "id" in self.selected_card: 
            card_id = self.selected_card["id"]
            self.root.clipboard_clear()
            self.root.clipboard_append(card_id)
            self.root.update() 

    def restart_app(self):
        try:
            python = sys.executable
            os.execl(python, python, *sys.argv)
        except Exception as e:
            messagebox.showerror("再起動エラー", f"再起動に失敗しました: {e}")

    def update_deck_count_display(self):
        if hasattr(self, 'deck_count_label') and self.deck_count_label.winfo_exists():
            self.deck_count_label.config(text=f"デッキ: {len(self.deck)}枚")

    # --- Window Openers ---
    def open_info_window(self):
        if self.info_window_instance is None or not self.info_window_instance.is_active():
            self.info_window_instance = InfoWindow(self)
        else:
            self.info_window_instance.lift_window()


    def open_opponent_window(self):
        if self.opponent_window_instance is None or not self.opponent_window_instance.is_active():
            self.opponent_window_instance = OpponentWindow(self)
        else:
            self.opponent_window_instance.lift_window()

    def open_deck_contents_window(self):
        if self.deck_contents_window_instance is None or not self.deck_contents_window_instance.is_active():
            self.deck_contents_window_instance = DeckContentsWindow(self)
        else:
            self.deck_contents_window_instance.lift_window()


    def open_marker_edit_window(self):
        if self.selected_card and self.selected_card.get("type") == "marker":
            if self.marker_edit_window_instance is None or not self.marker_edit_window_instance.is_active():
                self.marker_edit_window_instance = MarkerEditWindow(self, self.selected_card)
            else:
                 self.marker_edit_window_instance.lift_window() 


class InfoWindow:
    def __init__(self, app_ref):
        self.app = app_ref
        self.root = app_ref.root 
        self.window = tk.Toplevel(self.root)
        self.window.title("カード情報ウインドウ")
        self.window.geometry("400x600")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self._disable_close) 

        self.root.update_idletasks()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_w = self.root.winfo_width()
        self.window.geometry(f"400x600+{main_x + main_w}+{main_y}")
        
        self.image_label = tk.Label(self.window, bg="white") 
        self.image_label.pack(expand=True, fill="both")
        self.current_photo_image = None 

        self.update_display()

    def _disable_close(self):
        pass 

    def destroy_window(self): 
        if self.window:
            self.window.destroy()
            self.window = None
            self.app.info_window_instance = None


    def lift_window(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()

    def is_active(self):
        return self.window is not None and self.window.winfo_exists()

    def update_display(self):
        if not self.is_active(): return

        display_photo = None
        display_text = ""

        if self.app.selected_card and "id" in self.app.selected_card: 
            if not self.app.selected_card.get("revealed", False) and self.app.unknown_photo_image:
                display_photo = self.app.unknown_photo_image
            else:
                image_path = os.path.join("card-img", f"{self.app.selected_card['id']}.png")
                try:
                    pil_img = Image.open(image_path).resize((390, 555))
                    display_photo = ImageTk.PhotoImage(pil_img)
                except FileNotFoundError:
                    if self.app.noimage_large_photo_image:
                         display_photo = self.app.noimage_large_photo_image
                    else: 
                         display_text = "画像が見つかりません"
            if display_photo: self.app.last_displayed_image = display_photo


        elif self.app.last_displayed_image: 
            display_photo = self.app.last_displayed_image
        elif self.app.unknown_photo_image: 
             display_photo = self.app.unknown_photo_image 
        else:
             display_text = "有効なカードが選択されていません"


        if display_photo:
            self.image_label.config(image=display_photo, text="")
            self.current_photo_image = display_photo 
        else:
            self.image_label.config(image="", text=display_text, fg="red")
            self.current_photo_image = None


class OpponentWindow:
    def __init__(self, app_ref):
        self.app = app_ref
        self.root = app_ref.root
        self.window = tk.Toplevel(self.root)
        self.window.title("対戦者用ウインドウ")
        self.window.geometry("960x720")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self._disable_close)

        self.root.update_idletasks()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        self.window.geometry(f"960x720+{main_x + 64}+{main_y + 64}")
        self.window.lower()

        self.canvas = tk.Canvas(self.window, width=960, height=720, bg="white")
        self.canvas.pack()

        self.dice_label = tk.Label(self.window, text="", font=("YuGothB.ttc", 24), bg="white")
        
        self.playmat_photo_opponent = None 
        self.card_images_opponent = {} 
        self.marker_layer_opponent_tk = None 

        self.needs_redraw = True 
        self._load_resources()
        self._refresh_view_loop()


    def _load_resources(self):
        if self.app.playmat_image_pil:
            try:
                flipped_playmat_pil = self.app.playmat_image_pil.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_LEFT_RIGHT)
                self.playmat_photo_opponent = ImageTk.PhotoImage(flipped_playmat_pil)
            except Exception as e:
                print(f"Error creating opponent playmat: {e}")
                self.playmat_photo_opponent = None 

    def _disable_close(self):
        pass

    def destroy_window(self):
        if self.window:
            self.window.destroy()
            self.window = None
            self.app.opponent_window_instance = None


    def lift_window(self):
         if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.lower(self.root) 

    def is_active(self):
        return self.window is not None and self.window.winfo_exists()

    def show_dice_result(self, text): 
        if self.is_active():
            self.dice_label.config(text=text)
            self.dice_label.place(relx=0.5, rely=0.5, anchor="center")
    
    def update_dice_text(self, text): 
        if self.is_active():
             self.dice_label.config(text=text)

    def hide_dice_result(self):
        if self.is_active():
            self.dice_label.place_forget()

    def _get_opponent_card_image(self, card_data, is_hidden_hand):
        state_key = f"{card_data['id']}_{card_data.get('rotated',False)}_{card_data.get('face_up',True)}_{is_hidden_hand}"

        if state_key in self.card_images_opponent:
            return self.card_images_opponent[state_key]

        pil_image_to_transform = None
        target_size = (111, 78) if card_data.get('rotated') else (78, 111)

        if is_hidden_hand:
            pil_image_to_transform = self.app.reverse_rotated_image_pil if card_data.get('rotated') else self.app.reverse_image_pil
        elif not card_data.get('face_up', True): 
            pil_image_to_transform = self.app.reverse_rotated_image_pil if card_data.get('rotated') else self.app.reverse_image_pil
        else: 
            source_pil = card_data.get("original_image")
            if source_pil: 
                if card_data.get('rotated'):
                    pil_image_to_transform = source_pil.rotate(90, expand=True).resize(target_size)
                else:
                    pil_image_to_transform = source_pil.resize(target_size)
            elif self.app.noimage_pil: 
                 pil_image_to_transform = self.app.noimage_pil.rotate(90, expand=True).resize(target_size) if card_data.get('rotated') else self.app.noimage_pil.resize(target_size)


        if pil_image_to_transform:
            try:
                transformed_pil = pil_image_to_transform.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_LEFT_RIGHT)
                tk_image = ImageTk.PhotoImage(transformed_pil)
                self.card_images_opponent[state_key] = tk_image 
                return tk_image
            except Exception as e:
                print(f"Error transforming image for opponent: {card_data['id']} - {e}")
        
        return None 

    def _draw_view(self):
        if not self.is_active(): return
        self.canvas.delete("all")

        if self.playmat_photo_opponent:
            self.canvas.create_image(0, 0, image=self.playmat_photo_opponent, anchor="nw")
        
        for card_data in self.app.on_board:
            original_x, original_y = card_data.get("x",0), card_data.get("y",0)
            original_w, original_h = card_data.get("width",78), card_data.get("height",111)

            opp_x = 960 - (original_x + original_w)
            opp_y = 720 - (original_y + original_h)

            is_hidden_in_hand = original_y > 440 
            
            img_to_draw = self._get_opponent_card_image(card_data, is_hidden_in_hand)

            if img_to_draw:
                self.canvas.create_image(opp_x, opp_y, image=img_to_draw, anchor="nw")
        
        if self.app.markers:
            marker_layer_pil_opp = Image.new("RGBA", (self.canvas.winfo_width(), self.canvas.winfo_height()), (255, 255, 255, 0))
            draw_pil_opp = ImageDraw.Draw(marker_layer_pil_opp)
            
            try:
                font_opp = ImageFont.truetype("YuGothB.ttc", 14)
            except IOError:
                font_opp = ImageFont.load_default()

            for marker in self.app.markers:
                ox, oy, ow, oh = marker["x"], marker["y"], marker["width"], marker["height"]
                opp_marker_x = 960 - (ox + ow)
                opp_marker_y = 720 - (oy + oh)

                translucent_color_pil = (128, 128, 128, 128)
                draw_pil_opp.rectangle([opp_marker_x, opp_marker_y, opp_marker_x + ow, opp_marker_y + oh], fill=translucent_color_pil)

                if marker["text"]:
                    draw_text_with_outline(draw_pil_opp, (opp_marker_x, opp_marker_y), marker["text"], font_opp,
                                           "black", "white", 2,
                                           ow, oh, marker["text_width"], marker["text_height"])
            
            self.marker_layer_opponent_tk = ImageTk.PhotoImage(marker_layer_pil_opp)
            self.canvas.create_image(0,0, image=self.marker_layer_opponent_tk, anchor="nw")

        lp_deck_info_pil = Image.new("RGBA", (self.canvas.winfo_width(), self.canvas.winfo_height()), (255,255,255,0))
        draw_info_pil = ImageDraw.Draw(lp_deck_info_pil)
        try:
            font_info = ImageFont.truetype("YuGothB.ttc", 20)
        except IOError:
            font_info = ImageFont.load_default()
        
        lp_text = f"LP: {self.app.life_points.get()}"
        deck_count_text = f"Deck: {len(self.app.deck)}"
        
        lp_text_w, lp_text_h = font_info.getsize(lp_text) if hasattr(font_info, "getsize") else (80, 20)
        deck_text_w, deck_text_h = font_info.getsize(deck_count_text) if hasattr(font_info, "getsize") else (80, 20)

        lp_x_opp = 10 
        lp_y_opp = 20 
        deck_x_opp = 10
        deck_y_opp = lp_y_opp + lp_text_h + 5

        dummy_box_w = max(lp_text_w, deck_text_w) + 20 
        dummy_box_h = lp_text_h 

        draw_text_with_outline(draw_info_pil, (lp_x_opp, lp_y_opp), lp_text, font_info, "Black", "White", 1, 
                               dummy_box_w, dummy_box_h, lp_text_w, lp_text_h)
        draw_text_with_outline(draw_info_pil, (deck_x_opp, deck_y_opp), deck_count_text, font_info, "Black", "White", 1,
                               dummy_box_w, dummy_box_h, deck_text_w, deck_text_h)

        self.lp_deck_info_tk = ImageTk.PhotoImage(lp_deck_info_pil)
        self.canvas.create_image(0,0, image=self.lp_deck_info_tk, anchor="nw")


        self.needs_redraw = False 


    def _refresh_view_loop(self):
        if self.is_active():
            if self.needs_redraw: 
                self._draw_view()
            self.window.after(self.app.opponent_refresh_rate, self._refresh_view_loop)


class DeckContentsWindow:
    def __init__(self, app_ref):
        self.app = app_ref
        self.root = app_ref.root
        self.window = tk.Toplevel(self.root)
        self.window.title("デッキの中身を見る")
        
        self.window.geometry("800x660") 
        center_tk_window(self.root, self.window, 800, 660)

        self.window.protocol("WM_DELETE_WINDOW", self.destroy_window)

        self.card_mapping = self._load_card_list_names() 
        self.current_photo_image = None 

        main_frame = tk.Frame(self.window)
        main_frame.pack(fill="both", expand=True)

        list_frame = tk.Frame(main_frame)
        list_frame.pack(side="left", fill="y", padx=10, pady=10)

        self.listbox = tk.Listbox(list_frame, width=50, height=30) 
        self.listbox.pack(side="left", fill="y")
        
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        for card_data in self.app.deck:
            display_name = self.card_mapping.get(card_data["id"], card_data["id"])
            self.listbox.insert(tk.END, display_name)

        self.listbox.bind("<<ListboxSelect>>", self._show_card_image)

        image_display_frame = tk.Frame(main_frame, width=390, height=555, bg="white") 
        image_display_frame.pack_propagate(False)
        image_display_frame.pack(side="right", padx=10, pady=10, anchor="n")

        self.image_label = tk.Label(image_display_frame, bg="white")
        self.image_label.pack(expand=True, fill="both")

        button_frame = tk.Frame(self.window) 
        button_frame.pack(fill="x", side="bottom", pady=10)
        
        select_button = tk.Button(button_frame, text="選択したカードを出す", command=self._select_card_from_deck)
        select_button.pack() 

        self._show_card_image() 

    def _load_card_list_names(self):
        mapping = {}
        # MODIFIED: Load CardList.csv from script's directory (root)
        card_list_path = "CardList.csv"

        try:
            with open(card_list_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split(",", 2)
                        if len(parts) >= 2: 
                            card_id, display_name = parts[0], parts[1]
                            mapping[card_id] = display_name
        except FileNotFoundError:
            messagebox.showerror("エラー", f"{card_list_path}が見つかりません！", parent=self.window)
        return mapping
    
    def _show_card_image(self, event=None):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            if self.app.deck: 
                first_card_id_in_deck = self.app.deck[0]['id']
                self._display_image_for_id(first_card_id_in_deck)
            else: 
                self.image_label.config(image='', text="カードを選択してください")
                self.current_photo_image = None
            return

        selected_display_name = self.listbox.get(selected_indices[0])
        
        selected_card_id = None
        for c_id, d_name in self.card_mapping.items():
            if d_name == selected_display_name:
                if selected_indices[0] < len(self.app.deck) and self.app.deck[selected_indices[0]]['id'] == c_id:
                     selected_card_id = c_id
                     break
        if not selected_card_id and selected_indices[0] < len(self.app.deck): 
            selected_card_id = self.app.deck[selected_indices[0]]['id']


        if selected_card_id:
            self._display_image_for_id(selected_card_id)
        else:
            self.image_label.config(image='', text="ID不明のカードです")
            self.current_photo_image = None

    def _display_image_for_id(self, card_id):
        image_path = os.path.join("card-img", f"{card_id}.png")
        try:
            pil_img = Image.open(image_path).resize((390, 555))
            self.current_photo_image = ImageTk.PhotoImage(pil_img)
            self.image_label.config(image=self.current_photo_image, text="")
        except FileNotFoundError:
            if self.app.noimage_large_photo_image:
                self.current_photo_image = self.app.noimage_large_photo_image
                self.image_label.config(image=self.current_photo_image, text="")
            else:
                self.image_label.config(image='', text="画像が見つかりません")
                self.current_photo_image = None


    def _select_card_from_deck(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("エラー", "カードを選択してください！", parent=self.window)
            return
        
        selected_listbox_index = selected_indices[0]
        
        if selected_listbox_index < len(self.app.deck):
            card_to_move = self.app.deck.pop(selected_listbox_index) 
            
            card_to_move["x"], card_to_move["y"] = 600, 500 
            card_to_move["face_up"] = True 
            card_to_move["revealed"] = True
            card_to_move["rotated"] = False

            self.app._adjust_card_position(card_to_move)
            self.app.on_board.append(card_to_move)
            self.app.selected_card = card_to_move 
            
            self.app.draw_cards() 
            self.destroy_window() 
        else:
            messagebox.showerror("エラー", "デッキとリストの同期に問題が発生しました。", parent=self.window)


    def destroy_window(self):
        if self.window:
            self.window.destroy()
            self.window = None
        self.app.deck_contents_window_instance = None

    def lift_window(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
    
    def is_active(self):
        return self.window is not None and self.window.winfo_exists()


class MarkerEditWindow:
    def __init__(self, app_ref, marker_ref):
        self.app = app_ref
        self.root = app_ref.root
        self.marker = marker_ref 
        self.window = tk.Toplevel(self.root)
        self.window.title("テキスト編集")

        text_widget_width = 30 
        text_widget_height = 5
        window_width = text_widget_width * 8 + 40 
        window_height = text_widget_height * 20 + 80
        center_tk_window(self.root, self.window, window_width, window_height)

        self.window.protocol("WM_DELETE_WINDOW", self.destroy_window)

        self.text_box = tk.Text(self.window, width=text_widget_width, height=text_widget_height, wrap="word")
        self.text_box.insert(tk.END, self.marker.get("text", ""))
        self.text_box.pack(pady=10, padx=10, expand=True, fill="both")

        save_button = tk.Button(self.window, text="保存", command=self._save_text)
        save_button.pack(pady=5)

        self.text_box.focus_set()


    def _save_text(self):
        new_text = self.text_box.get("1.0", tk.END).strip()
        self.marker["text"] = new_text 
        self.app.draw_cards() 
        self.destroy_window()

    def destroy_window(self):
        if self.window:
            self.window.destroy()
            self.window = None
        self.app.marker_edit_window_instance = None 

    def lift_window(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
    
    def is_active(self):
        return self.window is not None and self.window.winfo_exists()


if __name__ == "__main__":
    main_root = tk.Tk()
    app = ShuffleMyriadApp(main_root)
    main_root.mainloop()
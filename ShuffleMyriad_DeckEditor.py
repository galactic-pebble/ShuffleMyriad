import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import datetime
import random # For Gacha feature

# --- Constants ---
CARD_LIST_CSV = "CardList.csv"
CARD_IMG_DIR = "card-img"
RESOURCE_DIR = "resource"
DECK_DIR = "deck"
DEFAULT_REVERSE_CARD = "reverse.png"
DEFAULT_PLAYMAT = "playmat.png"
NO_IMAGE_FILE = os.path.join(RESOURCE_DIR, "noimage.png")
CARD_PREVIEW_SIZE = (390, 555)

class DeckEditorApp:
    def __init__(self, root_window):
        self.root = root_window
        try:
            self.root.geometry("1280x800")
        except tk.TclError:
             print("初期ウィンドウサイズを設定できませんでした。デフォルトサイズを使用します。") # Japanese

        self.card_definitions = {}
        self.available_cards_display = [] # Now stores (f"{card_id} - {card_name}", card_id)

        self.main_deck = []
        self.ex_deck = []

        self.current_file_path = None
        self.reverse_card_name = tk.StringVar(value=DEFAULT_REVERSE_CARD)
        self.playmat_name = tk.StringVar(value=DEFAULT_PLAYMAT)
        self.unsaved_changes = False

        self._create_missing_dirs()
        self._load_card_definitions()
        self._load_no_image_placeholder()
        self._setup_ui()
        self._update_all_displays()
        self._update_window_title()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)


    def _update_window_title(self):
        base_title_prefix = "ShuffleMyriad デッキエディタ" # Japanese
        file_name_part = os.path.basename(self.current_file_path) if self.current_file_path else "新規デッキ" # Japanese
        unsaved_marker = "*" if self.unsaved_changes else ""
        self.root.title(f"{base_title_prefix} - {file_name_part}{unsaved_marker}")

    def set_unsaved_changes(self, status):
        if self.unsaved_changes == status:
            return
        self.unsaved_changes = status
        self._update_window_title()

    def _create_missing_dirs(self):
        for dir_path in [CARD_IMG_DIR, RESOURCE_DIR, DECK_DIR]:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path)
                    print(f"ディレクトリを作成しました: {dir_path}") # Japanese
                except OSError as e:
                    messagebox.showerror("エラー", f"ディレクトリ {dir_path} を作成できませんでした: {e}") # Japanese

    def _load_no_image_placeholder(self):
        try:
            img = Image.open(NO_IMAGE_FILE)
            img = img.resize(CARD_PREVIEW_SIZE, Image.Resampling.LANCZOS)
            self.no_image_photo = ImageTk.PhotoImage(img)
        except FileNotFoundError:
            self.no_image_photo = None
            print(f"警告: {NO_IMAGE_FILE} が見つかりません。") # Japanese
        except Exception as e:
            self.no_image_photo = None
            print(f"{NO_IMAGE_FILE} の読み込みエラー: {e}") # Japanese

    def _load_card_definitions(self):
        self.card_definitions = {}
        self.available_cards_display = []
        try:
            with open(CARD_LIST_CSV, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(",", 2)
                    if len(parts) >= 2:
                        card_id, card_name = parts[0].strip(), parts[1].strip()
                        ex_type = "0"
                        if len(parts) > 2:
                            val = parts[2].strip()
                            if val == "1":
                                ex_type = "1"

                        self.card_definitions[card_id] = {"name": card_name, "ex": ex_type}
                        self.available_cards_display.append((f"{card_id} - {card_name}", card_id))
                    else:
                        print(f"{CARD_LIST_CSV} 内の不正な行をスキップします: {line}") # Japanese
            self.available_cards_display.sort()
        except FileNotFoundError:
            messagebox.showerror("エラー", f"{CARD_LIST_CSV} が見つかりません！") # Japanese
        except Exception as e:
            messagebox.showerror("エラー", f"{CARD_LIST_CSV} の読み込みエラー: {e}") # Japanese

    def _setup_ui(self):
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="新規デッキ", command=self.new_deck) # Japanese
        filemenu.add_command(label="デッキを開く", command=self.open_deck) # Japanese
        filemenu.add_separator()
        filemenu.add_command(label="デッキを保存", command=self.save_deck) # Japanese
        filemenu.add_command(label="名前を付けてデッキを保存...", command=self.save_deck_as) # Japanese
        filemenu.add_separator()
        filemenu.add_command(label="ガチャデッキ生成 (100枚)", command=self.generate_gacha_deck_action) # Japanese
        filemenu.add_separator()
        filemenu.add_command(label="終了", command=self._on_closing) # Japanese
        menubar.add_cascade(label="ファイル", menu=filemenu) # Japanese
        self.root.config(menu=menubar)

        top_controls_frame = tk.Frame(self.root, pady=5)
        top_controls_frame.pack(fill="x")

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        available_frame = ttk.LabelFrame(main_frame, text="利用可能なカード", padding=5) # Japanese
        available_frame.pack(side="left", fill="both", expand=True, padx=5)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._filter_available_cards())
        search_entry = ttk.Entry(available_frame, textvariable=self.search_var, width=30)
        search_entry.pack(fill="x", pady=(0,5))

        self.available_listbox = tk.Listbox(available_frame, exportselection=False, width=40)
        self.available_listbox.pack(side="left", fill="both", expand=True)
        available_scrollbar = ttk.Scrollbar(available_frame, orient="vertical", command=self.available_listbox.yview)
        available_scrollbar.pack(side="right", fill="y")
        self.available_listbox.config(yscrollcommand=available_scrollbar.set)
        self.available_listbox.bind("<<ListboxSelect>>", lambda e: self._on_listbox_select(self.available_listbox))

        add_buttons_frame = tk.Frame(main_frame, padx=10)
        add_buttons_frame.pack(side="left", fill="y", anchor="center")
        ttk.Button(add_buttons_frame, text="自動追加 >>", command=self._add_auto).pack(pady=5) # Japanese (Changed "Add >>" to "自動追加 >>" for clarity as it auto-determines Main/EX)
        ttk.Button(add_buttons_frame, text="メインに追加 >>", command=self._add_to_main_deck).pack(pady=5) # Japanese
        ttk.Button(add_buttons_frame, text="EXに追加 >>", command=self._add_to_ex_deck).pack(pady=5) # Japanese
        ttk.Button(add_buttons_frame, text="<< 削除", command=self._remove_from_deck).pack(pady=20) # Japanese

        deck_frame = tk.Frame(main_frame)
        deck_frame.pack(side="left", fill="both", expand=True, padx=5)

        main_deck_frame = ttk.LabelFrame(deck_frame, text="メインデッキ (0)", padding=5) # Japanese
        main_deck_frame.pack(fill="both", expand=True, pady=(0,5))
        self.main_deck_label = main_deck_frame
        self.main_deck_listbox = tk.Listbox(main_deck_frame, exportselection=False, width=40)
        self.main_deck_listbox.pack(side="left", fill="both", expand=True)
        main_deck_scrollbar = ttk.Scrollbar(main_deck_frame, orient="vertical", command=self.main_deck_listbox.yview)
        main_deck_scrollbar.pack(side="right", fill="y")
        self.main_deck_listbox.config(yscrollcommand=main_deck_scrollbar.set)
        self.main_deck_listbox.bind("<<ListboxSelect>>", lambda e: self._on_listbox_select(self.main_deck_listbox))
        ttk.Button(main_deck_frame, text="ソート", command=lambda: self._sort_deck(self.main_deck, self.main_deck_listbox)).pack(side="bottom", fill="x", pady=(5,0)) # Japanese


        ex_deck_frame = ttk.LabelFrame(deck_frame, text="EXデッキ (0)", padding=5) # Japanese
        ex_deck_frame.pack(fill="both", expand=True, pady=(5,0))
        self.ex_deck_label = ex_deck_frame
        self.ex_deck_listbox = tk.Listbox(ex_deck_frame, exportselection=False, width=40)
        self.ex_deck_listbox.pack(side="left", fill="both", expand=True)
        ex_deck_scrollbar = ttk.Scrollbar(ex_deck_frame, orient="vertical", command=self.ex_deck_listbox.yview)
        ex_deck_scrollbar.pack(side="right", fill="y")
        self.ex_deck_listbox.config(yscrollcommand=ex_deck_scrollbar.set)
        self.ex_deck_listbox.bind("<<ListboxSelect>>", lambda e: self._on_listbox_select(self.ex_deck_listbox))
        ttk.Button(ex_deck_frame, text="ソート", command=lambda: self._sort_deck(self.ex_deck, self.ex_deck_listbox)).pack(side="bottom", fill="x", pady=(5,0)) # Japanese


        preview_resource_frame = tk.Frame(main_frame, width=CARD_PREVIEW_SIZE[0] + 24, padx=10)
        preview_resource_frame.pack(side="right", fill="y")
        preview_resource_frame.pack_propagate(False)

        self.card_preview_label = ttk.Label(preview_resource_frame, relief="sunken", anchor="center")
        self.card_preview_label.pack(pady=10, fill="x")
        self._update_card_preview(None) # Initialize with placeholder

        ttk.Label(preview_resource_frame, text="裏面カード画像:").pack(anchor="w", pady=(10,0)) # Japanese
        ttk.Entry(preview_resource_frame, textvariable=self.reverse_card_name).pack(fill="x")

        ttk.Label(preview_resource_frame, text="プレイマット画像:").pack(anchor="w", pady=(10,0)) # Japanese
        ttk.Entry(preview_resource_frame, textvariable=self.playmat_name).pack(fill="x")

        self.status_bar = ttk.Label(self.root, text="新規デッキ", relief="sunken", anchor="w", padding=2) # Japanese
        self.status_bar.pack(side="bottom", fill="x")

    def _filter_available_cards(self):
        current_selection_indices = self.available_listbox.curselection()
        selected_text_to_restore = None
        if current_selection_indices:
            selected_text_to_restore = self.available_listbox.get(current_selection_indices[0])

        filter_text = self.search_var.get().lower()
        self.available_listbox.delete(0, tk.END)
        new_selection_index = -1
        current_idx = 0
        for display_text, card_id in self.available_cards_display:
            if filter_text in display_text.lower():
                self.available_listbox.insert(tk.END, display_text)
                if selected_text_to_restore and display_text == selected_text_to_restore:
                    new_selection_index = current_idx
                current_idx +=1

        if new_selection_index != -1:
            self.available_listbox.selection_set(new_selection_index)
            self.available_listbox.see(new_selection_index)

    def _on_listbox_select(self, listbox_widget):
        for lb in [self.available_listbox, self.main_deck_listbox, self.ex_deck_listbox]:
            if lb is not listbox_widget:
                lb.selection_clear(0, tk.END)

        selection_indices = listbox_widget.curselection()
        if not selection_indices:
            self._update_card_preview(None)
            return

        selected_item_text = listbox_widget.get(selection_indices[0])

        card_id = None
        parts = selected_item_text.split(" - ", 1)
        if len(parts) > 0:
            card_id = parts[0]

        self._update_card_preview(card_id)

    def _update_card_preview(self, card_id):
        if not card_id or card_id not in self.card_definitions:
            if self.no_image_photo:
                self.card_preview_label.config(image=self.no_image_photo)
            else:
                self.card_preview_label.config(image='', text="画像なし") # Japanese
            return

        image_path = os.path.join(CARD_IMG_DIR, f"{card_id}.png")
        try:
            img = Image.open(image_path)
            img = img.resize(CARD_PREVIEW_SIZE, Image.Resampling.LANCZOS)
            photo_img = ImageTk.PhotoImage(img)
            self.card_preview_label.image = photo_img
            self.card_preview_label.config(image=photo_img)
        except FileNotFoundError:
            if self.no_image_photo:
                self.card_preview_label.config(image=self.no_image_photo)
            else:
                self.card_preview_label.config(image='', text="画像不明") # Japanese
        except Exception as e:
            print(f"カードID {card_id} のプレビュー読み込みエラー: {e}") # Japanese
            if self.no_image_photo:
                self.card_preview_label.config(image=self.no_image_photo)
            else:
                self.card_preview_label.config(image='', text="読込エラー") # Japanese

    def _update_listbox_from_deck(self, listbox, deck_list_ref):
        listbox.delete(0, tk.END)
        for card_id in deck_list_ref:
            name = self.card_definitions.get(card_id, {}).get("name", "不明なカード") # Japanese
            listbox.insert(tk.END, f"{card_id} - {name}")

    def _update_deck_counts(self):
        self.main_deck_label.config(text=f"メインデッキ ({len(self.main_deck)})") # Japanese
        self.ex_deck_label.config(text=f"EXデッキ ({len(self.ex_deck)})") # Japanese

    def _update_status_bar(self):
        file_name = os.path.basename(self.current_file_path) if self.current_file_path else "新規デッキ" # Japanese
        self.status_bar.config(text=f"{file_name} | メイン: {len(self.main_deck)}, EX: {len(self.ex_deck)}") # Japanese

    def _update_all_displays(self):
        self._filter_available_cards()
        self._update_listbox_from_deck(self.main_deck_listbox, self.main_deck)
        self._update_listbox_from_deck(self.ex_deck_listbox, self.ex_deck)
        self._update_deck_counts()
        self._update_status_bar()
        # Ensure a preview is shown if an item is selected in available_listbox after filtering
        if self.available_listbox.curselection():
             self._on_listbox_select(self.available_listbox)
        elif self.main_deck_listbox.curselection():
             self._on_listbox_select(self.main_deck_listbox)
        elif self.ex_deck_listbox.curselection():
             self._on_listbox_select(self.ex_deck_listbox)
        else:
            self._update_card_preview(None)


    def _get_selected_card_id_from_available(self):
        selection_indices = self.available_listbox.curselection()
        if not selection_indices: return None
        selected_item_text = self.available_listbox.get(selection_indices[0])
        parts = selected_item_text.split(" - ", 1)
        if len(parts) > 0:
            return parts[0]
        return None


    def _add_auto(self):
        card_id = self._get_selected_card_id_from_available()
        if card_id:
            props = self.card_definitions.get(card_id)
            target_deck_list = self.main_deck
            target_listbox = self.main_deck_listbox

            if props and props.get("ex") == "1":
                target_deck_list = self.ex_deck
                target_listbox = self.ex_deck_listbox

            target_deck_list.append(card_id)
            self._update_listbox_from_deck(target_listbox, target_deck_list)
            self._update_deck_counts()
            self._update_status_bar()
            self.set_unsaved_changes(True)

    def _add_to_main_deck(self):
        card_id = self._get_selected_card_id_from_available()
        if card_id:
            self.main_deck.append(card_id)
            self._update_listbox_from_deck(self.main_deck_listbox, self.main_deck)
            self._update_deck_counts()
            self._update_status_bar()
            self.set_unsaved_changes(True)


    def _add_to_ex_deck(self):
        card_id = self._get_selected_card_id_from_available()
        if card_id:
            self.ex_deck.append(card_id)
            self._update_listbox_from_deck(self.ex_deck_listbox, self.ex_deck)
            self._update_deck_counts()
            self._update_status_bar()
            self.set_unsaved_changes(True)

    def _remove_from_deck(self):
        main_sel = self.main_deck_listbox.curselection()
        ex_sel = self.ex_deck_listbox.curselection()

        card_removed_success = False
        removed_from_listbox_widget = None
        deck_list_itself = None
        original_removed_index = -1

        if main_sel:
            original_removed_index = main_sel[0]
            if 0 <= original_removed_index < len(self.main_deck):
                del self.main_deck[original_removed_index]
                card_removed_success = True
                removed_from_listbox_widget = self.main_deck_listbox
                deck_list_itself = self.main_deck
        elif ex_sel:
            original_removed_index = ex_sel[0]
            if 0 <= original_removed_index < len(self.ex_deck):
                del self.ex_deck[original_removed_index]
                card_removed_success = True
                removed_from_listbox_widget = self.ex_deck_listbox
                deck_list_itself = self.ex_deck

        if not card_removed_success:
            messagebox.showwarning("カード削除", "メインデッキまたはEXデッキから有効なカードを選択して削除してください。") # Japanese
            return

        self.set_unsaved_changes(True)
        self._update_listbox_from_deck(removed_from_listbox_widget, deck_list_itself)
        self._update_deck_counts()
        self._update_status_bar()

        new_list_count = len(deck_list_itself)
        if new_list_count > 0:
            new_selection_idx = min(original_removed_index, new_list_count - 1)
            removed_from_listbox_widget.selection_set(new_selection_idx)
            removed_from_listbox_widget.see(new_selection_idx)
            self._on_listbox_select(removed_from_listbox_widget)
        else:
            self._update_card_preview(None)

    def _sort_deck(self, deck_list_ref, listbox_widget):
        if not deck_list_ref:
            return

        current_selection_indices = listbox_widget.curselection()
        selected_card_id_to_restore = None
        if current_selection_indices:
            selected_text = listbox_widget.get(current_selection_indices[0])
            parts = selected_text.split(" - ", 1)
            if len(parts) > 0:
                selected_card_id_to_restore = parts[0]

        deck_list_ref.sort()
        self._update_listbox_from_deck(listbox_widget, deck_list_ref)
        self.set_unsaved_changes(True)

        if selected_card_id_to_restore:
            for i, item_text_in_listbox in enumerate(listbox_widget.get(0, tk.END)):
                listbox_item_parts = item_text_in_listbox.split(" - ", 1)
                if len(listbox_item_parts) > 0 and listbox_item_parts[0] == selected_card_id_to_restore:
                    listbox_widget.selection_set(i)
                    listbox_widget.see(i)
                    self._on_listbox_select(listbox_widget)
                    return

        if listbox_widget.size() > 0:
            listbox_widget.selection_set(0)
            listbox_widget.see(0)
            self._on_listbox_select(listbox_widget)
        else:
            self._update_card_preview(None)


    def new_deck(self):
        if self.unsaved_changes:
            if not messagebox.askyesno("新規デッキ", "未保存の変更があります。変更を破棄して続行しますか？"): # Japanese
                return

        self.main_deck = []
        self.ex_deck = []
        self.current_file_path = None
        self.reverse_card_name.set(DEFAULT_REVERSE_CARD)
        self.playmat_name.set(DEFAULT_PLAYMAT)
        self.set_unsaved_changes(False)
        self._update_all_displays()

    def open_deck(self):
        if self.unsaved_changes:
            if not messagebox.askyesno("デッキを開く", "未保存の変更があります。変更を破棄して続行しますか？"): # Japanese
                return

        file_path = filedialog.askopenfilename(
            title="デッキファイルを開く", # Japanese
            initialdir=DECK_DIR,
            filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")] # Japanese
        )
        if not file_path: return

        try:
            with open(file_path, "r", encoding="utf-8") as f: lines = [line.strip() for line in f]
            new_main_deck, new_ex_deck, resource_lines, current_section = [], [], [], "main"
            for line in lines:
                if not line: continue
                if line == "[EX]": current_section = "ex"
                elif line == "[Resource]": current_section = "resource"
                elif current_section == "main":
                    if line in self.card_definitions: new_main_deck.append(line)
                    else: print(f"警告: メインデッキのカードID '{line}' は {CARD_LIST_CSV} に存在しません。スキップします。") # Japanese
                elif current_section == "ex":
                    if line in self.card_definitions: new_ex_deck.append(line)
                    else: print(f"警告: EXデッキのカードID '{line}' は {CARD_LIST_CSV} に存在しません。スキップします。") # Japanese
                elif current_section == "resource": resource_lines.append(line)

            self.main_deck, self.ex_deck = new_main_deck, new_ex_deck
            self.reverse_card_name.set(resource_lines[0] if len(resource_lines) > 0 else DEFAULT_REVERSE_CARD)
            self.playmat_name.set(resource_lines[1] if len(resource_lines) > 1 else DEFAULT_PLAYMAT)
            self.current_file_path = file_path
            self.set_unsaved_changes(False)
            self._update_all_displays()
            messagebox.showinfo("デッキを開く", "デッキが正常に読み込まれました。") # Japanese
        except Exception as e:
            messagebox.showerror("デッキ読み込みエラー", f"デッキの読み込みに失敗しました: {e}") # Japanese
            # self.set_unsaved_changes(False) # Already false from successful load or should be reset if error occurs before load
            # self._update_all_displays() # Potentially show partially loaded or empty state

    def _perform_save(self, file_path):
        if not file_path: return False
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for card_id in self.main_deck: f.write(f"{card_id}\n")
                if self.ex_deck:
                    f.write("[EX]\n")
                    for card_id in self.ex_deck: f.write(f"{card_id}\n")
                f.write("[Resource]\n")
                f.write(f"{self.reverse_card_name.get() or DEFAULT_REVERSE_CARD}\n")
                f.write(f"{self.playmat_name.get() or DEFAULT_PLAYMAT}\n")
            self.current_file_path = file_path
            self.set_unsaved_changes(False)
            self._update_status_bar()
            messagebox.showinfo("デッキを保存", f"デッキは正常に {file_path} へ保存されました。") # Japanese
            return True
        except Exception as e:
            messagebox.showerror("デッキ保存エラー", f"デッキの保存に失敗しました: {e}") # Japanese
            return False

    def save_deck(self):
        if self.current_file_path:
            return self._perform_save(self.current_file_path)
        else:
            return self.save_deck_as()

    def save_deck_as(self):
        file_path = filedialog.asksaveasfilename(
            title="名前を付けて保存", # Japanese
            initialdir=DECK_DIR,
            defaultextension=".txt",
            initialfile=f"deck_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")] # Japanese
        )
        if file_path:
            return self._perform_save(file_path)
        return False

    def generate_gacha_deck_action(self):
        if self.unsaved_changes:
            if not messagebox.askyesno("ガチャデッキ生成", "未保存の変更があります。変更を破棄して続行しますか？"): # Japanese
                return

        if not self.card_definitions:
            messagebox.showerror("ガチャエラー", f"{CARD_LIST_CSV} からカード定義が読み込まれていません。") # Japanese
            return

        gacha_eligible_cards = [ cid for cid, props in self.card_definitions.items() if props.get("ex") in ["0", "1"]]
        if not gacha_eligible_cards:
            messagebox.showinfo("ガチャデッキ", f"{CARD_LIST_CSV} にガチャ対象カード（EX 0または1）がありません。") # Japanese
            return

        new_main_deck, new_ex_deck = [], []
        temp_gacha_pull = random.choices(gacha_eligible_cards, k=100)
        for card_id in temp_gacha_pull:
            props = self.card_definitions.get(card_id)
            if props and props.get("ex") == "1": new_ex_deck.append(card_id)
            else: new_main_deck.append(card_id)

        new_main_deck.sort(); new_ex_deck.sort()
        self.main_deck, self.ex_deck = new_main_deck, new_ex_deck
        self.current_file_path = None # Gacha deck is a new unsaved deck
        self.reverse_card_name.set(DEFAULT_REVERSE_CARD)
        self.playmat_name.set(DEFAULT_PLAYMAT)
        self.set_unsaved_changes(True)
        self._update_all_displays()
        messagebox.showinfo("ガチャデッキ", "100枚のガチャデッキが正常に生成されました！") # Japanese

    def _on_closing(self):
        if self.unsaved_changes:
            response = messagebox.askyesnocancel("終了", "未保存の変更があります。終了する前に保存しますか？") # Japanese
            if response is True: # Save
                if self.save_deck():
                    self.root.destroy()
                # else: save failed, don't close
            elif response is False: # Don't save
                self.root.destroy()
            # else: Cancel (None), do nothing
        else:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = DeckEditorApp(root)
    root.mainloop()
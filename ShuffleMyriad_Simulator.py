import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
from tkinter import simpledialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import random
import sys
from datetime import datetime
import time

def load_config(config_file="config.txt"):
    """
    Load refresh rate from the config file.
    If the file or the value is invalid, return a default value.
    """
    default_opponent_refresh_rate = 120  # Default refresh rate
    if not os.path.exists(config_file):
        print(f"{config_file} not found. Using default refresh rate: {default_refresh_rate}")
        return default_opponent_refresh_rate

    try:
        with open(config_file, "r") as f:
            for line in f:
                if line.startswith("opponent_refresh_rate"):
                    _, value = line.strip().split("=")
                    return int(value)
    except Exception as e:
        print(f"Error reading {config_file}: {e}. Using default refresh rate: {default_refresh_rate}")
    return default_opponent_refresh_rate

opponent_refresh_rate = load_config()

# メインウィンドウをディスプレイの中央に配置
def center_main_window(root, width, height):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

# メインウィンドウの設定
root = tk.Tk()
root.title("ShuffleMyriad_Simulator")
root.geometry("960x860")
center_main_window(root, 960, 860)
# サイズ変更を無効化
root.resizable(False, False)

# キャンバスの作成
canvas = tk.Canvas(root, width=960, height=720, bg="white")
canvas.pack()

# ゲーム状態を保持する変数
# デッキ
deck = []
# ボード上のカード
on_board = []
# ボード上のマーカー（カードの一種として扱う）
markers = []
# 選択中のカード（通常カードまたはマーカー）
selected_card = None
# ドラッグ状態フラグ
is_dragging = False

playmat_path = os.path.join("resource", "playmat.png")
playmat_image = Image.open(playmat_path).resize((960, 720))
playmat_photo = ImageTk.PhotoImage(playmat_image)  # プレイマット画像の参照を保持

opponent_window = None  # 対戦者用ウインドウの参照を保持する変数
edit_window = None  # 編集ウインドウの参照を保持
deck_window = None  # デッキ内容表示ウィンドウの参照を保持

last_displayed_image = None  # 最後に表示されたカード画像を保持する変数

# リバースボタンの参照
reverse_button = None
bring_to_front_button = None
send_to_back_button = None

# カード裏面の画像の設定
reverse_image_path = os.path.join("resource", "reverse.png")
reverse_image = Image.open(reverse_image_path).resize((78, 111)) if os.path.exists(reverse_image_path) else None
reverse_photo_image = ImageTk.PhotoImage(reverse_image) if reverse_image else None
reverse_rotated_image = reverse_image.rotate(90, expand=True).resize((111, 78)) if reverse_image else None
reverse_rotated_photo_image = ImageTk.PhotoImage(reverse_rotated_image) if reverse_rotated_image else None

noimage_path = os.path.join("resource", "noimage.png")
noimage_image = Image.open(noimage_path).resize((78, 111)) if os.path.exists(noimage_path) else None
noimage_photo_image = ImageTk.PhotoImage(noimage_image) if noimage_image else None
noimage_large_image = noimage_image.resize((390, 555)) if noimage_image else None
noimage_large_photo_image = ImageTk.PhotoImage(noimage_large_image) if noimage_large_image else None

unknown_image_path = os.path.join("resource", "unknown.png")
unknown_image = Image.open(unknown_image_path).resize((390, 555)) if os.path.exists(unknown_image_path) else None
unknown_photo_image = ImageTk.PhotoImage(unknown_image) if unknown_image else None

# デッキ枚数表示ラベルの初期化（グローバル変数として宣言）
deck_count_label = None
info_window = None  # カード情報ウィンドウの参照

# デッキをロードする関数
def load_deck():
    global deck, ex_deck, reverse_image_path, reverse_image, reverse_photo_image, reverse_rotated_image, reverse_rotated_photo_image, playmat_path, playmat_image, playmat_photo
    ex_deck = []  # EXデッキを明示的に初期化

    # 実行ファイルと同じディレクトリを初期ディレクトリに設定
    initial_dir = os.path.dirname(sys.argv[0]) if getattr(sys, 'frozen', False) else os.getcwd()

    file_path = filedialog.askopenfilename(
        title="デッキデータを選択",
        filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")],
        initialdir=initial_dir  # 初期ディレクトリを指定
    )
    if not file_path:
        return
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = [line.strip() for line in file if line.strip()]

            # リソースセクションの解析
            resource_section = None
            if "[Resource]" in lines:
                resource_index = lines.index("[Resource]")
                resource_section = lines[resource_index + 1:]
                lines = lines[:resource_index]  # リソースセクションを削除

            # カード裏面画像とプレイマット画像を設定
            if resource_section and len(resource_section) >= 2:
                reverse_image_path = os.path.join("resource", resource_section[0])
                playmat_path = os.path.join("resource", resource_section[1])
            else:
                reverse_image_path = os.path.join("resource", "reverse.png")
                playmat_path = os.path.join("resource", "playmat.png")

            if os.path.exists(reverse_image_path):
                reverse_image = Image.open(reverse_image_path).resize((78, 111))
                reverse_photo_image = ImageTk.PhotoImage(reverse_image)
                reverse_rotated_image = reverse_image.rotate(90, expand=True).resize((111, 78))
                reverse_rotated_photo_image = ImageTk.PhotoImage(reverse_rotated_image)
            else:
                reverse_image = None
                reverse_photo_image = None
                reverse_rotated_image = None
                reverse_rotated_photo_image = None

            if os.path.exists(playmat_path):
                playmat_image = Image.open(playmat_path).resize((960, 720))
                playmat_photo = ImageTk.PhotoImage(playmat_image)

            # [EX]以降をEXデッキとして扱う
            if "[EX]" in lines:
                ex_index = lines.index("[EX]")
                ex_deck = [
                    {"id": card_id, "width": 78, "height": 111, "rotated": False, "face_up": True, "revealed": True, "image": None, "original_image": None}
                    for card_id in lines[ex_index + 1:]
                ]
                deck = [
                    {"id": card_id, "width": 78, "height": 111, "rotated": False, "face_up": True, "revealed": True, "image": None, "original_image": None}
                    for card_id in lines[:ex_index]
                ]
            else:
                deck = [
                    {"id": card_id, "width": 78, "height": 111, "rotated": False, "face_up": True, "revealed": True, "image": None, "original_image": None}
                    for card_id in lines
                ]

        # 各カードの画像をロード
        for card in deck + ex_deck:
            image_path = os.path.join("card-img", f"{card['id']}.png")
            if os.path.exists(image_path):
                card_image = Image.open(image_path).resize((78, 111))
                card["original_image"] = card_image
                card["image"] = ImageTk.PhotoImage(card_image)
            elif noimage_image:
                card["original_image"] = noimage_image
                card["image"] = noimage_photo_image

        # EXデッキのカードをウィンドウに並べて配置
        x, y = 20, 600  # 初期位置
        for card in ex_deck:
            card["x"], card["y"] = x, y
            x += 15  # 横方向に配置を調整
            if x > 900:  # 横幅が足りなくなったら改行
                x = 20
                y += 10
            on_board.append(card)

        draw_cards()
        update_deck_count_display()  # デッキ枚数表示を更新
        messagebox.showinfo("成功", f"デッキを読み込みました！カード数: {len(deck)}, EXデッキカード数: {len(ex_deck)}")
    except Exception as e:
        messagebox.showerror("エラー", f"デッキの読み込み中にエラーが発生しました:\n{e}")

# デッキをシャッフルする関数
def shuffle_deck():
    global deck
    if not deck:
        messagebox.showinfo("エラー", "デッキが空です！")
        return
    random.shuffle(deck)  # デッキをランダムに並び替え

    dice_label.place(relx=0.5, rely=0.5, anchor="center")
    opponent_dice_label.place(relx=0.5, rely=0.5, anchor="center")
    dice_label.config(text=f"シャッフル")
    opponent_dice_label.config(text=f"シャッフル")

    #messagebox.showinfo("成功", "デッキをシャッフルしました！")

# 指定したカードIDでカードを生成しボードに追加する関数
def select_card_by_id():
    card_id = simpledialog.askstring("カードID入力", "カードIDを入力してください:")
    if not card_id:
        return
    image_path = os.path.join("card-img", f"{card_id}.png")
    if not os.path.exists(image_path):
        messagebox.showinfo("エラー", "指定したIDのカード画像が見つかりません！")
        return
    card_image = Image.open(image_path).resize((78, 111))
    card = {
        "id": card_id,
        "width": 78,
        "height": 111,
        "rotated": False,
        "face_up": True,
        "revealed": True,
        "image": ImageTk.PhotoImage(card_image),
        "original_image": card_image,
        "x": 600,
        "y": 500
    }
    adjust_card_position(card)  # 重なり防止の位置調整
    on_board.append(card)
    draw_cards()

# カードが重ならないように位置を調整する関数
def adjust_card_position(new_card):
    offset_x, offset_y = 10, 2  # 少しずらす量
    overlap = True
    max_attempts = 100  # 無限ループ回避のための最大試行回数
    attempts = 0
    while overlap and attempts < max_attempts:
        overlap = False
        for card in on_board:
            if abs(card["x"] - new_card["x"]) == 0 and abs(card["y"] - new_card["y"]) == 0:
                # カードが重なっている場合、ずらす
                new_card["x"] += offset_x
                new_card["y"] += offset_y
                
                # 画面端に行きすぎた場合、逆方向にずらす
                if new_card["x"] > 960 - new_card["width"]:
                    new_card["x"] -= 2 * offset_x  # X方向を逆に
                    offset_x = -offset_x  # 次のずらし方向を変更
                if new_card["y"] > 720 - new_card["height"]:
                    new_card["y"] -= 2 * offset_y  # Y方向を逆に
                    offset_y = -offset_y  # 次のずらし方向を変更

                # 画面内に収める
                new_card["x"] = min(max(new_card["x"], 0), 960 - new_card["width"])
                new_card["y"] = min(max(new_card["y"], 0), 720 - new_card["height"])
                
                overlap = True
                break  # 重なりが見つかったら次の位置調整へ
        attempts += 1
    if attempts >= max_attempts:
        messagebox.showwarning("警告", "カードの配置に失敗しました。位置調整を停止します。")

def view_deck_contents():
    global deck_window
    if deck_window is not None and tk.Toplevel.winfo_exists(deck_window):
        return

    # カードIDと表示情報のマッピングを作成する関数
    def load_card_list():
        card_mapping = {}
        try:
            with open("CardList.txt", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        card_id, display_name, card_ex = line.split(",", 2)
                        card_mapping[card_id] = display_name
        except FileNotFoundError:
            messagebox.showerror("エラー", "CardList.txtが見つかりません！")
        return card_mapping

    # カードIDと表示情報のマッピングを読み込む
    card_mapping = load_card_list()

    # デッキの中身を表示するための新しいウィンドウを作成
    deck_window = tk.Toplevel(root)
    deck_window.title("デッキの中身を見る")  # ウィンドウタイトルを設定

    # ウィンドウを中央に配置
    center_window(root, deck_window, 800, 660)

    deck_window.geometry("800x660")  # ウィンドウサイズを設定

    # ウィンドウ全体を占めるメインフレームを作成
    main_frame = tk.Frame(deck_window)
    main_frame.pack(fill="both", expand=True)

    # リストボックスと画像ラベルを配置するためのフレームを作成
    frame = tk.Frame(main_frame)
    frame.pack(fill="both", expand=True)

    # デッキ内のカードリストを表示するためのリストボックス
    listbox = tk.Listbox(frame, width=60, height=30)
    listbox.pack(side="left", padx=10, pady=10)  # リストボックスを左側に配置

    # 選択されたカードの画像を表示するためのラベル（固定サイズを設定）
    image_frame = tk.Frame(frame, width=390, height=555, bg="white")
    image_frame.pack_propagate(False)  # サイズ固定のためウィジェットの拡張を無効化
    image_frame.pack(side="right", padx=10, pady=10)  # フレームを右側に配置

    image_label = tk.Label(image_frame, text="", bg="white")
    image_label.pack(expand=True, fill="both")  # ラベルをフレーム内で拡張

    # デッキ内のカード表示名をリストボックスに追加
    for card in deck:
        display_name = card_mapping.get(card["id"], card["id"])  # 表示名を取得、なければIDを使用
        listbox.insert(tk.END, display_name)

    # リストボックスで選択されたカードの画像を表示する関数
    def show_card_image():
        selected_index = listbox.curselection()  # 選択されたカードのインデックスを取得
        if not selected_index:  # カードが選択されていない場合は何もしない
            return
        selected_display_name = listbox.get(selected_index)  # リストボックスから表示名を取得
        selected_card_id = next((card_id for card_id, display_name in card_mapping.items() if display_name == selected_display_name), None)
        if not selected_card_id:
            return
        image_path = os.path.join("card-img", f"{selected_card_id}.png")  # カード画像のパスを作成
        if os.path.exists(image_path):  # 画像が存在する場合
            card_image = Image.open(image_path).resize((390, 555))  # 画像をリサイズ
            photo_image_display = ImageTk.PhotoImage(card_image)  # Tkinter用のPhotoImageに変換
            image_label.config(image=photo_image_display)  # ラベルに画像を設定
            image_label.image = photo_image_display  # 参照を保持してガベージコレクションを防ぐ
        else:
            image_label.config(image="", text="画像が見つかりません")  # 画像が見つからない場合のエラーメッセージ

    # デッキから選択されたカードをボードに移動する関数
    def select_card_from_deck():
        selected_index = listbox.curselection()  # 選択されたカードのインデックスを取得
        if not selected_index:  # カードが選択されていない場合はエラーメッセージを表示
            messagebox.showinfo("エラー", "カードを選択してください！")
            return
        selected_display_name = listbox.get(selected_index)  # リストボックスから表示名を取得
        selected_card_id = next((card_id for card_id, display_name in card_mapping.items() if display_name == selected_display_name), None)
        if not selected_card_id:
            return
        for card in deck:  # デッキ内でカードを検索
            if card["id"] == selected_card_id:
                card["x"], card["y"] = 600, 500  # カードの位置をボード上に設定
                adjust_card_position(card)  # 重なり防止の位置調整
                on_board.append(card)  # カードをボードに追加
                deck.remove(card)  # デッキからカードを削除
                draw_cards()  # ボードを再描画
                update_deck_count_display()  # デッキ枚数表示を更新
                deck_window.destroy()  # ウィンドウを閉じる
                return

    # リストボックスの選択イベントにshow_card_image関数をバインド
    listbox.bind("<<ListboxSelect>>", lambda _: show_card_image())

    # ウィンドウ下部にボタンを配置するためのフレームを作成
    button_frame = tk.Frame(deck_window)
    button_frame.pack(fill="x", side="bottom", pady=10)  # ボタンフレームを下部に配置

    # デッキから選択されたカードをボードに移動するボタン
    select_button = tk.Button(button_frame, text="選択したカードを出す", command=select_card_from_deck)
    select_button.pack()  # ボタンをボタンフレームに追加

def add_marker():
    marker = {
        "type": "marker",
        "x": canvas.winfo_width() // 2 - 60,  # キャンバスの中央 (幅の半分 - マーカーの半分)
        "y": int(canvas.winfo_height() * 0.9),  # キャンバスの下の方 (高さの90%の位置)
        "width": 120,
        "height": 50,
        "text": "",
        "selected": False
    }
    markers.append(marker)
    draw_cards()

def create_translucent_rectangle(width, height, color, alpha):
    image = Image.new("RGBA", (width, height), (255, 255, 255, 0))  # 透明な背景
    draw = ImageDraw.Draw(image)
    draw.rectangle([(0, 0), (width, height)], fill=(*color, alpha))  # RGBAで塗りつぶし
    return ImageTk.PhotoImage(image)

def draw_text_with_outline(draw, position, text, font, text_color, outline_color, outline_width, marker_width, marker_height, text_width, text_height):
    """
    マーカーの中心に文字列を描画し、縁取りを加える。

    引数:
    - draw: ImageDrawオブジェクト（Pillowの描画用オブジェクト）
    - position: マーカーの左上座標 (x, y) を格納したタプル
    - text: 描画する文字列
    - font: 使用するフォントオブジェクト
    - text_color: テキストの色
    - outline_color: 縁取りの色
    - outline_width: 縁取りの太さ（ピクセル単位）
    - marker_width: マーカーの幅
    - marker_height: マーカーの高さ
    """
    x, y = position

    # 中心位置を計算
    text_x = x + (marker_width - text_width) // 2
    text_y = y + (marker_height - text_height) // 2 - 2

    # 縁取りを描画
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:  # 中心を除外
                draw.text((text_x + dx, text_y + dy), text, font=font, fill=outline_color)

    # 中央に本来のテキストを描画
    draw.text((text_x, text_y), text, font=font, fill=text_color)

# ボード上のカードを描画する関数
def draw_cards():
    global reverse_button, bring_to_front_button, send_to_back_button, playmat_photo, selected_card
    canvas.delete("all")  # キャンバスをクリア
    # プレイマット画像を背景に描画
    if playmat_photo:
        canvas.create_image(0, 0, image=playmat_photo, anchor="nw")
        canvas.playmat_photo = playmat_photo  # 参照を保持してガベージコレクションを防ぐ

    # カードの描画
    for card in on_board:
        # カードの位置とサイズを取得
        x, y, w, h = max(0, min(card.get("x", 0), 960 - card.get("width", 78))), max(0, min(card.get("y", 0), 720 - card.get("height", 111))), card.get("width", 78), card.get("height", 111)
        card["x"], card["y"] = x, y
        # 表向きかどうかで描画内容を変更
        if card.get("face_up", True):
            if card.get("original_image"):
                if card.get("rotated"):
                    # 横向き（回転状態）のカードを描画
                    rotated_image = card["original_image"].rotate(90, expand=True).resize((111, 78))
                    card["image"] = ImageTk.PhotoImage(rotated_image)
                    card["width"], card["height"] = 111, 78
                else:
                    # 通常のカードを描画
                    card["image"] = ImageTk.PhotoImage(card["original_image"].resize((78, 111)))
                    card["width"], card["height"] = 78, 111
                canvas.create_image(x, y, image=card["image"], anchor="nw")
        else:
            # 裏向きのカードを描画
            if card.get("rotated"):
                if reverse_rotated_photo_image:
                    canvas.create_image(x, y, image=reverse_rotated_photo_image, anchor="nw")
                    card["width"], card["height"] = 111, 78
            else:
                if reverse_photo_image:
                    canvas.create_image(x, y, image=reverse_photo_image, anchor="nw")
                    card["width"], card["height"] = 78, 111
        # 選択中のカードを強調表示
        if card == selected_card:
            canvas.create_rectangle(x, y, x + card["width"], y + card["height"], outline="red", width=3)

    # ボタンの再配置（選択中のカード用）
    if reverse_button:
        reverse_button.place_forget()
    if bring_to_front_button:
        bring_to_front_button.place_forget()
    if send_to_back_button:
        send_to_back_button.place_forget()
    
    # 選択中のカードがマーカーでない場合にのみボタンを表示
    if selected_card and selected_card not in markers and is_dragging == False:
        reverse_button = tk.Button(root, text="リバース", command=reverse_card)
        bring_to_front_button = tk.Button(root, text="最前面", command=bring_to_front)
        send_to_back_button = tk.Button(root, text="最背面", command=send_to_back)

        button_x = selected_card["x"] + selected_card["width"] // 2 - 22
        button_y = selected_card["y"] + selected_card["height"] + 5

        reverse_button.place(x=button_x, y=button_y)
        bring_to_front_button.place(x=button_x - 50, y=button_y)
        send_to_back_button.place(x=button_x + 50, y=button_y)

    # Pillow用の背景画像を作成
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()
    background = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 0))

    draw = ImageDraw.Draw(background)

    for marker in markers:
        if marker["text"]:
            # 一時的なテキスト描画オブジェクトを作成
            bbox = draw.textbbox((0, 0), marker["text"], font=ImageFont.truetype("YuGothB", 14))
            if bbox:  # テキストのサイズ計算が正常に行えた場合
                marker["text_width"] = bbox[2] - bbox[0]
                marker["text_height"] = bbox[3] - bbox[1]
                marker["width"] = max(marker["text_width"] + 20, 120)  # 最小幅を設定
                marker["height"] = max(marker["text_height"] + 10, 50)  # 最小高さを設定
            else:
                # テキストのバウンディングボックスが計算できない場合はデフォルトサイズを設定
                marker["width"] = 120
                marker["height"] = 50
        x, y, w, h = marker["x"], marker["y"], marker["width"], marker["height"]

        # マーカーの背景を描画
        translucent_color = (128, 128, 128, 128)  # 灰色の半透明
        draw.rectangle([x, y, x + w, y + h], fill=translucent_color)

        # マーカーのテキストを描画
        outline_width = 2
        if marker["text"]:
            draw_text_with_outline(draw, (x, y), marker["text"],
                                   font=ImageFont.truetype("YuGothB.ttc", 14),
                                   text_color="black", outline_color="white",
                                   outline_width=outline_width,
                                   marker_width=w,  # キーワード引数
                                   marker_height=h,  # キーワード引数
                                   text_width=marker["text_width"], text_height=marker["text_height"]
                                   )
        if marker == selected_card:
            canvas.create_rectangle(x, y, x + w, y + h, outline="red", width=3)

    # Pillow画像をTkinterキャンバスに表示
    background_photo = ImageTk.PhotoImage(background)
    canvas.create_image(0, 0, image=background_photo, anchor="nw")
    canvas.photo_image = background_photo  # 参照を保持してガベージコレクションを防ぐ

def update_info_display():
    global last_displayed_image
    for widget in info_window.winfo_children():
        widget.destroy()
    if selected_card and "id" in selected_card:
        if not selected_card.get("revealed", False):  # 表示されていない場合
            image_path = os.path.join("resource", "unknown.png")
        else:
            image_path = os.path.join("card-img", f"{selected_card['id']}.png")
        if os.path.exists(image_path):
            image_display = Image.open(image_path).resize((390, 555))
            photo_image_display = ImageTk.PhotoImage(image_display)
            last_displayed_image = photo_image_display  # 現在の画像を保持
            label = tk.Label(info_window, image=photo_image_display)
            label.photo = photo_image_display
            label.pack()
        else:
            tk.Label(info_window, text="画像が見つかりません", fg="red").pack()
    elif last_displayed_image:
        # 最後に表示した画像を表示
        label = tk.Label(info_window, image=last_displayed_image)
        label.photo = last_displayed_image
        label.pack()
    else:
        tk.Label(info_window, text="有効なカードが選択されていません", fg="red").pack()
            
def select_card(event):
    root.focus()
    dice_label_forget()
    global selected_card, is_dragging, drag_offset_x, drag_offset_y
    for marker in reversed(markers):
        if marker["x"] < event.x < marker["x"] + marker["width"] and marker["y"] < event.y < marker["y"] + marker["height"]:
            selected_card = marker
            is_dragging = True
            drag_offset_x = event.x - marker["x"]
            drag_offset_y = event.y - marker["y"]
            draw_cards()
            update_info_display()  # 情報ウィンドウを更新
            return
    for card in reversed(on_board):
        if card["x"] < event.x < card["x"] + card["width"] and card["y"] < event.y < card["y"] + card["height"]:
            selected_card = card
            is_dragging = True
            drag_offset_x = event.x - card["x"]
            drag_offset_y = event.y - card["y"]
            draw_cards()
            update_info_display()  # 情報ウィンドウを更新
            return
    selected_card = None
    is_dragging = False
    drag_offset_x = None
    drag_offset_y = None
    update_info_display()  # 選択が解除された場合も情報ウィンドウを更新

def move_card(event):
    global selected_card, drag_offset_x, drag_offset_y
    if selected_card and is_dragging and drag_offset_x is not None and drag_offset_y is not None:
        selected_card["x"] = event.x - drag_offset_x
        selected_card["y"] = event.y - drag_offset_y
        draw_cards()

def release_card(event):
    global is_dragging
    is_dragging = False
    draw_cards()

def edit_marker_text():
    global edit_window
    if edit_window is not None and tk.Toplevel.winfo_exists(edit_window):
        # 編集ウインドウが既に存在している場合
        return
    if selected_card and selected_card.get("type") == "marker":
        edit_window = tk.Toplevel(root)
        edit_window.title("テキスト編集")

        # 適切なサイズのウィンドウに調整
        text_width = 30
        text_height = 5
        window_width = text_width * 8 + 10  # 文字幅×8 + 余白
        window_height = text_height * 20 + 30  # 行数×20 + ボタンと余白
        center_window(root, edit_window, window_width, window_height)

        text_box = tk.Text(edit_window, width=text_width, height=text_height)
        text_box.insert(tk.END, selected_card["text"])
        text_box.pack(pady=10)

        def save_text():
            global edit_window
            new_text = text_box.get("1.0", tk.END).strip()
            if new_text:
                selected_card["text"] = new_text
            if edit_window is not None:
                edit_window.destroy()
                edit_window = None
            draw_cards()

        save_button = tk.Button(edit_window, text="保存", command=save_text)
        save_button.pack()

        # ウインドウを閉じる際に参照をリセット
        def on_close():
            global edit_window
            if edit_window is not None:  # Noneチェックを追加
                edit_window.destroy()
                edit_window = None

        edit_window.protocol("WM_DELETE_WINDOW", on_close)
        
def rotate_card():
    if not selected_card:
        messagebox.showinfo("エラー", "カードを選択してください！")
        return
    if selected_card["rotated"]:
        selected_card["x"] = selected_card["x"] + 16
        selected_card["y"] = selected_card["y"] - 16
    else:
        selected_card["x"] = selected_card["x"] - 16
        selected_card["y"] = selected_card["y"] + 16
    selected_card["rotated"] = not selected_card["rotated"]
    draw_cards()

def right_click(event):
    global selected_card
    for card in reversed(on_board):
        if card["x"] < event.x < card["x"] + card["width"] and card["y"] < event.y < card["y"] + card["height"]:
            selected_card = card
            if selected_card["rotated"]:
                selected_card["x"] = selected_card["x"] + 16
                selected_card["y"] = selected_card["y"] - 16
            else:
                selected_card["x"] = selected_card["x"] - 16
                selected_card["y"] = selected_card["y"] + 16
            selected_card["rotated"] = not selected_card["rotated"]
            draw_cards()
            return

def reverse_card():
    if not selected_card:
        messagebox.showinfo("エラー", "カードを選択してください！")
        return
    selected_card["face_up"] = not selected_card["face_up"]
    if selected_card["face_up"]:  # 表向きになった場合
        selected_card["revealed"] = True
    draw_cards()
    update_info_display()

def bring_to_front():
    if not selected_card:
        messagebox.showinfo("エラー", "カードを選択してください！")
        return
    on_board.remove(selected_card)
    on_board.append(selected_card)
    draw_cards()

def send_to_back():
    if not selected_card:
        messagebox.showinfo("エラー", "カードを選択してください！")
        return
    on_board.remove(selected_card)
    on_board.insert(0, selected_card)
    draw_cards()

def move_to_deck_top():
    global selected_card
    if not selected_card:
        messagebox.showinfo("エラー", "カードを選択してください！")
        return
    on_board.remove(selected_card)
    deck.insert(0, selected_card)
    selected_card = None
    draw_cards()
    update_deck_count_display()  # デッキ枚数表示を更新

def move_to_deck_bottom():
    global selected_card
    if not selected_card:
        messagebox.showinfo("エラー", "カードを選択してください！")
        return
    on_board.remove(selected_card)
    deck.append(selected_card)
    selected_card = None
    draw_cards()
    update_deck_count_display()  # デッキ枚数表示を更新

def unrotate_all():
    for card in on_board:
        if card["rotated"] == True:
            card["rotated"] = False
            card["x"] = card["x"] + 16
            card["y"] = card["y"] - 16
    draw_cards()

def draw_from_deck(face_up=True, x=600, y=500):
    global selected_card
    if not deck:
        messagebox.showinfo("デッキ", "デッキにカードがありません！")
        return
    card = deck.pop(0)
    card["x"] = x
    card["y"] = y
    card["rotated"] = False
    card["face_up"] = face_up
    card["revealed"] = face_up  # 表向きの場合のみ revealed を True に
    adjust_card_position(card)  # 重なり防止の位置調整
    on_board.append(card)
    selected_card = card
    draw_cards()
    update_deck_count_display()  # デッキ枚数表示を更新
    update_info_display()

# 対戦者用ウインドウを開く関数
def open_opponent_window():
    global opponent_window
    if opponent_window is not None and tk.Toplevel.winfo_exists(opponent_window):
        return
    
    opponent_window = tk.Toplevel(root)  # 新しいウインドウを作成
    opponent_window.title("対戦者用ウインドウ")  # ウィンドウのタイトルを設定
    opponent_window.geometry("960x720")  # ウィンドウサイズを設定

    # サイズ変更を無効化
    opponent_window.resizable(False, False)

    def disable_close():
        pass  # 何もしないことで閉じる操作を無効化
    info_window.protocol("WM_DELETE_WINDOW", disable_close)

    # 対戦者用ウィンドウをメインウィンドウの背面に表示
    x = root.winfo_x() + 64
    y = root.winfo_y() + 64
    opponent_window.geometry(f"960x720+{x}+{y}")
    opponent_window.lower()  # 背面に移動

    global playmat_path, playmat_image, playmat_photo_opponent, opponent_dice_label
    playmat_photo_opponent = None  # プレイマット画像の参照を保持

    # キャンバスを作成
    opponent_canvas = tk.Canvas(opponent_window, width=960, height=720, bg="white")  # キャンバスを作成
    opponent_canvas.pack()  # キャンバスをウィンドウに配置

    opponent_dice_label = tk.Label(opponent_window, text="", font=("YuGothB.ttc", 24), bg="white")

    # 対戦者用ビューを描画する関数
    def draw_opponent_view():
        # プレイマット画像の読み込みと描画
        opponent_canvas.delete("all")  # キャンバスをクリア
        global playmat_photo_opponent  # グローバル変数を宣言
        if playmat_path:
            if os.path.exists(playmat_path):  # 画像ファイルが存在するか確認
                playmat_image = Image.open(playmat_path).resize((960, 720))  # 画像を開き、リサイズ
                playmat_image = playmat_image.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_LEFT_RIGHT)  # 画像を反転
                playmat_photo_opponent = ImageTk.PhotoImage(playmat_image)  # PhotoImageに変換
                opponent_canvas.create_image(0, 0, image=playmat_photo_opponent, anchor="nw")  # プレイマット画像を描画
#            else:
#        else:
        if playmat_photo_opponent:  # プレイマット画像がある場合、それを背景として描画
            opponent_canvas.create_image(0, 0, image=playmat_photo_opponent, anchor="nw")
        for card in on_board:  # ボード上のカードをすべて描画
            # カードの座標を反転（相手側から見た座標）
            x, y = 960 - (card.get("x", 0) + card.get("width", 0)), 720 - (card.get("y", 0) + card.get("height", 0))
            if card.get("y", 0) > 440:  # y座標が440より下の場合、裏向きにする
                if card.get("rotated") and reverse_rotated_image:
                    # 横向きで裏向きの画像を生成して描画
                    reversed_image = reverse_rotated_image.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_LEFT_RIGHT)
                    reversed_photo = ImageTk.PhotoImage(reversed_image)
                    opponent_canvas.create_image(x, y, image=reversed_photo, anchor="nw")
                    card["opponent_image"] = reversed_photo  # 画像参照を保持
                elif reverse_image:
                    # 通常の裏向き画像を生成して描画
                    reversed_image = reverse_image.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_LEFT_RIGHT)
                    reversed_photo = ImageTk.PhotoImage(reversed_image)
                    opponent_canvas.create_image(x, y, image=reversed_photo, anchor="nw")
                    card["opponent_image"] = reversed_photo  # 画像参照を保持
            else:
                # メインウインドウと同じ表裏状態で描画
                if card.get("face_up", True):  # 表向きの場合
                    if card.get("rotated") and card.get("original_image"):
                        # 横向きの画像を生成して描画
                        rotated_image = card["original_image"].rotate(90, expand=True).resize((111, 78))
                        rotated_photo = ImageTk.PhotoImage(rotated_image.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_LEFT_RIGHT))
                        opponent_canvas.create_image(x, y, image=rotated_photo, anchor="nw")
                        card["opponent_image"] = rotated_photo
                    elif card.get("original_image"):
                        # 通常の画像を生成して描画
                        normal_image = card["original_image"].resize((78, 111))
                        normal_photo = ImageTk.PhotoImage(normal_image.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_LEFT_RIGHT))
                        opponent_canvas.create_image(x, y, image=normal_photo, anchor="nw")
                        card["opponent_image"] = normal_photo
                else:  # 裏向きの場合
                    if card.get("rotated") and reverse_rotated_photo_image:
                        # 横向きの裏向き画像を描画
                        reversed_image = reverse_rotated_image.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_LEFT_RIGHT)
                        reversed_photo = ImageTk.PhotoImage(reversed_image)
                        opponent_canvas.create_image(x, y, image=reversed_photo, anchor="nw")
                        card["opponent_image"] = reversed_photo
                    elif reverse_photo_image:
                        # 通常の裏向き画像を描画
                        reversed_image = reverse_image.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_LEFT_RIGHT)
                        reversed_photo = ImageTk.PhotoImage(reversed_image)
                        opponent_canvas.create_image(x, y, image=reversed_photo, anchor="nw")
                        card["opponent_image"] = reversed_photo
        # マーカーの描画
        # Pillow用の背景画像を作成
        opponent_canvas_width = opponent_canvas.winfo_width()
        opponent_canvas_height = opponent_canvas.winfo_height()
        opponent_background = Image.new("RGBA", (opponent_canvas_width, opponent_canvas_height), (255, 255, 255, 0))

        draw = ImageDraw.Draw(opponent_background)

        for marker in markers:
            x, y = 960 - (marker["x"] + marker["width"]), 720 - (marker["y"] + marker["height"])
            w, h = marker["width"], marker["height"]

            # マーカーの背景を描画
            translucent_color = (128, 128, 128, 128)  # 灰色の半透明
            draw.rectangle([x, y, x + w, y + h], fill=translucent_color)

            # マーカーのテキストを描画
            outline_width = 2
            if marker["text"]:
                draw_text_with_outline(draw, (x, y), marker["text"],
                                       font=ImageFont.truetype("YuGothB.ttc", 14),
                                       text_color="black", outline_color="white",
                                       outline_width=outline_width,
                                       marker_width=w,  # キーワード引数
                                       marker_height=h,  # キーワード引数
                                       text_width=marker["text_width"], text_height=marker["text_height"]
                                       )

        # Pillow画像をTkinterキャンバスに表示
        opponent_background_photo = ImageTk.PhotoImage(opponent_background)
        opponent_canvas.create_image(0, 0, image=opponent_background_photo, anchor="nw")
        opponent_canvas.photo_image = opponent_background_photo  # 参照を保持してガベージコレクションを防ぐ

        # ライフポイントを描画
        try:
            font = ImageFont.truetype("YuGothB.ttc", 20)
        except IOError:
            font = ImageFont.load_default()

        try:
            life_points_value = life_points.get()
        except tk.TclError:
            life_points_value = 0  # デフォルト値を設定

        text = f"LP: {life_points.get()}"
        draw_text_with_outline(draw, (opponent_canvas_width - 100, 20), text, font, "Black", "White", 1, 40, 20, 40, 20)
        text = f"Deck: {len(deck)}"
        draw_text_with_outline(draw, (opponent_canvas_width - 100, 55), text, font, "Black", "White", 1, 40, 20, 40, 20)

        # Pillow画像をTkinterキャンバスに描画
        opponent_background_photo = ImageTk.PhotoImage(opponent_background)
        opponent_canvas.create_image(0, 0, image=opponent_background_photo, anchor="nw")
        opponent_canvas.photo_image = opponent_background_photo  # 参照を保持してガベージコレクションを防ぐ

    # ビューを定期的に更新
    def refresh_opponent_view():
        draw_opponent_view()  # ビューを描画
        opponent_window.after(opponent_refresh_rate, refresh_opponent_view)  #再描画

    refresh_opponent_view()  # 最初の更新を実行

def open_info_window():
    global info_window
    if info_window is not None and tk.Toplevel.winfo_exists(info_window):
        return
    info_window = tk.Toplevel(root)
    info_window.title("カード情報ウインドウ")
    info_window.geometry("400x600")

    # サイズ変更を無効化
    info_window.resizable(False, False)

    def disable_close():
        pass  # 何もしないことで閉じる操作を無効化
    info_window.protocol("WM_DELETE_WINDOW", disable_close)

    # カード情報ウィンドウをメインウィンドウの右に配置
    x = root.winfo_x() + root.winfo_width()
    y = root.winfo_y()
    info_window.geometry(f"400x600+{x}+{y}")

    update_info_display()

def delete_card(event=None):
    global selected_card
    if selected_card:
        if selected_card in on_board:
            on_board.remove(selected_card)
        elif selected_card in markers:
            markers.remove(selected_card)
#        else:
#            messagebox.showinfo("エラー", "選択されたオブジェクトが見つかりません！")
        selected_card = None
        draw_cards()
#    else:
#        messagebox.showinfo("エラー", "削除するオブジェクトが選択されていません！")
        
def center_window(parent, window, width, height):
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")
    
def gacha_deck_making():

    def load_card_list():
        card_mapping = {}
        try:
            with open("CardList.txt", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        card_id, display_name, card_ex = line.split(",", 2)
                        card_mapping[card_id] = card_ex
        except FileNotFoundError:
            messagebox.showerror("エラー", "CardList.txtが見つかりません！")
        return card_mapping

    # カードリストをロード
    card_mapping = load_card_list()

    if not card_mapping:
        messagebox.showerror("エラー", "カードリストが空です。処理を終了します。")
        return

    # カードIDをリスト化
    card_ids = list(card_mapping.keys())

    # 100回分の抽選を実施
    gacha_selected_cards = [random.choice(card_ids) for _ in range(100)]

    # EX値が2以上のカードを再抽選
    for i, card_id in enumerate(gacha_selected_cards):
        while int(card_mapping[card_id]) >= 2:
            card_id = random.choice(card_ids)  # 再抽選
            gacha_selected_cards[i] = card_id

    # EX値でカードを分類
    ex_0 = [card_id for card_id in gacha_selected_cards if card_mapping[card_id] == "0"]
    ex_1 = [card_id for card_id in gacha_selected_cards if card_mapping[card_id] == "1"]

    # ID順にソート
    ex_0_sorted = sorted(ex_0)  # ID順にソート
    ex_1_sorted = sorted(ex_1)

    # テキストファイルを生成
    output_filename = f"gacha_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            # EXが0のデータをID順に追記
            for card_id in ex_0_sorted:
                f.write(f"{card_id}\n")

            # [EX]を追記
            f.write("[EX]\n")

            # EXが1のデータをID順に追記
            for card_id in ex_1_sorted:
                f.write(f"{card_id}\n")

            # [Resource]と画像ファイル名を追記
            f.write("[Resource]\n")
            f.write("reverse.png\n")
            f.write("playmat.png\n")

        messagebox.showinfo("成功", f"{output_filename} に正常にデッキが出力されました。")
    except Exception as e:
        messagebox.showerror("エラー", f"ファイルの書き込み中に問題が発生しました: {e}")
        
def dice_label_forget():
    dice_label.place_forget()  # ラベルを非表示にする
    opponent_dice_label.place_forget()  # ラベルを非表示にする
    
def roll_dice():
    global selected_card
    selected_card = None
    draw_cards()
    if dice_label.winfo_ismapped():
        dice_label_forget()  # ラベルを非表示にする
    else:
        result = random.randint(1, 6)
        display_dice_result(result)

def display_dice_result(result):
    """中央に結果を表示し、アニメーション的に文字列を更新する"""
    def update_text_dice(index):
        if index < len(messages):
            dice_label.config(text=messages[index])
            opponent_dice_label.config(text=messages[index])
            root.after(100, update_text_dice, index + 1)
        else:
            dice_label.config(text=f"1D6... {result}")
            opponent_dice_label.config(text=f"1D6... {result}")

    messages = ["1D6", "1D6.", "1D6..", "1D6..."]
    dice_label.place(relx=0.5, rely=0.5, anchor="center")
    opponent_dice_label.place(relx=0.5, rely=0.5, anchor="center")
    update_text_dice(0)
    
def coin_toss():
    global selected_card
    selected_card = None
    draw_cards()
    if dice_label.winfo_ismapped():
        dice_label_forget()  # ラベルを非表示にする
    else:
        result = random.randint(1, 2)
        if result == 1:
            result = "表"
        else:
            result = "裏"
        display_coin_result(result)

def display_coin_result(result):
    """中央に結果を表示し、アニメーション的に文字列を更新する"""
    def update_text_coin(index):
        if index < len(messages):
            dice_label.config(text=messages[index])
            opponent_dice_label.config(text=messages[index])
            root.after(100, update_text_coin, index + 1)
        else:
            dice_label.config(text=f"コイントス... {result}")
            opponent_dice_label.config(text=f"コイントス... {result}")

    messages = ["コイントス", "コイントス.", "コイントス..", "コイントス..."]
    dice_label.place(relx=0.5, rely=0.5, anchor="center")
    opponent_dice_label.place(relx=0.5, rely=0.5, anchor="center")
    update_text_coin(0)
    
# ラベルの作成（結果表示用）
dice_label = tk.Label(root, text="", font=("YuGothB.ttc", 24), bg="white")

def save_board():
    from datetime import datetime
    output_filename = f"save_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"  # 自動生成ファイル名

    try:
        with open(output_filename, "w", encoding="utf-8") as file:
            # リソース情報の保存
            file.write("[Resource]\n")

            # reverse_image_path を相対パスで保存
            reverse_relative_path = os.path.relpath(reverse_image_path, "resource") if reverse_image_path else "reverse.png"
            file.write(f"{reverse_relative_path}\n")

            # playmat_path を相対パスで保存
            playmat_relative_path = os.path.relpath(playmat_path, "resource") if playmat_path else "playmat.png"
            file.write(f"{playmat_relative_path}\n")

            # デッキ情報の保存
            file.write("[Deck]\n")
            for card in deck:
                file.write(f"{card['id']}\n")

            # ボード上のカード情報の保存
            file.write("[Board]\n")
            for card in on_board:
                file.write(
                    f"{card['id']},{card['x']},{card['y']},{int(card['rotated'])},{int(card['face_up'])},{int(card['revealed'])}\n"
                )

            # マーカー情報の保存
            file.write("[Markers]\n")
            for marker in markers:
                file.write(
                    f"{marker['text'].replace('\n', '\\n')},{marker['x']},{marker['y']},{marker['width']},{marker['height']}\n"
                )

        messagebox.showinfo("成功", f"盤面を保存しました！\nファイル名: {output_filename}")
    except Exception as e:
        messagebox.showerror("エラー", f"保存中にエラーが発生しました:\n{e}")

def load_board():
    global deck, on_board, markers
    global reverse_image_path, playmat_path, reverse_image, reverse_photo_image, reverse_rotated_image, reverse_rotated_photo_image, playmat_image, playmat_photo

    file_path = filedialog.askopenfilename(
        filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")],
        title="盤面の読み込み"
    )
    if not file_path:
        return

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        # 初期化
        deck = []
        on_board = []
        markers = []

        section = None
        resource_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue  # 空白行をスキップ

            if line == "[Resource]":
                section = "resource"
                resource_lines = []  # リソースセクションの内容を初期化
                continue
            elif line == "[Deck]":
                section = "deck"
                continue
            elif line == "[Board]":
                section = "board"
                continue
            elif line == "[Markers]":
                section = "markers"
                continue

            # セクションごとの処理
            if section == "resource":
                resource_lines.append(line)  # リソースセクションの内容を収集
            elif section == "deck":
                deck.append({"id": line, "width": 78, "height": 111, "rotated": False, "face_up": True, "revealed": True, "image": None, "original_image": None})
            elif section == "board":
                card_id, x, y, rotated, face_up, revealed = line.split(",")
                on_board.append({
                    "id": card_id,
                    "x": int(x),
                    "y": int(y),
                    "rotated": bool(int(rotated)),
                    "face_up": bool(int(face_up)),
                    "revealed": bool(int(revealed)),
                    "width": 78 if not bool(int(rotated)) else 111,
                    "height": 111 if not bool(int(rotated)) else 78,
                    "image": None,
                    "original_image": None
                })
            elif section == "markers":
                text, x, y, width, height = line.split(",")
                markers.append({
                    "type": "marker",
                    "text": text.replace('\\n', '\n'),
                    "x": int(x),
                    "y": int(y),
                    "width": int(width),
                    "height": int(height),
                    "selected": False
                })

        # リソース画像の設定
        if len(resource_lines) >= 1:
            reverse_image_path = os.path.join("resource", resource_lines[0])
        else:
            reverse_image_path = os.path.join("resource", "reverse.png")

        if len(resource_lines) >= 2:
            playmat_path = os.path.join("resource", resource_lines[1])
        else:
            playmat_path = os.path.join("resource", "playmat.png")

        # リソース画像の読み込み
        if os.path.exists(reverse_image_path):
            reverse_image = Image.open(reverse_image_path).resize((78, 111))
            reverse_photo_image = ImageTk.PhotoImage(reverse_image)
            reverse_rotated_image = reverse_image.rotate(90, expand=True).resize((111, 78))
            reverse_rotated_photo_image = ImageTk.PhotoImage(reverse_rotated_image)
        else:
            reverse_image = None
            reverse_photo_image = None
            reverse_rotated_image = None
            reverse_rotated_photo_image = None

        if os.path.exists(playmat_path):
            playmat_image = Image.open(playmat_path).resize((960, 720))
            playmat_photo = ImageTk.PhotoImage(playmat_image)

        # ボード上のカード画像を再設定
        for card in deck + on_board:
            image_path = os.path.join("card-img", f"{card['id']}.png")
            if os.path.exists(image_path):
                card_image = Image.open(image_path).resize((78, 111))
                card["original_image"] = card_image
                card["image"] = ImageTk.PhotoImage(card_image)
            elif noimage_image:
                card["original_image"] = noimage_image
                card["image"] = noimage_photo_image

        draw_cards()
        update_deck_count_display()  # デッキ枚数表示を更新
        messagebox.showinfo("成功", "盤面を読み込みました！")
    except Exception as e:
        messagebox.showerror("エラー", f"読み込み中にエラーが発生しました:\n{e}")

# 選択中のカードIDをクリップボードにコピーする関数
def copy_card_id_to_clipboard(event=None):
    if selected_card and "id" in selected_card:
        card_id = selected_card["id"]
        root.clipboard_clear()  # クリップボードをクリア
        root.clipboard_append(card_id)  # カードIDをクリップボードに追加
        root.update()  # クリップボードの更新
#        messagebox.showinfo("クリップボード", f"カードID '{card_id}' をクリップボードにコピーしました！")
#    else:
#        messagebox.showwarning("クリップボード", "選択中のカードがありません！")

# アプリを再起動する関数
def restart_app():
    python = sys.executable
    os.execl(python, python, *sys.argv)  # 現在のPythonスクリプトを再実行
    

# イベントバインディング（クリックやドラッグ）
canvas.bind("<Button-1>", select_card)
canvas.bind("<B1-Motion>", move_card)
canvas.bind("<ButtonRelease-1>", release_card)
canvas.bind("<Button-3>", right_click)
root.bind("<Delete>", delete_card)
canvas.bind("<Double-1>", lambda event: edit_marker_text() if selected_card and selected_card.get("type") == "marker" else None)
root.bind("<Control-t>", lambda event: move_to_deck_top())  # Ctrl+Tでデッキトップへ戻す
root.bind("<Control-b>", lambda event: move_to_deck_bottom())  # Ctrl+Bでデッキボトムへ戻す
root.bind("<Control-f>", lambda event: bring_to_front())  # Ctrl+Fで最前面に移動
root.bind("<Control-r>", lambda event: send_to_back())  # Ctrl+Rで最背面に移動
root.bind("<Control-c>", copy_card_id_to_clipboard)

life_points = tk.IntVar(value=0)  # 初期値は0

# ライフポイント入力が有効かどうかを検証する関数
def validate_life_input(new_value):
    if new_value == "":
        return True
    try:
        val = int(new_value)
        return 0 <= val <= 999999  # 0から999999まで（6桁）
    except ValueError:
        return False

# ライフポイントの入力エラーを防ぐための設定
validate_cmd = root.register(validate_life_input)

def setup_buttons():
    global life_points, deck_count_label  # グローバル変数を使用

    # メインボタンフレーム
    button_frame = tk.Frame(root)
    button_frame.pack()

    # 右下ボタン用フレーム
    bottom_right_frame = tk.Frame(root)
    bottom_right_frame.place(relx=1.0, rely=1.0, anchor="se")  # 右下に配置

    # 左下ボタン用フレーム
    bottom_left_frame = tk.Frame(root)
    bottom_left_frame.place(relx=0.0, rely=1.0, anchor="sw")  # 左下に配置

    # ライフポイント入力ボックスを左下に追加
    tk.Label(bottom_left_frame, text="ライフポイント:").pack(side="top", padx=5, pady=2)

    life_spinbox = tk.Spinbox(
        bottom_left_frame,
        from_=0,
        to=999999,
        increment=1,
        textvariable=life_points,
        width=8,
        validate="key",  # 入力時に検証
        validatecommand=(validate_cmd, "%P")  # 入力内容を検証
    )
    life_spinbox.pack(side="top", padx=5, pady=2)

    # デッキ枚数表示ラベルを左下に追加
    deck_count_label = tk.Label(bottom_left_frame, text=f"デッキ: {len(deck)}枚", font=("Arial", 10))
    deck_count_label.pack(side="top", padx=5, pady=2)

    # 左下ボタン用の横並びフレームを作成
    gacha_button_frame = tk.Frame(bottom_left_frame)
    gacha_button_frame.pack(side="top", padx=5, pady=2)

    # 左下ボタンを横並びで配置
    gacha_buttons = [
        ("コイントス", coin_toss),
        ("6面ダイス", roll_dice),
    ]
    for i, (text, command) in enumerate(gacha_buttons):
        button = tk.Button(gacha_button_frame, text=text, command=command)
        button.grid(row=0, column=i, padx=2, pady=2)  # 横並びに配置
    
    # メインボタンを配置
    buttons = [
        ("デッキトップへ戻す", move_to_deck_top),
        ("デッキボトムへ戻す", move_to_deck_bottom),
        ("すべて回転解除", unrotate_all),
        ("ドロー", draw_from_deck),
        ("シャッフル", shuffle_deck),
        ("マーカーを追加", add_marker),
        ("カードID指定生成", select_card_by_id),
        ("デッキから表向きで出す", lambda: draw_from_deck(y=350)),
        ("デッキから裏向きで出す", lambda: draw_from_deck(face_up=False,y=350)),
        ("デッキの中身を見る", view_deck_contents),
#       ("対戦者ウインドウを開く", open_opponent_window),
#       ("カード情報ウインドウを開く", open_info_window),
    ]
    for i, (text, command) in enumerate(buttons):
        button = tk.Button(button_frame, text=text, command=command)
        button.grid(row=i // 5, column=i % 5, padx=5, pady=5)

    # 右下ボタンを配置
    special_buttons = [
        ("100連ガチャ", gacha_deck_making),
        ("デッキをロード", load_deck),
        ("盤面のセーブ", save_board),
        ("盤面のロード", load_board),
        ("再起動", restart_app),
    ]
    for i, (text, command) in enumerate(special_buttons):
        button = tk.Button(bottom_right_frame, text=text, command=command)
        button.grid(row=i // 2, column=i % 2, padx=5, pady=5)

# ライフポイントの値を表示する（オプション機能として使用可能）
def show_life_points():
    print(f"現在のライフポイント: {life_points.get()}")

# デッキ枚数表示を更新する関数
def update_deck_count_display():
    if 'deck_count_label' in globals() and deck_count_label.winfo_exists():
        deck_count_label.config(text=f"デッキ: {len(deck)}枚")
    
setup_buttons()

def show_initial_windows():
    # カード情報ウィンドウを開く
    open_info_window()
    # 対戦者用ウィンドウを開く
    open_opponent_window()

# メインウィンドウの位置が確定した後に実行
root.after(100, show_initial_windows)

# 初期描画を実行
draw_cards()

# メインループ開始
root.mainloop()

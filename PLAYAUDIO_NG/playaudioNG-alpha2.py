import os
import gi
import eyed3
from PIL import Image
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, GObject, Gst, GdkPixbuf, GLib
from threading import Thread
import time

# Inicjalizacja GStreamer
Gst.init(None)

class AudioPlayer(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Audio Player")

        self.set_default_size(1200, 700)
        self.set_resizable(False)  # Blokowanie zmiany rozmiaru okna
        self.connect("destroy", Gtk.main_quit)

        self.player = Gst.ElementFactory.make("playbin", "player")
        self.equalizer = Gst.ElementFactory.make("equalizer-3bands", "equalizer")

        self.playlist = Gtk.ListStore(str)
        self.treeview = Gtk.TreeView(model=self.playlist)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Playlist", renderer, text=0)
        self.treeview.append_column(column)
        self.treeview.connect("row-activated", self.on_row_activated)

        self.button_play = Gtk.Button(label="Play")
        self.button_play.connect("clicked", self.on_play_clicked)

        self.button_stop = Gtk.Button(label="Stop")
        self.button_stop.connect("clicked", self.on_stop_clicked)

        self.button_add = Gtk.Button(label="Add to Playlist")
        self.button_add.connect("clicked", self.on_add_clicked)

        self.button_load_folder = Gtk.Button(label="Load Folder")
        self.button_load_folder.connect("clicked", self.on_load_folder_clicked)

        self.slider_volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.slider_volume.set_value(50)
        self.slider_volume.connect("value-changed", self.on_volume_changed)

        self.equalizer_sliders = []
        for i in range(3):
            slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -24, 12, 1)
            slider.set_value(0)
            slider.connect("value-changed", self.on_eq_slider_changed, i)
            self.equalizer_sliders.append(slider)

        hbox_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox_buttons.pack_start(self.button_add, False, False, 0)
        hbox_buttons.pack_start(self.button_load_folder, False, False, 0)
        hbox_buttons.pack_start(self.button_play, False, False, 0)
        hbox_buttons.pack_start(self.button_stop, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.pack_start(self.treeview, True, True, 0)
        vbox.pack_start(hbox_buttons, False, False, 0)
        vbox.pack_start(Gtk.Label(label="Volume:"), False, False, 0)
        vbox.pack_start(self.slider_volume, False, False, 0)

        hbox_eq = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for i, slider in enumerate(self.equalizer_sliders):
            hbox_eq.pack_start(Gtk.Label(label=f"Band {i}"), False, False, 0)
            hbox_eq.pack_start(slider, True, True, 0)

        vbox.pack_start(hbox_eq, False, False, 0)

        # Dodanie obszarów na dane odtwarzacza
        self.info_label = Gtk.Label(label="Current Song Info")
        self.info_label.set_size_request(1000, 200)
        self.vinyl_image = Gtk.Image.new_from_file("vinyl.png")
        self.album_cover = Gtk.Image.new()
        self.album_cover.set_size_request(200, 200)  # Ustawienie żądanych wymiarów obrazka

        # Kontener dla obszarów płyty winylowej, okładki albumu i informacji o utworze
        self.fixed = Gtk.Fixed()
        self.fixed.put(self.info_label, 0, 0)  # Informacje o utworze zajmują od 0 do 1/3 szerokości
        self.fixed.put(self.vinyl_image, 1000, 0)  # Płyta winylowa zajmuje od 2/3 do 3/3 szerokości
        self.fixed.put(self.album_cover, 1000, 0)  # Okładka zajmuje nad obrazem płyty winylowej


        vbox.pack_start(self.fixed, False, False, 0)

        self.add(vbox)

        self.current_playlist_index = -1

        # Podłączanie equalizera do odtwarzacza
        self.player.set_property("audio-filter", self.equalizer)

        # Wątek do animacji obrotu płyty winylowej
        self.rotation_thread = None
        self.rotation_stop = False

    def on_play_clicked(self, widget):
        self.rotation_stop = True
        if self.current_playlist_index != -1:
            file_path = self.playlist[self.current_playlist_index][0]
            tag_info = self.get_metadata(file_path)
            if tag_info:
                title = tag_info.get("title", "Unknown Title")
                artist = tag_info.get("artist", "Unknown Artist")
                album = tag_info.get("album", "Unknown Album")
                self.info_label.set_text(f"{title} - {artist} ({album})")
            else:
                self.info_label.set_text("No metadata tags found")
        
            self.player.set_state(Gst.State.PLAYING)
            # Rozpoczęcie wątku animacji tylko, jeśli nie został jeszcze uruchomiony
            if not self.rotation_thread or not self.rotation_thread.is_alive():
                self.rotation_stop = False
                self.rotation_thread = Thread(target=self.rotate_vinyl, daemon=True)
                self.rotation_thread.start()

    def on_stop_clicked(self, widget):
        self.player.set_state(Gst.State.NULL)
        # Zatrzymanie animacji
        self.rotation_stop = True

    def on_add_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(title="Please choose a file", parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        filter_audio = Gtk.FileFilter()
        filter_audio.set_name("Audio files")
        filter_audio.add_mime_type("audio/*")
        dialog.add_filter(filter_audio)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()
            self.playlist.append([file_path])
        dialog.destroy()

    def on_load_folder_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(title="Please choose a folder", parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder_path = dialog.get_filename()
            self.add_files_from_folder(folder_path)
        dialog.destroy()

    def add_files_from_folder(self, folder_path):
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith(".mp3") or file.endswith(".wav") or file.endswith(".ogg"):
                    file_path = os.path.join(root, file)
                    self.playlist.append([file_path])

    def on_row_activated(self, treeview, path, column):
        # Zatrzymanie animacji
        self.rotation_stop = True
        iter = treeview.get_model().get_iter(path)
        self.current_playlist_index = path.get_indices()[0]
        file_path = treeview.get_model().get_value(iter, 0)

        # Zwalnianie obecnego potoku, jeśli jest uruchomiony
        if self.player:
            self.player.set_state(Gst.State.NULL)

        # Ustawianie URI odtwarzacza na wybrany plik
        self.player.set_property("uri", "file://" + file_path)

        # Pobieranie tagów metadanych i aktualizacja etykiety informacyjnej
        tag_info = self.get_metadata(file_path)
        if tag_info:
            title = tag_info.get("title", "Unknown Title")
            artist = tag_info.get("artist", "Unknown Artist")
            album = tag_info.get("album", "Unknown Album")
            self.info_label.set_text(f"{title} - {artist} ({album})")
        
            # Aktualizacja obrazu płyty winylowej
            self.vinyl_image.set_from_file("vinyl.png")
        
            # Pobieranie okładki albumu, jeśli jest dostępna
            album_cover_path = tag_info.get("album_cover")
            if album_cover_path:
                album_cover_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(album_cover_path, 200, 200)  # Pomniejszenie obrazka
                self.album_cover.set_from_pixbuf(album_cover_pixbuf)
            else:
                self.album_cover.set_from_file("default_album_cover.png")  # Ustawienie domyślnej okładki albumu
        else:
            self.info_label.set_text("No metadata tags found")
            self.vinyl_image.set_from_file("vinyl.png")  # Ustawienie domyślnego obrazu płyty winylowej
            self.album_cover.set_from_file("default_album_cover.png")  # Ustawienie domyślnej okładki albumu    

        # Rozpoczęcie odtwarzania
        self.player.set_state(Gst.State.PLAYING)
        # Rozpoczęcie wątku animacji tylko, jeśli nie został jeszcze uruchomiony
        if not self.rotation_thread or not self.rotation_thread.is_alive():
            self.rotation_stop = False
            self.rotation_thread = Thread(target=self.rotate_vinyl, daemon=True)
            self.rotation_thread.start()

    def get_metadata(self, file_path):
        audiofile = eyed3.load(file_path)
        if audiofile:
            tag = audiofile.tag
            if tag:
                title = tag.title
                artist = tag.artist
                album = tag.album
                album_cover_path = None
                if tag.images:
                    image = tag.images[0]
                    image_data = image.image_data
                    image_extension = image.mime_type.split("/")[1]
                    album_cover_path = "album_cover." + image_extension
                    with open(album_cover_path, "wb") as f:
                        f.write(image_data)
                return {"title": title, "artist": artist, "album": album, "album_cover": album_cover_path}
        return None

    def on_volume_changed(self, widget):
        volume = widget.get_value() / 100
        self.player.set_property("volume", volume)

    def on_eq_slider_changed(self, widget, band):
        value = widget.get_value()
        self.equalizer.set_property(f"band{band}", value)

    def rotate_vinyl(self):
        angle = 0
        moved_once = False
        while not self.rotation_stop:
            if not moved_once:
                # Przesunięcie płyty winylowej tylko raz
                for x in range(1000, 900, -1):  # Płynne przesuwanie płyty winylowej w lewo
                    self.fixed.move(self.vinyl_image, x, 0)
                    time.sleep(0.05)
                moved_once = True
            #else:
             #   rotated_image = self.rotate_image("vinyl.png", angle)  # Obracamy obrazek
              #  if rotated_image is not None:  # Sprawdzamy, czy obrazek został poprawnie obrócony
               #     pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(rotated_image, 200, 200)  # Przekształcamy obrócony obrazek do formatu GdkPixbuf    
                #    self.vinyl_image.set_from_pixbuf(pixbuf)  # Ustawiamy obrócony obrazek w komponencie Gtk.Image
           #angle += 0.25  # Zwiększamy kąt obrotu
           #angle %= 360  # Ograniczamy kąt do zakresu od 0 do 360 stopni
           #time.sleep(0.001)  # Czekamy krótki czas, aby uzyskać płynną animację

    def rotate_image(self, image_path, angle):
        img = Image.open(image_path)  # Poprawienie nazwy zmiennej na 'img'
        rotated_image = img.rotate(angle, resample=Image.BICUBIC, expand=True)    
        rotated_image_path = "rotated_vinyl.png"
        rotated_image.save(rotated_image_path)
        return rotated_image_path

    def run(self):
        self.show_all()
        Gtk.main()

if __name__ == "__main__":
    player = AudioPlayer()
    player.run()


import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, GObject, Gst, GLib
import os

# Inicjalizacja GStreamer
Gst.init(None)

class AudioPlayer(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Audio Player")

        self.set_default_size(1280, 720)
        self.connect("destroy", Gtk.main_quit)

        self.equalizer_10bands = Gst.parse_launch("equalizer-10bands")
        self.equalizer_3bands = Gst.ElementFactory.make("equalizer-3bands", "equalizer_3bands")

        self.player = Gst.ElementFactory.make("playbin", "player")

        self.playlist = Gtk.ListStore(str)
        self.treeview = Gtk.TreeView(model=self.playlist)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Playlist", renderer, text=0)
        self.treeview.append_column(column)
        self.treeview.connect("row-activated", self.on_row_activated)

        self.button_add = Gtk.Button(label="Add to Playlist")
        self.button_add.connect("clicked", self.on_add_clicked)

        self.button_load_folder = Gtk.Button(label="Load Folder")
        self.button_load_folder.connect("clicked", self.on_load_folder_clicked)

        vbox_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vbox_buttons.pack_start(self.button_add, False, False, 0)
        vbox_buttons.pack_start(self.button_load_folder, False, False, 0)

        self.slider_volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.slider_volume.set_value(50)
        self.slider_volume.connect("value-changed", self.on_volume_changed)

        self.equalizer_sliders = []
        self.equalizer_type = "10bands"  # Domyślnie ustaw na equalizer 10-pasmowy

        hbox_eq_sliders = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.update_equalizer_sliders()  # Tworzenie suwaków equalizera na podstawie wybranego typu

        hbox_equalizer_select = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox_equalizer_select.pack_start(Gtk.Label(label="Equalizer Type:"), False, False, 0)
        self.radio_10bands = Gtk.RadioButton.new_with_label_from_widget(None, "10 Bands Equalizer")
        self.radio_10bands.connect("toggled", self.on_equalizer_selected, "10bands")
        hbox_equalizer_select.pack_start(self.radio_10bands, False, False, 0)
        self.radio_3bands = Gtk.RadioButton.new_with_label_from_widget(self.radio_10bands, "3 Bands Equalizer")
        self.radio_3bands.connect("toggled", self.on_equalizer_selected, "3bands")
        hbox_equalizer_select.pack_start(self.radio_3bands, False, False, 0)

        hbox_stop_button = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.button_stop = Gtk.Button(label="Stop")
        self.button_stop.connect("clicked", self.on_stop_clicked)
        hbox_stop_button.pack_start(self.button_stop, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.pack_start(self.treeview, True, True, 0)
        vbox.pack_start(vbox_buttons, False, False, 0)
        vbox.pack_start(Gtk.Label(label="Volume:"), False, False, 0)
        vbox.pack_start(self.slider_volume, False, False, 0)
        vbox.pack_start(hbox_eq_sliders, False, False, 0)
        vbox.pack_start(hbox_equalizer_select, False, False, 0)
        vbox.pack_start(hbox_stop_button, False, False, 0)

        self.add(vbox)

        self.current_playlist_index = -1
        self.player.set_property("audio-filter", self.equalizer_10bands)  # Domyślnie ustaw equalizer 10-pasmowy

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
            self.load_equalizer_preset(file_path)
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
                    self.load_equalizer_preset(file_path)

    def on_row_activated(self, treeview, path, column):
        iter = treeview.get_model().get_iter(path)
        self.current_playlist_index = path.get_indices()[0]
        file_path = treeview.get_model().get_value(iter, 0)
        if self.player:
            self.player.set_state(Gst.State.NULL)
        self.player.set_property("uri", "file://" + file_path)
        self.player.set_state(Gst.State.PLAYING)
        self.load_equalizer_preset(file_path)

    def on_volume_changed(self, widget):
        volume = widget.get_value() / 100
        self.player.set_property("volume", volume)

    def on_equalizer_selected(self, widget, equalizer_type):
        self.equalizer_type = equalizer_type
        self.update_equalizer_sliders()  # Aktualizacja suwaków equalizera po zmianie typu

    def update_equalizer_sliders(self):
        # Usunięcie istniejących suwaków
        for slider in self.equalizer_sliders:
            slider.destroy()
        self.equalizer_sliders.clear()

        # Resetowanie wszystkich wartości equalizera do domyślnych
        if self.equalizer_type == "10bands":
            for i in range(10):
                self.equalizer_10bands.set_property(f"band{i}", 0)
        elif self.equalizer_type == "3bands":
            for i in range(3):
                self.equalizer_3bands.set_property(f"band{i}", 0)

        # Tworzenie nowych suwaków w zależności od wybranego typu
        if self.equalizer_type == "10bands":
            num_bands = 10
            equalizer = self.equalizer_10bands
        elif self.equalizer_type == "3bands":
            num_bands = 3
            equalizer = self.equalizer_3bands

        hbox_eq_sliders = None
        # Sprawdzenie, czy istnieje kontener dla suwaków equalizera
        if self.get_child() is not None:
            hbox_eq_sliders = self.get_child().get_children()[4]
    
        if hbox_eq_sliders is not None:
            for i in range(num_bands):
                slider = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, -24, 12, 1)
                slider.set_value(0)
                slider.set_size_request(30, 150)  # Ustawienie szerokości i wysokości suwaka
                slider.connect("value-changed", self.on_eq_slider_changed, i)
                self.equalizer_sliders.append(slider)
    
            for slider in self.equalizer_sliders:
                hbox_eq_sliders.pack_start(slider, False, False, 0)
            hbox_eq_sliders.show_all()

        # Aktualizacja elementu equalizera w potoku GStreamer
        self.player.set_property("audio-filter", equalizer)

    def on_eq_slider_changed(self, widget, band):
        value = widget.get_value()
        if self.equalizer_type == "10bands":
            self.equalizer_10bands.set_property(f"band{band}", value)
        elif self.equalizer_type == "3bands":
            print(f"New value for band {band}: {value}")
            self.equalizer_3bands.set_property(f"band{band}", value)

        # Po zmianie wartości equalizera, zapisz ustawienia do pliku .eqp
        self.save_equalizer_preset()

    def on_stop_clicked(self, widget):
        self.player.set_state(Gst.State.NULL)

        for i in range(10):
            self.equalizer_10bands.set_property(f"band{i}", 0)

        for i in range(3):
            self.equalizer_3bands.set_property(f"band{i}", 0)

        self.update_equalizer_sliders()

    def save_equalizer_preset(self):
        if self.current_playlist_index >= 0:
            file_path = self.playlist[self.current_playlist_index][0]
            eqp_file_path = os.path.splitext(file_path)[0] + ".eqp"
            with open(eqp_file_path, 'w') as file:
                file.write(f"Equalizer Type: {self.equalizer_type}\n")
                if self.equalizer_type == "10bands":
                    for i in range(10):
                        band_value = self.equalizer_10bands.get_property(f"band{i}")
                        file.write(f"band{i}={band_value}\n")
                elif self.equalizer_type == "3bands":
                    for i in range(3):
                        band_value = self.equalizer_3bands.get_property(f"band{i}")
                        file.write(f"band{i}={band_value}\n")


    def load_equalizer_preset(self, audio_file_path):
        eqp_file_path = os.path.splitext(audio_file_path)[0] + ".eqp"
        if os.path.exists(eqp_file_path):
            with open(eqp_file_path, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    if line.startswith("Equalizer Type:"):
                        _, equalizer_type = line.split(":")
                        equalizer_type = equalizer_type.strip()
                        if equalizer_type == "10bands":
                           self.radio_10bands.set_active(True)
                        elif equalizer_type == "3bands":
                            self.radio_3bands.set_active(True)
                    elif line.startswith("band"):
                        band, value = line.split("=")
                        band = int(band.replace("band", ""))
                        value = float(value.strip())
                        if equalizer_type == "10bands":
                            self.equalizer_10bands.set_property(f"band{band}", value)
                            self.equalizer_sliders[band].set_value(value)
                        elif equalizer_type == "3bands":
                            self.equalizer_3bands.set_property(f"band{band}", value)
                            self.equalizer_sliders[band].set_value(value)

    def run(self):
        self.show_all()
        Gtk.main()

if __name__ == "__main__":
    player = AudioPlayer()
    player.run()
